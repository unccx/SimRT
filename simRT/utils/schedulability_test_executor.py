import functools
import os
from abc import ABC, abstractmethod
from multiprocessing import Pool
from pathlib import Path
from typing import Callable, Sequence

import psutil
from tqdm import tqdm

from simRT import PlatformInfo
from simRT.core.task import TaskInfo
from simRT.generator.task_factory import Taskset
from simRT.utils.schedulability_analyzer import SchedulabilityAnalyzer
from simRT.utils.task_storage import TaskStorage


class PersistenceStrategy(ABC):
    def __init__(self, data_path: Path) -> None:
        self.data_path = data_path
        self.data_path.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def save_task(self, task: TaskInfo) -> None:
        pass

    @abstractmethod
    def save_taskset(self, taskset: Taskset, **kwargs) -> None:
        pass

    @abstractmethod
    def close(self):
        pass


class SqlitePersistence(PersistenceStrategy):

    def connect(self) -> None:
        self.task_db = TaskStorage(self.data_path / "data.sqlite")

    def save_task(self, task: TaskInfo):
        self.task_db.insert_task(task)

    def save_taskset(self, platform: PlatformInfo, taskset: Taskset, **kwargs) -> None:
        exact_test_result = kwargs.get("exact_test_result")
        suff_test_result = kwargs.get("suff_test_result")

        taskset_utilization = sum(task.utilization for task in taskset)
        system_utilization = taskset_utilization / platform.S_m

        self.task_db.insert_taskset(
            taskset, exact_test_result, suff_test_result, system_utilization
        )

    def close(self):
        self.task_db.commit()
        self.task_db.close()


class ExecutionStrategy(ABC):
    @abstractmethod
    def execute(self, test_func: Callable, tasksets: Sequence[Taskset]) -> None:
        pass


class ParallelStrategy(ExecutionStrategy):

    def __init__(self, num_process: int, chunksize: int, show_progress: bool = False):
        self.num_process = num_process
        self.chunksize = chunksize
        self.show_progress = show_progress

    @staticmethod
    def _set_high_priority():
        """为进程设置高优先级的内部函数"""
        # 获取当前进程的PID
        pid = os.getpid()
        # 获取当前进程对象
        current_process = psutil.Process(pid)
        if os.name == "posix":  # linux
            try:
                current_process.nice(-10)  # 高优先级
            except psutil.AccessDenied:
                print(
                    "Access denied: Unable to set high priority. Try running as root."
                )
        elif os.name == "nt":  # windows
            current_process.nice(psutil.HIGH_PRIORITY_CLASS)
        else:
            raise OSError("Unsupported operating system")

    def execute(self, test_func: Callable, tasksets: Sequence[Taskset]) -> None:
        """多进程进行可调度性测试"""
        with Pool(
            processes=self.num_process, initializer=self._set_high_priority
        ) as pool:
            results = pool.imap_unordered(test_func, tasksets, self.chunksize)
            for result in tqdm(
                results, total=len(tasksets), disable=not self.show_progress
            ):
                pass


class SerialStrategy(ExecutionStrategy):
    def execute(self, test_func: Callable, tasksets: Sequence[Taskset]) -> None:
        for taskset in tasksets:
            test_func(taskset)


class SchedulabilityTestExecutor:

    def __init__(
        self,
        execution_strategy: ExecutionStrategy,
        persistence_strategy: PersistenceStrategy,
        test_analyzer: SchedulabilityAnalyzer,
    ):
        self._execution_strategy = execution_strategy
        self._persistence_strategy = persistence_strategy
        self._test_analyzer = test_analyzer

    @staticmethod
    def _analyze_and_save_taskset(
        taskset: Taskset,
        platform: PlatformInfo,
        persistence_strategy: PersistenceStrategy,
        test_analyzer: SchedulabilityAnalyzer,
    ):
        persistence_strategy.connect()
        result = test_analyzer.analyze(taskset, platform)
        for task in taskset:
            persistence_strategy.save_task(task)
        persistence_strategy.save_taskset(platform=platform, taskset=taskset, **result)
        persistence_strategy.close()

    def execute(self, tasksets: Sequence[Taskset], platform: PlatformInfo) -> None:
        # 交给执行模型执行的函数需要是 picklable 序列化，这样才能多进程执行
        func = functools.partial(
            self._analyze_and_save_taskset,
            platform=platform,
            persistence_strategy=self._persistence_strategy,
            test_analyzer=self._test_analyzer,
        )

        self._execution_strategy.execute(func, tasksets)
