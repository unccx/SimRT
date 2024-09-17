import math
from abc import ABC, abstractmethod
from itertools import count
from random import randint, random, uniform

from ..core.processor import PlatformInfo, SpeedType
from ..core.task import PeriodicTask, TaskInfo

Taskset = list[TaskInfo]


class AbstractTaskFactory(ABC):
    _task_id_iter = count()

    def __init__(
        self,
        period_bound: tuple[int, int],
        platform_info: PlatformInfo,
        implicit_deadline: bool = True,
    ) -> None:
        assert period_bound[0] <= period_bound[1], "Invalid value range"
        self.platform_info = platform_info
        self.period_bound = period_bound
        self.implicit_deadline = implicit_deadline

    @abstractmethod
    def create_task(self, task_utilization: float) -> TaskInfo:
        pass


class PeriodicTaskFactory(AbstractTaskFactory):
    def create_task(self, task_utilization: float) -> TaskInfo:
        """
        根据输入的利用率列表返回任务集
        输入的利用率列表的利用率之和不要求小于等于1
        """
        assert (
            0 < task_utilization <= self.platform_info.fastest_speed
        ), "Invalid task utilization"

        period = randint(*self.period_bound)
        wcet = period * task_utilization

        if self.implicit_deadline:
            deadline = period
        else:
            # 要求 deadline <= period，但是至少在最快的核心上执行满足 deadline
            # 在最快的核心上执行时间 fastest_execution_time <= deadline
            fastest_execution_time = wcet / self.platform_info.fastest_speed
            deadline = randint(math.ceil(fastest_execution_time), math.ceil(period))

        return TaskInfo(
            id=next(self._task_id_iter),
            type=PeriodicTask,
            wcet=wcet,
            deadline=deadline,
            period=period,
        )


class UtilizationGenerationAlgorithm:

    @staticmethod
    def generate_uniform_utilizations(
        num_task: int, fastest_speed: float
    ) -> list[float]:
        assert fastest_speed > 0 and num_task > 0, "parameter must be greater than 0"
        task_utilizations = []
        for _ in range(num_task):
            task_utilizations.append(uniform(0, fastest_speed))

        return task_utilizations

    @staticmethod
    def UScaling(
        taskset_utilization: float, num_task: int, fastest_speed: float
    ) -> list[float]:
        """
        输入任务集利用率和任务数量根据 UScaling 算法生成一系列任务利用率
        任务利用率之和等于任务集利用率。当任务集利用率大于1时，可能生成大于1的任务利用率
        任务利用率需要小于最快的处理器速度，只留下符合要求的任务集
        """
        assert (
            taskset_utilization > 0 and fastest_speed > 0 and num_task > 0
        ), "parameter must be greater than 0"
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
        assert (
            taskset_utilization > 0 and fastest_speed > 0 and num_task > 0
        ), "parameter must be greater than 0"
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
        assert (
            taskset_utilization > 0 and fastest_speed > 0 and num_task > 0
        ), "parameter must be greater than 0"
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
