import math
import unittest
from itertools import count
from unittest import mock

import simpy

import simRT
from simRT.core.job import Job


class TestJob(unittest.TestCase):

    def setUp(self) -> None:
        self.speed_list = [2, 1]
        self.env = simpy.Environment()
        self.platform = simRT.ProcessorPlatform(self.env, self.speed_list)

        triplets = [(25, 50, 50), (30, 75, 75)]

        self.tasks = []
        self.hyper_period = 1
        for triplet in triplets:
            self.hyper_period = math.lcm(self.hyper_period, triplet[2])

        for i, triplet in enumerate(triplets):
            task = mock.Mock()
            task.id = i
            task.env = self.env
            task.platform = self.platform
            task.wcet, task.deadline, task.period = triplet
            task._job_id_generator = count()

            task.jobs = []
            self.tasks.append(task)

        self.logs = []

    def test_job_id(self):
        for task in self.tasks:
            for i in range(10):
                task.jobs.append(Job(task))
                self.assertEqual(task.jobs[i].id, f"{task.id}_{i}")
                # print(task.jobs[i].id)

    def test_remaining_execution(self):
        job = Job(self.tasks[0])
        self.assertEqual(job.remaining_execution, job.wcet)
        job.accumulated_execution += 5
        self.assertEqual(job.remaining_execution, job.wcet - 5)

    def test_activate_job(self):

        def create_job(task, env: simpy.Environment):
            while True:
                job = Job(task)
                task.jobs.append(job)
                ret = yield job
                self.logs.append((env.now, ret))

        for task in self.tasks:
            self.env.process(create_job(task, self.env))

        self.env.run(until=self.hyper_period)

        # for record in self.log:
        #     print(record)
