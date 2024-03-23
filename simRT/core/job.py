from __future__ import annotations

from typing import TYPE_CHECKING, Generator, Optional

import simpy
from simpy.core import SimTime

if TYPE_CHECKING:
    from .processor import ProcessorPlatform, ProcessorRequest, SpeedType
    from .task import GenericTask


class Job(simpy.Process):
    def __init__(self, task: GenericTask):
        super().__init__(task.env, self.activate_job())
        self.task = task
        self.id: str = f"{task.id}_{next(self.task._job_id_generator)}"
        self.cpu: Optional[ProcessorRequest] = None

        # start_time 和 end_time 只用于记录执行历史
        self._start_time: Optional[SimTime] = None  # 该作业开始执行的时间
        self._end_time: Optional[SimTime] = None  # 该作业结束执行的时间
        self.logs = []

        self.arrival_time: SimTime = self.env.now
        self.absolute_deadline: SimTime = self.env.now + task.deadline
        self.accumulated_execution: SimTime = 0

    @property
    def platform(self) -> ProcessorPlatform:
        return self.task.platform

    @property
    def wcet(self) -> SimTime:
        return self.task.wcet

    @property
    def period(self) -> SimTime:
        return self.task.period

    @property
    def remaining_execution(self) -> SimTime:
        return max(self.wcet - self.accumulated_execution, 0)

    def is_running(self) -> bool:
        """Returns True If the job is executed on the processor"""
        return self.cpu is not None and self.cpu.is_on_platform

    def is_active(self) -> bool:
        """Returns True if the job is still executing"""
        return self._end_time is None

    def activate_job(self) -> Generator:
        while self.remaining_execution > 0:
            # Retry the job until it is done.
            prio = self.absolute_deadline  # EDF
            with self.platform.request(priority=prio) as req:
                # 等待 req 申请得到处理器核心，即使是在上一行 with 代码中
                # request 占有处理器核心，也需要等待其他 process 的 request
                # 留下优先级最高的 req
                try:
                    yield req
                except simpy.Interrupt as ir:
                    # 在同一时刻先占有核心的请求可能会被优先级更高的请求挤出
                    # 处理器平台，需要重新请求处理器核心
                    # 也可能只是 req 在处理器占有队列（users）中的位置变化而被中断
                    # 这种情况不需要重新请求处理器核心
                    if not req.is_on_platform:
                        continue

                assert self.cpu is None
                self.cpu = req
                if self._start_time is None:
                    self._start_time = self.env.now

                # 只要没有被挤出处理器占有队列（users）并且剩余执行量还大于0，就继续执行
                # 但是需要重新确定 req 所占有的核心速度
                while self.cpu.is_on_platform and self.remaining_execution > 0:
                    assert self.cpu.speed is not None
                    execution_speed: SimTime = self.cpu.speed
                    start: SimTime = self.env.now
                    try:
                        yield self.env.timeout(
                            self.remaining_execution / execution_speed
                        )
                        self.accumulated_execution = self.wcet
                    except simpy.Interrupt as ir:
                        self.accumulated_execution += (
                            self.env.now - start
                        ) * execution_speed

                    # 记录 Job 在不同核心的执行历史
                    log = {
                        "arrival": self.arrival_time,
                        "start": start,
                        "end": self.env.now,
                        "speed": execution_speed,
                    }
                    if self.remaining_execution > 0:
                        log["next_speed"] = self.cpu.speed
                        log["remaining"] = self.remaining_execution
                    self.logs.append(log)

                self.cpu = None

        assert (
            self.accumulated_execution == self.wcet
        ), "accumulated_execution is not equal to wcet"

        self._end_time = self.env.now

        if self.env.now > self.absolute_deadline:
            # Job 执行完成的时间错过 Job 的绝对期限，中断模拟
            self.task.interrupt(
                f"{self.id} miss deadline at [{self.absolute_deadline}]"
            )
