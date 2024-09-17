import bisect
import random
from abc import ABC, abstractmethod
from re import U
from typing import Callable, Optional, Sequence, Type

from ..core.processor import PlatformInfo, SpeedType
from ..core.task import GenericTask, PeriodicTask, TaskInfo
from ..generator.task_factory import (
    AbstractTaskFactory,
    PeriodicTaskFactory,
    UtilizationGenerationAlgorithm,
)

Taskset = list[TaskInfo]


class AbstractTasksetFactory(ABC):

    def __init__(
        self,
        utilization_algorithm: Callable,
        platform_info: PlatformInfo,
    ) -> None:
        self.platform_info = platform_info
        self.utilization_algorithm = utilization_algorithm

    @abstractmethod
    def create_taskset(
        self,
        num_task: int,
        system_utilization: Optional[float] = None,
    ) -> Taskset:
        pass


class TasksetFactory(AbstractTasksetFactory):

    def __init__(
        self,
        task_factory: AbstractTaskFactory,
        utilization_algorithm: Callable,
        platform_info: PlatformInfo,
    ) -> None:
        super().__init__(utilization_algorithm, platform_info)
        self.task_factory = task_factory

    def create_taskset(
        self,
        num_task: int,
        system_utilization: Optional[float] = None,
    ) -> Taskset:
        """
        如果 system_utilization 为 None ，在 (1e-10, 1) 内随机生成 system_utilization
        """
        if system_utilization is None:
            system_utilization = random.uniform(1e-10, 1)
        else:
            assert 0 < system_utilization <= 1, "System utilization must be in (0,1]"

        taskset_utilization = system_utilization * self.platform_info.S_m
        utilizations = self.utilization_algorithm(
            taskset_utilization, num_task, self.platform_info.fastest_speed
        )

        return [self.task_factory.create_task(u) for u in utilizations]


class TaskSubsetFactory(AbstractTasksetFactory):

    def __init__(
        self,
        tasks: list[TaskInfo],
        utilization_algorithm: Callable,
        platform_info: PlatformInfo,
    ):
        super().__init__(utilization_algorithm, platform_info)
        self.tasks: list[TaskInfo] = sorted(tasks, key=lambda task: task.utilization)
        self.task_utilizations = [task.utilization for task in self.tasks]

    def _select_task(self, target_utilization: float) -> TaskInfo:
        """
        从 self.tasks 中选择与 target_utilization 利用率相近的任务作为任务集
        候选的 self.tasks 的任务数量太少会导致 selected_task 的利用率与target_utilization相差过大
        """
        assert target_utilization > 0, "target_utilization must be greater than 0"
        index = bisect.bisect_left(self.task_utilizations, target_utilization)

        if index == 0:
            selected_task = self.tasks[0]
        if index == len(self.tasks):
            selected_task = self.tasks[-1]
        else:
            before = self.tasks[index - 1]
            after = self.tasks[index]
            selected_task = min(
                [after, before], key=lambda x: abs(x.utilization - target_utilization)
            )

        return selected_task

    def create_taskset(
        self,
        num_task: int,
        system_utilization: Optional[float] = None,
    ) -> Taskset:
        if system_utilization is None:
            system_utilization = random.uniform(1e-10, 1)
        else:
            assert 0 < system_utilization <= 1, "System utilization must be in (0,1]"

        taskset_utilization = system_utilization * self.platform_info.S_m
        utilizations = self.utilization_algorithm(
            taskset_utilization, num_task, self.platform_info.fastest_speed
        )

        return [self._select_task(u) for u in utilizations]


class TasksetGenerator:
    def __init__(self):
        self.utilization_algorithm: Callable = UtilizationGenerationAlgorithm.UUniFast
        self.implicit_deadline: bool = True

    def set_platform_info(self, platform_info: PlatformInfo | Sequence[SpeedType]):
        if isinstance(platform_info, Sequence):
            self.platform_info = PlatformInfo(list(platform_info))
        elif isinstance(platform_info, PlatformInfo):
            self.platform_info = platform_info
        else:
            assert False, f"processorsinfo type is not {type(platform_info)}"
        return self

    def set_period_bound(self, period_bound: tuple[int, int]):
        self.period_bound = period_bound
        return self

    def set_taskset_factory(self, taskset_factory_type: Type[AbstractTasksetFactory]):
        self.taskset_factory_type = taskset_factory_type
        return self

    def set_task_type(self, task_type: Type[GenericTask]):
        self.task_type = task_type
        return self

    def set_utilization_algorithm(self, utilization_algorithm):
        self.utilization_algorithm = utilization_algorithm
        return self

    def set_implicit_deadline(self, implicit_deadline: bool):
        self.implicit_deadline = implicit_deadline
        return self

    def set_num_task(self, num_task: int):
        self.num_task = num_task
        return self

    def setup(self):
        self._validate_required_attributes()
        self._setup_task_factory()
        self._setup_taskset_factory()
        return self

    def _validate_required_attributes(self):
        required_attributes = [
            "task_type",
            "taskset_factory_type",
            "platform_info",
            "period_bound",
        ]
        for attr in required_attributes:
            if not hasattr(self, attr):
                raise AttributeError(f"{attr} must be set")

        if self.taskset_factory_type == TaskSubsetFactory and not hasattr(
            self, "num_task"
        ):
            raise ValueError("num_task must be set")

    def _setup_task_factory(self):
        if self.task_type == PeriodicTask:
            self.task_factory = PeriodicTaskFactory(
                self.period_bound, self.platform_info, self.implicit_deadline
            )
        else:
            raise ValueError("task_type setting error")

    def _setup_taskset_factory(self):
        if self.taskset_factory_type == TasksetFactory:
            self.taskset_factory = TasksetFactory(
                self.task_factory, self.utilization_algorithm, self.platform_info
            )
        elif self.taskset_factory_type == TaskSubsetFactory:

            utilizations = UtilizationGenerationAlgorithm.generate_uniform_utilizations(
                self.num_task, self.platform_info.fastest_speed
            )
            self.tasks = [self.task_factory.create_task(u) for u in utilizations]
            self.taskset_factory = TaskSubsetFactory(
                self.tasks, self.utilization_algorithm, self.platform_info
            )
        else:
            raise ValueError("taskset_factory_type setting error")

    def generate_taskset(
        self,
        num_task: int,
        system_utilization: Optional[float] = None,
    ) -> Taskset:
        return self.taskset_factory.create_taskset(num_task, system_utilization)
