import math
from itertools import count
from random import randint, uniform
from typing import Sequence

from simpy.core import SimTime

from ..core.processor import SpeedType
from ..core.task import GenericTask, TaskInfo


class TaskGenerator:
    _task_id_iter = count()

    def __init__(
        self,
        task_type: type[GenericTask],
        period_bound: tuple[int, int],
        speed_list: list[SpeedType] = [1],
        implicit_deadline: bool = True,
    ) -> None:
        self.task_type = task_type
        self.period_bound = period_bound
        self.speed_list = sorted(speed_list)
        self.implicit_deadline = implicit_deadline

    @property
    def sum_of_processor_speeds(self):
        return sum(self.speed_list)

    @property
    def S_m(self):
        return self.sum_of_processor_speeds

    def generate_task(self, task_utilization_list: list[float]) -> Sequence[TaskInfo]:
        """
        根据输入的利用率列表返回任务集
        输入的利用率列表的利用率之和不要求小于等于1
        """
        taskinfos = []
        for task_u in task_utilization_list:
            assert task_u <= 1, "Task utilization must be less than or equal to 1"
            period = randint(*self.period_bound)
            wcet = period * task_u
            deadline = (
                period if self.implicit_deadline else randint(math.ceil(wcet), period)
            )

            taskinfo = TaskInfo(
                id=next(self._task_id_iter),
                type=self.task_type,
                wcet=wcet,
                deadline=deadline,
                period=period,
            )
            taskinfos.append(taskinfo)

        return taskinfos

    def UScaling_algorithm(
        self, system_utilization: float, num_task: int
    ) -> Sequence[TaskInfo]:
        """
        输入系统利用率和任务数量根据 UScaling 算法生成一系列利用率（利用率之和可以大于1）
        """
        assert (
            system_utilization > 0 and system_utilization <= 1
        ), "System utilization must be in (0,1]"
        taskset_utilization = system_utilization * self.S_m

        task_utilization_list = []
        for _ in range(num_task):
            task_utilization_list.append(uniform(0, taskset_utilization))

        factor = taskset_utilization / sum(task_utilization_list)
        task_utilization_list = [task_u * factor for task_u in task_utilization_list]
        return self.generate_task(task_utilization_list)
