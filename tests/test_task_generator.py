import unittest

from simRT.core.processor import PlatformInfo
from simRT.core.task import TaskInfo
from simRT.generator.task_factory import (
    PeriodicTaskFactory,
    UtilizationGenerationAlgorithm,
)


class TestPeriodicTaskFactory(unittest.TestCase):

    def setUp(self):
        self.platform_info = PlatformInfo([1, 2, 3])
        self.factory = PeriodicTaskFactory(
            (10, 100), self.platform_info, implicit_deadline=True
        )

    def test_create_task_valid_utilization(self):
        task_utilization = 0.5
        task = self.factory.create_task(task_utilization)
        self.assertIsInstance(task, TaskInfo)
        self.assertEqual(task.wcet, task.period * task_utilization)
        self.assertEqual(task.deadline, task.period)

    def test_create_task_invalid_utilization(self):
        with self.assertRaises(AssertionError):
            self.factory.create_task(
                5
            )  # Invalid utilization greater than fastest_speed

    def test_create_task_non_implicit_deadline(self):
        factory = PeriodicTaskFactory(
            (10, 100), self.platform_info, implicit_deadline=False
        )
        task_utilization = 0.5
        task = factory.create_task(task_utilization)
        self.assertIsInstance(task, TaskInfo)
        self.assertTrue(task.deadline <= task.period)
        self.assertTrue(task.deadline >= (task.wcet / self.platform_info.fastest_speed))


class TestUtilizationGenerationAlgorithm(unittest.TestCase):

    def setUp(self):
        self.fastest_speed = 1.0

    def test_generate_uniform_utilizations(self):
        num_task = 5
        utilizations = UtilizationGenerationAlgorithm.generate_uniform_utilizations(
            num_task, self.fastest_speed
        )
        self.assertEqual(len(utilizations), num_task)
        for u in utilizations:
            self.assertGreaterEqual(u, 0)
            self.assertLessEqual(u, self.fastest_speed)

    def test_UScaling(self):
        taskset_utilization = 2.0
        num_task = 5
        utilizations = UtilizationGenerationAlgorithm.UScaling(
            taskset_utilization, num_task, self.fastest_speed
        )
        self.assertEqual(len(utilizations), num_task)
        self.assertAlmostEqual(sum(utilizations), taskset_utilization, delta=0.01)
        for u in utilizations:
            self.assertLessEqual(u, self.fastest_speed)

    def test_UFitting(self):
        taskset_utilization = 2.0
        num_task = 5
        utilizations = UtilizationGenerationAlgorithm.UFitting(
            taskset_utilization, num_task, self.fastest_speed
        )
        self.assertEqual(len(utilizations), num_task)
        self.assertAlmostEqual(sum(utilizations), taskset_utilization, delta=0.01)
        for u in utilizations:
            self.assertLessEqual(u, self.fastest_speed)

    def test_UUniFast(self):
        taskset_utilization = 2.0
        num_task = 5
        utilizations = UtilizationGenerationAlgorithm.UUniFast(
            taskset_utilization, num_task, self.fastest_speed
        )
        self.assertEqual(len(utilizations), num_task)
        self.assertAlmostEqual(sum(utilizations), taskset_utilization, delta=0.01)
        for u in utilizations:
            self.assertLessEqual(u, self.fastest_speed)
