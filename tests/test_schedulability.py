import unittest

from simRT import Schedulability
from simRT.core.task import PeriodicTask, TaskInfo


class TestSchedulability(unittest.TestCase):
    def test_G_EDF_sufficient_test_case1(self):
        triplets = [(2, 10, 10), (1, 10, 10), (10, 11, 11)]
        taskinfos = [
            TaskInfo(i, PeriodicTask, *triplet) for i, triplet in enumerate(triplets)
        ]
        schedulability = Schedulability.G_EDF_sufficient_test(
            Gamma=taskinfos, speed_list=[1, 0.5]
        )
        print(schedulability)
