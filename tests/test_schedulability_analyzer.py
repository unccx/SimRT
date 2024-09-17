import unittest

from simrt.core.processor import PlatformInfo
from simrt.core.task import PeriodicTask, TaskInfo
from simrt.utils.schedulability_analyzer import SchedulabilityAnalyzer
from simrt.utils.schedulability_test import GlobalEDFTest, SimulationTest, TestFactory


class TestSchedulabilityAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = SchedulabilityAnalyzer()
        triplets = [(2, 10, 10), (1, 10, 10), (5, 11, 11)]
        self.taskset = [
            TaskInfo(i, PeriodicTask, *triplet) for i, triplet in enumerate(triplets)
        ]
        self.platform = PlatformInfo(speed_list=[1, 0.5])

    def test_analyze_with_sufficient_test(self):
        suff_test = GlobalEDFTest()
        self.analyzer.set_sufficient_test(suff_test)
        result = self.analyzer.analyze(self.taskset, self.platform)
        self.assertIsNotNone(result["suff_test_result"])
        self.assertIsNone(result["exact_test_result"])

    def test_analyze_with_exact_test(self):
        exact_test = SimulationTest()
        self.analyzer.set_exact_test(exact_test)
        result = self.analyzer.analyze(self.taskset, self.platform)
        self.assertIsNone(result["suff_test_result"])
        self.assertIsNotNone(result["exact_test_result"])

    def test_analyze_with_both_tests(self):
        suff_test = GlobalEDFTest()
        exact_test = SimulationTest()
        self.analyzer.set_sufficient_test(suff_test)
        self.analyzer.set_exact_test(exact_test)
        result = self.analyzer.analyze(self.taskset, self.platform)
        self.assertIsNotNone(result["suff_test_result"])
        self.assertIsNotNone(result["exact_test_result"])


if __name__ == "__main__":
    unittest.main()
