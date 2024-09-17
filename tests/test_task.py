import math
import unittest
from unittest import mock

import simpy

import simrt
from simrt.core.task import GenericTask, PeriodicTask, TaskInfo


class TestTaskInfo(unittest.TestCase):

    def test_init(self):
        task_info = TaskInfo(id=2, type=PeriodicTask, wcet=10, deadline=15, period=20)
        self.assertEqual(task_info.utilization, 10 / 20)
        self.assertEqual(task_info.density, 10 / 15)
        self.assertEqual(task_info.wcet, 10)
        self.assertEqual(task_info.deadline, 15)
        self.assertEqual(task_info.period, 20)

        self.env = simpy.Environment()
        self.platform = simrt.ProcessorPlatform(self.env)

        task = task_info.as_task(self.platform)
        self.assertIsInstance(task, PeriodicTask)


class TestPeriodicTask(unittest.TestCase):
    def setUp(self) -> None:
        self.env = simpy.Environment()

    def init(self, speed_list, triplets):

        self.speed_list = speed_list
        self.platform = simrt.ProcessorPlatform(self.env, self.speed_list)

        self.hyper_period = 1
        self.tasks = []
        for i, triplet in enumerate(triplets):
            self.hyper_period = math.lcm(self.hyper_period, triplet[2])
            taskinfo = mock.Mock()
            taskinfo.id = i
            taskinfo.wcet, taskinfo.deadline, taskinfo.period = triplet
            task = PeriodicTask(platform=self.platform, taskinfo=taskinfo)
            self.tasks.append(task)

    def test_miss_deadline(self):
        triplets = [(2, 10, 10), (1, 10, 10), (10, 11, 11)]
        self.init(speed_list=[1, 0.5], triplets=triplets)

        self.assertEqual(self.hyper_period, 110)

        with self.assertRaises(simpy.Interrupt, msg="2_0 miss deadline at [11]"):
            self.env.run(until=self.hyper_period)

        logs = {
            "0_0": {"arrival": 0, "start": 0, "end": 2.0, "speed": 1},
            "0_1": {
                "arrival": 10,
                "start": 10,
                "end": 12.0,
                "speed": 0.5,
                "next_speed": 1,
                "remaining": 1.0,
            },
            "1_0": {"arrival": 0, "start": 0, "end": 2.0, "speed": 0.5},
            "2_0": {"arrival": 0, "start": 2.0, "end": 12.0, "speed": 1},
        }

        for task in self.tasks:
            for job in task.jobs:
                for log in job.logs:
                    self.assertEqual(logs[job.id], log)
                    # print(f"{job.id}: {log}")

    def test_run(self):
        triplets = [(25, 50, 50), (30, 75, 75)]
        self.init(speed_list=[1], triplets=triplets)

        self.assertEqual(self.hyper_period, 150)

        logs = {
            "0_0": {"arrival": 0, "start": 0, "end": 25.0, "speed": 1},
            "0_1": {"arrival": 50, "start": 55.0, "end": 80.0, "speed": 1},
            "0_2": {"arrival": 100, "start": 110.0, "end": 135.0, "speed": 1},
            "1_0": {"arrival": 0, "start": 25.0, "end": 55.0, "speed": 1},
            "1_1": {"arrival": 75, "start": 80.0, "end": 110.0, "speed": 1},
        }

        self.env.run(until=self.hyper_period)

        for task in self.tasks:
            for job in task.jobs:
                for log in job.logs:
                    self.assertEqual(logs[job.id], log)
                    # print(f"{job.id}: {log}")
