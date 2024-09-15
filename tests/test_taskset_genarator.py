import unittest
from random import uniform
from unittest.mock import MagicMock, Mock, patch

from simRT.core.processor import PlatformInfo, SpeedType
from simRT.core.task import PeriodicTask, TaskInfo
from simRT.generator.task_factory import (
    PeriodicTaskFactory,
    UtilizationGenerationAlgorithm,
)
from simRT.generator.taskset_generator import (
    TasksetFactory,
    TasksetGenerator,
    TaskSubsetFactory,
)


class TestTasksetFactory(unittest.TestCase):

    def setUp(self):
        self.platform_info = PlatformInfo([1, 2, 3])
        self.task_factory = MagicMock()
        self.utilization_algorithm = UtilizationGenerationAlgorithm.UScaling
        self.factory = TasksetFactory(
            self.task_factory, self.utilization_algorithm, self.platform_info
        )

    def test_create_taskset_valid_utilization(self):
        num_task = 5
        system_utilization = 0.8

        # Mock the create_task method
        self.task_factory.create_task.side_effect = lambda u: TaskInfo(
            id=0, type=PeriodicTask, wcet=u, deadline=1, period=1
        )

        taskset = self.factory.create_taskset(num_task, system_utilization)
        self.assertEqual(len(taskset), num_task)
        self.assertAlmostEqual(
            sum(task.utilization for task in taskset),
            system_utilization * self.platform_info.S_m,
            delta=0.01,
        )

    def test_create_taskset_random_utilization(self):
        num_task = 5

        # Mock the create_task method
        self.task_factory.create_task.side_effect = lambda u: TaskInfo(
            id=0, type=PeriodicTask, wcet=u, deadline=1, period=1
        )

        taskset = self.factory.create_taskset(num_task)
        self.assertEqual(len(taskset), num_task)
        self.assertTrue(
            0 < sum(task.utilization for task in taskset) / self.platform_info.S_m < 1
        )


class TestTaskSubsetFactory(unittest.TestCase):

    def setUp(self):
        self.platform_info = PlatformInfo([1])
        self.tasks = [
            TaskInfo(id=i, type=PeriodicTask, wcet=1, deadline=i, period=i)
            for i in range(1, 10001)
        ]
        self.utilization_algorithm = UtilizationGenerationAlgorithm.UScaling
        self.factory = TaskSubsetFactory(
            self.tasks, self.utilization_algorithm, self.platform_info
        )

    def test_create_taskset_valid_utilization(self):
        num_task = 1000
        system_utilization = 0.8
        taskset = self.factory.create_taskset(num_task, system_utilization)
        self.assertEqual(len(taskset), num_task)
        self.assertAlmostEqual(
            sum(task.utilization for task in taskset),
            system_utilization * self.platform_info.S_m,
            delta=0.01,
        )

    def test_create_taskset_random_utilization(self):
        num_task = 5
        taskset = self.factory.create_taskset(num_task)
        self.assertEqual(len(taskset), num_task)
        self.assertGreater(sum(task.utilization for task in taskset), 0)

    def test_select_task(self):
        target_utilization = 0.5
        selected_task = self.factory._select_task(target_utilization)
        self.assertIsInstance(selected_task, TaskInfo)


class TestTasksetGenerator(unittest.TestCase):

    def setUp(self):
        self.generator = TasksetGenerator()

    def test_set_platform_info_sequence(self):
        self.generator.set_platform_info([1.0, 2.0, 3.0])
        self.assertIsInstance(self.generator.platform_info, PlatformInfo)
        self.assertEqual(len(self.generator.platform_info.speed_list), 3)

    def test_set_platform_info_instance(self):
        platform_info = PlatformInfo([1.0])
        self.generator.set_platform_info(platform_info)
        self.assertIs(self.generator.platform_info, platform_info)

    def test_set_platform_info_invalid(self):
        with self.assertRaises(AssertionError):
            self.generator.set_platform_info(123)  # type: ignore

    def test_set_period_bound(self):
        self.generator.set_period_bound((10, 100))
        self.assertEqual(self.generator.period_bound, (10, 100))

    def test_setup_missing_task_type(self):
        with self.assertRaises(AttributeError):
            self.generator.setup()

    def test_setup_missing_taskset_factory(self):
        self.generator.set_task_type(PeriodicTask)
        with self.assertRaises(AttributeError):
            self.generator.setup()

    def test_setup_missing_platform_info(self):
        self.generator.set_task_type(PeriodicTask)
        self.generator.set_taskset_factory(TasksetFactory)
        with self.assertRaises(AttributeError):
            self.generator.setup()

    def test_setup_missing_period_bound(self):
        self.generator.set_task_type(PeriodicTask)
        self.generator.set_taskset_factory(TasksetFactory)
        self.generator.set_platform_info(PlatformInfo([1.0]))
        with self.assertRaises(AttributeError):
            self.generator.setup()

    def test_setup_correct(self):
        self.generator.set_task_type(PeriodicTask)
        self.generator.set_taskset_factory(TasksetFactory)
        self.generator.set_platform_info(PlatformInfo([1.0]))
        self.generator.set_period_bound((10, 100))
        self.generator.setup()
        self.assertIsInstance(self.generator.task_factory, PeriodicTaskFactory)
        self.assertIsInstance(self.generator.taskset_factory, TasksetFactory)

    def test_generate_taskset(self):
        self.generator.set_task_type(PeriodicTask)
        self.generator.set_taskset_factory(TasksetFactory)
        self.generator.set_platform_info(PlatformInfo([1, 2, 3]))
        self.generator.set_period_bound((10, 100))
        self.generator.setup()
        taskset = self.generator.generate_taskset(5, 0.8)
        self.assertEqual(len(taskset), 5)
        self.assertAlmostEqual(
            sum(task.utilization for task in taskset)
            / self.generator.platform_info.S_m,
            0.8,
        )

    def test_generate_taskset_with_subset_factory(self):
        self.generator.set_task_type(PeriodicTask)
        self.generator.set_taskset_factory(TaskSubsetFactory)
        self.generator.set_platform_info(PlatformInfo([1, 2, 3]))
        self.generator.set_period_bound((10, 100))
        self.generator.set_num_task(10000)
        self.generator.setup()
        taskset = self.generator.generate_taskset(5, 0.8)
        self.assertEqual(len(taskset), 5)
        self.assertAlmostEqual(
            sum(task.utilization for task in taskset)
            / self.generator.platform_info.S_m,
            0.8,
            delta=0.001,
        )
