import inspect
import math
from itertools import count
from random import randint, random, uniform
from typing import Callable, Optional, Sequence

from ..core.processor import PlatformInfo, SpeedType
from ..core.task import GenericTask, TaskInfo

Taskset = list[TaskInfo]

class TaskGenerator:
    _task_id_iter = count()

    def __init__(
        self,
        task_type: type[GenericTask],
        period_bound: tuple[int, int],
        platform_info: Optional[PlatformInfo | Sequence[SpeedType]] = None,
        implicit_deadline: bool = True,
    ) -> None:
        if platform_info is None:
            self.platform_info = PlatformInfo()
        elif isinstance(platform_info, Sequence):
            self.platform_info = PlatformInfo(list(platform_info))
        elif isinstance(platform_info, PlatformInfo):
            self.platform_info = platform_info
        else:
            assert False, f"platform_info type is not {type(platform_info)}"

        self.task_type = task_type
        self.period_bound = period_bound
        self.implicit_deadline = implicit_deadline

    def generate_taskset(
        self,
        system_utilization: float,
        num_task: int,
        num_task_set: int,
        algorithm: Optional[Callable] = None,
    ) -> list[Taskset]:
        assert (
            system_utilization > 0 and system_utilization <= 1
        ), "System utilization must be in (0,1]"
        taskset_utilization = system_utilization * self.platform_info.S_m

        # 默认使用 UUniFast 算法生成利用率
        if algorithm is None:
            algorithm = self.UUniFast

        # 检查生成利用率的算法是否为这几种
        assert algorithm.__name__ in ["UScaling", "UFitting", "UFitting", "UUniFast"]

        task_sets = []
        while len(task_sets) < num_task_set:
            utilizations = algorithm(
                taskset_utilization, num_task, self.platform_info.fastest_speed
            )
            task_set = self.generate_task(utilizations)
            task_sets.append(task_set)

        return task_sets

    def generate_task(self, task_utilizations: Sequence[float]) -> list[TaskInfo]:
        """
        根据输入的利用率列表返回任务集
        输入的利用率列表的利用率之和不要求小于等于1
        """
        taskinfos = []
        for task_u in task_utilizations:
            assert (
                task_u <= self.platform_info.fastest_speed
            ), "Task utilization must be less than or equal to fastest core speed"

            period = randint(*self.period_bound)
            wcet = period * task_u

            if self.implicit_deadline:
                deadline = period
            else:
                # 要求 deadline <= period，但是至少在最快的核心上执行满足 deadline
                # 在最快的核心上执行时间 fastest_execution_time <= deadline
                fastest_execution_time = wcet / self.platform_info.fastest_speed
                deadline = randint(math.ceil(fastest_execution_time), math.ceil(period))

            taskinfo = TaskInfo(
                id=next(self._task_id_iter),
                type=self.task_type,
                wcet=wcet,
                deadline=deadline,
                period=period,
            )
            taskinfos.append(taskinfo)

        return taskinfos

    @staticmethod
    def UScaling(
        taskset_utilization: float, num_task: int, fastest_speed: float
    ) -> list[float]:
        """
        输入任务集利用率和任务数量根据 UScaling 算法生成一系列任务利用率
        任务利用率之和等于任务集利用率。当任务集利用率大于1时，可能生成大于1的任务利用率
        任务利用率需要小于最快的处理器速度，只留下符合要求的任务集
        """
        assert taskset_utilization > 0, "taskset_utilization must be greater than 0"
        while True:
            task_utilizations = []
            for _ in range(num_task):
                task_utilizations.append(uniform(0, taskset_utilization))

            factor = taskset_utilization / sum(task_utilizations)
            task_utilizations = [task_u * factor for task_u in task_utilizations]
            if all(u <= fastest_speed for u in task_utilizations):
                return task_utilizations

    @staticmethod
    def UFitting(
        taskset_utilization: float, num_task: int, fastest_speed: float
    ) -> list[float]:
        """
        输入任务集利用率和任务数量根据 UFitting 算法生成一系列任务利用率
        任务利用率之和等于任务集利用率。当任务集利用率大于1时，可能生成大于1的任务利用率
        任务利用率需要小于最快的处理器速度，只留下符合要求的任务集
        """
        assert taskset_utilization > 0, "taskset_utilization must be greater than 0"
        while True:
            sum_U = taskset_utilization
            task_utilizations = []
            for _ in range(num_task - 1):
                task_u = uniform(0, sum_U)
                sum_U -= task_u
                task_utilizations.append(task_u)

            task_utilizations.append(sum_U)
            if all(u <= fastest_speed for u in task_utilizations):
                return task_utilizations

    @staticmethod
    def UUniFast(
        taskset_utilization: float, num_task: int, fastest_speed: float
    ) -> list[float]:
        """
        输入任务集利用率和任务数量根据 UUniFast 算法生成一系列任务利用率
        任务利用率之和等于任务集利用率。当任务集利用率大于1时，可能生成大于1的任务利用率
        任务利用率需要小于最快的处理器速度，只留下符合要求的任务集
        """
        assert taskset_utilization > 0, "taskset_utilization must be greater than 0"
        while True:
            task_utilizations = []
            sumU = taskset_utilization
            for i in range(1, num_task):
                nextSumU = sumU * random() ** (1.0 / (num_task - i))
                task_utilizations.append(sumU - nextSumU)
                sumU = nextSumU
            task_utilizations.append(sumU)
            if all(u <= fastest_speed for u in task_utilizations):
                return task_utilizations
