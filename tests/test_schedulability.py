import unittest

from simRT import Schedulability
from simRT.core.model import Simulator
from simRT.core.processor import PlatformInfo
from simRT.core.task import PeriodicTask, TaskInfo
from simRT.generator import TaskGenerator, Taskset


class TestSchedulability(unittest.TestCase):

    def setUp(self) -> None:
        self.task_gen = TaskGenerator(
            task_type=PeriodicTask,
            period_bound=(5, 20),
            platform_info=[1, 0.5],
            implicit_deadline=True,
        )
        self.num_task = len(self.task_gen.platform_info.speed_list) * 2 + 1

    def test_G_EDF_sufficient_test_case1(self):
        triplets = [(2, 10, 10), (1, 10, 10), (10, 11, 11)]
        taskinfos = [
            TaskInfo(i, PeriodicTask, *triplet) for i, triplet in enumerate(triplets)
        ]
        schedulability = Schedulability.G_EDF_sufficient_test(
            Gamma=taskinfos, processors=PlatformInfo([1, 0.5])
        )
        self.assertFalse(schedulability)

    def test_G_EDF_sufficient_test_case2(self):
        num_task_set = 10
        tasksets = self.task_gen.generate_taskset(
            system_utilization=0.8, num_task=self.num_task, num_task_set=num_task_set
        )
        success = 0
        sim_success = 0
        sim_fail = 0
        for i, taskset in enumerate(tasksets):
            sim = Simulator(taskset, self.task_gen.platform_info)
            sim_schedulability = sim.run(show_progress=True)
            schedulability = Schedulability.G_EDF_sufficient_test(
                Gamma=taskset, processors=self.task_gen.platform_info
            )

            # print(f"[{i}] test:{schedulability}, sim:{sim_schedulability}")
            if schedulability is True:
                success += 1
                self.assertTrue(sim_schedulability)

            if sim_schedulability is False:
                sim_fail += 1
                self.assertFalse(schedulability)

            if sim_schedulability is True:
                sim_success += 1

        self.assertEqual(sim_fail + sim_success, num_task_set)
        # print(f"sim success rate: {sim_success/num_task_set}")
        # print(f"success rate: {success/num_task_set}")

    def test_G_EDF_sufficient_test_case3(self):
        triplets = [
            (1, 37, 37),
            (1, 43, 43),
            (1, 5, 5),
            (1, 25, 25),
            (1, 47, 47),
            (1, 26, 26),
            (1, 45, 45),
        ]
        taskinfos = [
            TaskInfo(i, PeriodicTask, *triplet) for i, triplet in enumerate(triplets)
        ]

        schedulability = Schedulability.G_EDF_sufficient_test(
            Gamma=taskinfos, processors=PlatformInfo([1, 0.5])
        )
        self.assertTrue(schedulability)
