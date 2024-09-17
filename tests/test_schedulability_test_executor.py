import unittest
from pathlib import Path

from simrt import PlatformInfo
from simrt.core.task import PeriodicTask, TaskInfo
from simrt.generator.task_factory import Taskset
from simrt.utils.schedulability_analyzer import SchedulabilityAnalyzer
from simrt.utils.schedulability_test import TestFactory
from simrt.utils.schedulability_test_executor import (
    ParallelStrategy,
    SchedulabilityTestExecutor,
    SerialStrategy,
    SqlitePersistence,
)


class TestExecutionStrategy(unittest.TestCase):
    def setUp(self) -> None:
        task2 = TaskInfo(id=2, type=PeriodicTask, wcet=3, deadline=4, period=4)
        task1 = TaskInfo(id=1, type=PeriodicTask, wcet=5, deadline=6, period=7)
        task3 = TaskInfo(id=3, type=PeriodicTask, wcet=8, deadline=9, period=9)
        task4 = TaskInfo(id=4, type=PeriodicTask, wcet=8, deadline=9, period=9)

        self.tasksets: list[Taskset] = [
            [task1, task2, task3],
            [task2, task3],
            [task1],
            [task1, task2, task3, task4],
        ]
        ns_result = [True, True, True, False]
        sufficient = [False, True, False, False]

    @staticmethod
    def _test_func(taskset: Taskset):
        task2 = TaskInfo(id=2, type=PeriodicTask, wcet=3, deadline=4, period=4)
        task1 = TaskInfo(id=1, type=PeriodicTask, wcet=5, deadline=6, period=7)
        task3 = TaskInfo(id=3, type=PeriodicTask, wcet=8, deadline=9, period=9)
        task4 = TaskInfo(id=4, type=PeriodicTask, wcet=8, deadline=9, period=9)

        tasksets: list[Taskset] = [
            [task1, task2, task3],
            [task2, task3],
            [task1],
            [task1, task2, task3, task4],
        ]

        assert taskset in tasksets, "_test_func"

    def test_parallel_strategy(self):
        strategy = ParallelStrategy(num_process=2, chunksize=1)
        strategy.execute(self._test_func, self.tasksets)

    def test_serial_strategy(self):
        strategy = SerialStrategy()
        strategy.execute(self._test_func, self.tasksets)


class TestSchedulabilityTestExecutor(unittest.TestCase):

    def setUp(self):
        # Path("./data/").mkdir(parents=True, exist_ok=True)
        self.analyzer = SchedulabilityAnalyzer()
        self.analyzer.set_exact_test(TestFactory.create_test("SimulationTest"))
        self.analyzer.set_sufficient_test(TestFactory.create_test("GlobalEDFTest"))

        self.persistence_strategy = SqlitePersistence(data_path=Path("./data"))

        task2 = TaskInfo(id=2, type=PeriodicTask, wcet=3, deadline=4, period=4)
        task1 = TaskInfo(id=1, type=PeriodicTask, wcet=5, deadline=6, period=7)
        task3 = TaskInfo(id=3, type=PeriodicTask, wcet=8, deadline=9, period=9)
        task4 = TaskInfo(id=4, type=PeriodicTask, wcet=8, deadline=9, period=9)

        self.tasksets: list[Taskset] = [
            [task1, task2, task3],
            [task2, task3],
            [task1],
            [task1, task2, task3, task4],
        ]
        self.platform = PlatformInfo([1, 2, 3])

    def tearDown(self) -> None:
        Path("./data/data.sqlite").unlink()
        pass

    def test_execute_with_serial_strategy(self):
        self.execution_strategy = SerialStrategy()
        self.executor = SchedulabilityTestExecutor(
            test_analyzer=self.analyzer,
            execution_strategy=self.execution_strategy,
            persistence_strategy=self.persistence_strategy,
        )
        self.executor.execute(self.tasksets, self.platform)

    def test_execute_with_parallel_strategy(self):
        self.execution_strategy = ParallelStrategy(num_process=2, chunksize=1)
        self.executor = SchedulabilityTestExecutor(
            test_analyzer=self.analyzer,
            execution_strategy=self.execution_strategy,
            persistence_strategy=self.persistence_strategy,
        )
        self.executor.execute(self.tasksets, self.platform)


if __name__ == "__main__":
    unittest.main()
