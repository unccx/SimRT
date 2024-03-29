import math
import unittest
from asyncio import Task

import simpy

from simRT import Simulator
from simRT.core.task import PeriodicTask, TaskInfo


class TestSimulator(unittest.TestCase):
    def test_add_task(self):
        self.sim = Simulator(taskinfos=[])
        self.hyper_period = 1
        triplets = [(2, 10, 10), (1, 10, 10), (10, 11, 11)]
        for i, triplet in enumerate(triplets):
            self.sim.add_task(TaskInfo(i, PeriodicTask, *triplet))
            self.hyper_period = math.lcm(self.hyper_period, triplet[2])

        for task, triplet in zip(self.sim.tasks, triplets):
            self.assertEqual(task.wcet, triplet[0])
            self.assertEqual(task.deadline, triplet[1])
            self.assertEqual(task.period, triplet[2])

        self.assertEqual(self.sim.hyper_period, self.hyper_period)
        self.assertEqual(self.sim.num_task, len(triplets))

    def test_run_until(self):
        triplets = [(25, 50, 50), (30, 75, 75)]
        taskinfos = [
            TaskInfo(i, PeriodicTask, *triplet) for i, triplet in enumerate(triplets)
        ]
        self.sim = Simulator(taskinfos)

        self.sim.run(until=self.sim.hyper_period - 10)
        self.assertEqual(self.sim.env.now, self.sim.hyper_period - 10)

        self.sim.run(until=self.sim.hyper_period + 10)
        self.assertEqual(self.sim.env.now, self.sim.hyper_period)

    def test_run_case(self):
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
        self.sim = Simulator(taskinfos)

        ret = self.sim.run(until=1000000, show_progress=True)
        print(ret)

    def test_run_meet_deadline(self):
        triplets = [(25, 50, 50), (30, 75, 75)]
        taskinfos = [
            TaskInfo(i, PeriodicTask, *triplet) for i, triplet in enumerate(triplets)
        ]
        self.sim = Simulator(taskinfos)

        meet_deadline = self.sim.run()
        self.assertTrue(meet_deadline)

    def test_run_miss_deadline(self):
        triplets = [(2, 10, 10), (1, 10, 10), (10, 11, 11)]
        taskinfos = [
            TaskInfo(i, PeriodicTask, *triplet) for i, triplet in enumerate(triplets)
        ]
        self.sim = Simulator(taskinfos, platform_info=[1, 0.5])

        meet_deadline = self.sim.run()
        self.assertFalse(meet_deadline)
