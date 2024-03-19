from __future__ import annotations

from itertools import count
from typing import TYPE_CHECKING, Generator, Iterator, Optional

import simpy
from simpy import Environment, Process
from simpy.core import SimTime

from .job import Job
from .processor import ProcessorPlatform


class GenericTask(Process):

    def __init__(self, id: int, env: Environment, platform: ProcessorPlatform):
        super().__init__(env, self.create_job())
        self.id: int = id
        self.platform: ProcessorPlatform = platform
        self._job_id_generator: Iterator = count()
        self.jobs: list[Job] = []

        self.wcet: SimTime
        """Worst-Case Execution Time."""
        self.deadline: SimTime
        """Relative deadline"""
        self.period: SimTime
        """Job arrival cycle or minimum interarrival time"""

    @property
    def job_count(self) -> int:
        """The number of jobs that have been generated"""
        return len(self.jobs)

    @property
    def job(self) -> Optional[Job]:
        """Recently generated job"""
        if len(self.jobs) > 0:
            return self.jobs[-1]

    def __lt__(self, other: GenericTask):
        return self.id < other.id

    def is_active(self) -> bool:
        return self.job is not None and self.job.is_active()

    def create_job(self) -> Generator:
        raise NotImplementedError(self)


class PeriodicTask(GenericTask):
    def create_job(self) -> Generator:
        while True:
            job = Job(self)
            self.jobs.append(job)
            yield self.env.timeout(self.deadline)
