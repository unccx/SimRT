import math
from typing import Optional, Sequence

import simpy
from simpy.core import SimTime
from tqdm import trange

from .processor import PlatformInfo, ProcessorPlatform, SpeedType
from .task import GenericTask, TaskInfo


class Simulator:

    def __init__(
        self,
        taskinfos: Sequence[TaskInfo],
        platform_info: Optional[PlatformInfo | Sequence[SpeedType]] = None,
    ) -> None:
        """
        taskinfos 任务集合
        processors 处理器集合，如果为 None 则默认为单处理器
        """
        self.env = simpy.Environment()
        self.platform = ProcessorPlatform(self.env, platform_info)
        self.tasks: list[GenericTask] = []
        self._hyper_period = 1

        for taskinfo in taskinfos:
            self.add_task(taskinfo)

    def add_task(self, taskinfo: TaskInfo) -> None:
        self.tasks.append(taskinfo.as_task(self.platform))
        self._hyper_period = math.lcm(self._hyper_period, math.ceil(taskinfo.period))

    @property
    def num_task(self):
        return len(self.tasks)

    @property
    def hyper_period(self):
        """
        返回任务周期的最小公倍数
        """
        return self._hyper_period

    def run(self, until: Optional[SimTime] = None, show_progress: bool = False) -> bool:
        try:
            if until is None or until > self.hyper_period:
                until = self.hyper_period
            if show_progress:
                for i in trange(
                    1, math.ceil(until) + 1, 100, desc="Processing", leave=False
                ):
                    self.env.run(until=i)
            else:
                self.env.run(until=until)
        except simpy.Interrupt as ir:
            # 在模拟调度期间错过任务的 deadline
            return False

        # 在模拟调度期间满足所有任务的 deadline
        return True
