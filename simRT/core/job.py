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
                try:
                    yield req
                except simpy.Interrupt as ir:
                    if not req.is_on_platform:
                        continue

                assert self.cpu is None
                self.cpu = req
                if self._start_time is None:
                    self._start_time = self.env.now

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
            # 这个 job 超出 deadline
            self.task.interrupt(
                f"{self.id} miss deadline at [{self.absolute_deadline}]"
            )
