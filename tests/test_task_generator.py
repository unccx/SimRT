import unittest

from simRT.core.task import PeriodicTask
from simRT.generator import TaskGenerator


class TestTaskGenerator(unittest.TestCase):
    def setUp(self) -> None:
        self.speed_list = [1, 2]
        self.task_gen = TaskGenerator(
            task_type=PeriodicTask,
            period_bound=(5, 100),
            speed_list=self.speed_list,  # type: ignore
            implicit_deadline=True,
        )

    def test_init(self):
        self.assertEqual(self.task_gen.sum_of_processor_speeds, sum(self.speed_list))
        self.assertEqual(self.task_gen.S_m, sum(self.speed_list))

    def test_generate_task(self):
        task_utilization_list = [0.2, 0.3, 0.2, 0.12, 0.33, 0.1]
        taskinfos = self.task_gen.generate_task(task_utilization_list)
        for i, taskinfo in enumerate(taskinfos):
            self.assertAlmostEqual(task_utilization_list[i], taskinfo.utilization)

    def test_UScaling_algorithm(self):
        sys_u = 0.7
        taskinfos = self.task_gen.UScaling_algorithm(sys_u, 20)

        sys_u_gen = (
            sum(taskinfo.utilization for taskinfo in taskinfos) / self.task_gen.S_m
        )

        self.assertAlmostEqual(sys_u, sys_u_gen)
