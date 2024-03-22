import unittest

from simRT.core.processor import PlatformInfo
from simRT.core.task import PeriodicTask
from simRT.generator import TaskGenerator, Taskset


class TestTaskGenerator(unittest.TestCase):
    def setUp(self) -> None:
        self.speed_list: list = [1, 2]
        self.task_gen = TaskGenerator(
            task_type=PeriodicTask,
            period_bound=(5, 100),
            platform_info=PlatformInfo(self.speed_list),
            implicit_deadline=True,
        )

        self.S_m = self.task_gen.platform_info.S_m
        self.fastest_speed = self.task_gen.platform_info.fastest_speed

    def test_init(self):
        self.assertEqual(self.task_gen.platform_info.S_m, sum(self.speed_list))

    def test_generate_task(self):
        task_utilization_list = [0.2, 0.3, 0.2, 0.12, 0.33, 0.1]
        taskinfos = self.task_gen.generate_task(task_utilization_list)
        for i, taskinfo in enumerate(taskinfos):
            self.assertAlmostEqual(task_utilization_list[i], taskinfo.utilization)

    def test_UScaling_case1(self):
        for _ in range(100):
            taskset_u = 0.7
            task_utilization_list = self.task_gen.UScaling(
                taskset_u, 20, self.fastest_speed
            )
            taskinfos = self.task_gen.generate_task(task_utilization_list)

            taskset_u_gen = sum(taskinfo.utilization for taskinfo in taskinfos)

            self.assertAlmostEqual(taskset_u, taskset_u_gen)

    def test_UScaling_case2(self):
        for _ in range(100):
            taskset_u = 2.4
            task_utilization_list = self.task_gen.UScaling(
                taskset_u, 20, self.fastest_speed
            )
            taskinfos = self.task_gen.generate_task(task_utilization_list)
            taskset_u_gen = sum(taskinfo.utilization for taskinfo in taskinfos)
            self.assertAlmostEqual(taskset_u, taskset_u_gen)

    def test_UScaling_case3(self):
        taskset_u = 0
        with self.assertRaises(AssertionError):
            self.task_gen.UScaling(taskset_u, 20, self.fastest_speed)

        taskset_u = -1
        with self.assertRaises(AssertionError):
            self.task_gen.UScaling(taskset_u, 20, self.fastest_speed)

    def test_UFitting_case1(self):
        for _ in range(100):
            taskset_u = 0.7
            task_utilization_list = self.task_gen.UFitting(
                taskset_u, 20, self.fastest_speed
            )
            taskinfos = self.task_gen.generate_task(task_utilization_list)

            taskset_u_gen = sum(taskinfo.utilization for taskinfo in taskinfos)

            self.assertAlmostEqual(taskset_u, taskset_u_gen)

    def test_UFitting_case2(self):
        for _ in range(100):
            taskset_u = 2.4
            task_utilization_list = self.task_gen.UFitting(
                taskset_u, 20, self.fastest_speed
            )
            taskinfos = self.task_gen.generate_task(task_utilization_list)
            taskset_u_gen = sum(taskinfo.utilization for taskinfo in taskinfos)
            self.assertAlmostEqual(taskset_u, taskset_u_gen)

    def test_UFitting_case3(self):
        taskset_u = 0
        with self.assertRaises(AssertionError):
            self.task_gen.UFitting(taskset_u, 20, self.fastest_speed)

        taskset_u = -1
        with self.assertRaises(AssertionError):
            self.task_gen.UFitting(taskset_u, 20, self.fastest_speed)

    def test_UUniFast_case1(self):
        for _ in range(100):
            taskset_u = 0.7
            task_utilization_list = self.task_gen.UUniFast(
                taskset_u, 20, self.fastest_speed
            )
            taskinfos = self.task_gen.generate_task(task_utilization_list)
            taskset_u_gen = sum(taskinfo.utilization for taskinfo in taskinfos)

            self.assertAlmostEqual(taskset_u, taskset_u_gen)

    def test_UUniFast_case2(self):
        for _ in range(100):
            staskset_u = 2.4
            task_utilization_list = self.task_gen.UUniFast(
                staskset_u, 20, self.fastest_speed
            )
            taskinfos = self.task_gen.generate_task(task_utilization_list)
            taskset_u_gen = sum(taskinfo.utilization for taskinfo in taskinfos)
            self.assertAlmostEqual(staskset_u, taskset_u_gen)

    def test_UUniFast_case3(self):
        taskset_u = 0
        with self.assertRaises(AssertionError):
            self.task_gen.UUniFast(taskset_u, 20, self.fastest_speed)

        taskset_u = -1
        with self.assertRaises(AssertionError):
            self.task_gen.UUniFast(taskset_u, 20, self.fastest_speed)

    def test_generate_taskset_case1(self):
        tasksets: list[Taskset] = self.task_gen.generate_taskset(
            system_utilization=0.7,
            num_task=10,
            num_task_set=100,
        )

        for taskset in tasksets:
            self.assertAlmostEqual(
                sum(task.utilization for task in taskset) / self.S_m, 0.7
            )

    def test_generate_taskset_case2(self):
        tasksets: list[Taskset] = self.task_gen.generate_taskset(
            system_utilization=0.8,
            num_task=10,
            num_task_set=100,
            algorithm=self.task_gen.UFitting,
        )

        for taskset in tasksets:
            self.assertAlmostEqual(
                sum(task.utilization for task in taskset) / self.S_m, 0.8
            )

    def test_generate_taskset_case3(self):
        tasksets: list[Taskset] = self.task_gen.generate_taskset(
            system_utilization=0.8,
            num_task=10,
            num_task_set=100,
            algorithm=self.task_gen.UScaling,
        )

        for taskset in tasksets:
            self.assertAlmostEqual(
                sum(task.utilization for task in taskset) / self.S_m, 0.8
            )

    def test_generate_taskset_error_algorithm(self):
        with self.assertRaises(AssertionError):
            tasksets: list[Taskset] = self.task_gen.generate_taskset(
                system_utilization=0.7,
                num_task=10,
                num_task_set=100,
                algorithm=self.setUp,
            )

    def test_generate_taskset_error_system_utilization(self):
        with self.assertRaises(AssertionError):
            tasksets: list[Taskset] = self.task_gen.generate_taskset(
                system_utilization=1.1,
                num_task=10,
                num_task_set=100,
                algorithm=self.setUp,
            )

        with self.assertRaises(AssertionError):
            tasksets: list[Taskset] = self.task_gen.generate_taskset(
                system_utilization=0,
                num_task=10,
                num_task_set=100,
                algorithm=self.setUp,
            )
