import unittest
from unittest.mock import patch

from simrt.core.model import Simulator
from simrt.core.processor import PlatformInfo
from simrt.core.task import PeriodicTask, TaskInfo
from simrt.generator.taskset_generator import (
    TasksetFactory,
    TasksetGenerator,
    TaskSubsetFactory,
)
from simrt.utils.schedulability_test import GlobalEDFTest, SimulationTest, TestFactory


class TestGlobalEDFTest(unittest.TestCase):

    def setUp(self):
        triplets = [(2, 10, 10), (1, 10, 10), (10, 11, 11)]
        self.taskset = [
            TaskInfo(i, PeriodicTask, *triplet) for i, triplet in enumerate(triplets)
        ]
        self.platform = PlatformInfo(speed_list=[1, 0.5])
        self.sufficient_test = GlobalEDFTest()

    def test_dbf(self):
        result = GlobalEDFTest._DBF(self.taskset[0], 25)
        self.assertEqual(result, 4)

        result = GlobalEDFTest._DBF(self.taskset[0], 15)
        self.assertEqual(result, 2)

        result = GlobalEDFTest._DBF(self.taskset[0], 10)
        self.assertEqual(result, 2)

        result = GlobalEDFTest._DBF(self.taskset[0], 5)
        self.assertEqual(result, 2)

    def test_load(self):
        result = GlobalEDFTest._LOAD(self.taskset)
        self.assertGreater(result, 0)

    def test_test(self):
        result = self.sufficient_test.test(self.taskset, self.platform)
        self.assertIsInstance(result, bool)
        self.assertFalse(result)

    def test_case(self):
        triplets = [
            (1, 37, 37),
            (1, 43, 43),
            (1, 5, 5),
            (1, 25, 25),
            (1, 47, 47),
            (1, 26, 26),
            (1, 45, 45),
        ]
        self.taskset = [
            TaskInfo(i, PeriodicTask, *triplet) for i, triplet in enumerate(triplets)
        ]
        schedulability = self.sufficient_test.test(self.taskset, self.platform)
        self.assertTrue(schedulability)

    def test_case1(self):
        num_task_set = 1000
        generater = (
            TasksetGenerator()
            .set_period_bound((1, 10))
            .set_task_type(PeriodicTask)
            .set_platform_info([1, 0.5])
            .set_implicit_deadline(True)
            .set_taskset_factory(TasksetFactory)
            .setup()
        )
        tasksets = [
            generater.generate_taskset(num_task=5, system_utilization=0.99)
            for _ in range(num_task_set)
        ]

        success = 0
        sim_success = 0
        sim_fail = 0
        for i, taskset in enumerate(tasksets):
            sim = Simulator(taskset, generater.platform_info)
            sim_schedulability = sim.run(show_progress=False)
            schedulability = self.sufficient_test.test(taskset, generater.platform_info)

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


class TestSimulationTest(unittest.TestCase):

    def setUp(self):
        triplets = [(2, 10, 10), (1, 10, 10), (10, 11, 11)]
        self.taskset = [
            TaskInfo(i, PeriodicTask, *triplet) for i, triplet in enumerate(triplets)
        ]
        self.platform = PlatformInfo(speed_list=[1, 0.5])
        self.test = SimulationTest()

    @patch.object(Simulator, "run", return_value=True)
    def test_simulation(self, mock_run):
        result = self.test.test(self.taskset, self.platform)
        self.assertTrue(result)
        mock_run.assert_called_once_with(until=None, show_progress=False)


class TestTestFactory(unittest.TestCase):

    def test_create_global_edf_test(self):
        test = TestFactory.create_test("GlobalEDFTest")
        self.assertIsInstance(test, GlobalEDFTest)

    def test_create_simulation_test(self):
        test = TestFactory.create_test("SimulationTest")
        self.assertIsInstance(test, SimulationTest)

    def test_create_invalid_test(self):
        with self.assertRaises(ValueError):
            TestFactory.create_test("InvalidTest")
