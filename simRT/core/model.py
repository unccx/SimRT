import math
from typing import Optional, Sequence

import simpy
from simpy.core import SimTime

from .processor import ProcessorPlatform, SpeedType
from .task import GenericTask, TaskInfo


class Simulator:

    def __init__(
        self, taskinfos: Sequence[TaskInfo], speed_list: list[SpeedType] = [1]
    ) -> None:
        self.env = simpy.Environment()
        self.platform = ProcessorPlatform(self.env, speed_list)
        self.tasks: list[GenericTask] = []
        self._hyper_period = 1

        for taskinfo in taskinfos:
            self.add_task(taskinfo)

    def add_task(self, taskinfo: TaskInfo) -> None:
        self.tasks.append(taskinfo.task_from_info(self.platform))
        self._hyper_period = math.lcm(self._hyper_period, math.ceil(taskinfo.period))

    @property
    def num_task(self):
        return len(self.tasks)

    @property
    def hyper_period(self):
        return self._hyper_period

    def run(self, until: Optional[SimTime] = None) -> bool:
        try:
            if until is None or until > self.hyper_period:
                self.env.run(until=self.hyper_period)
            else:
                self.env.run(until=until)
        except simpy.Interrupt as ir:
            return False

        return True
