from __future__ import annotations

from dataclasses import dataclass
from itertools import count
from typing import TYPE_CHECKING, Generator, Iterator, Optional, Type

import simpy
from simpy import Environment, Process
from simpy.core import SimTime

from .job import Job
from .processor import ProcessorPlatform


@dataclass(frozen=True, order=True)
class TaskInfo:
    id: int
    type: Type[GenericTask]
    wcet: SimTime
    deadline: SimTime
    period: SimTime

    @property
    def utilization(self) -> float:
        return self.wcet / self.period

    def task_from_info(self, platform) -> GenericTask:
        if self.type is PeriodicTask:
            return self.type(platform, self)
        assert False, "The current type is only PeriodicTask"


class GenericTask(Process):

    def __init__(self, platform: ProcessorPlatform, taskinfo: TaskInfo):
        super().__init__(platform._env, self.create_job())
        self.task_info = taskinfo
        self.platform: ProcessorPlatform = platform
        self._job_id_generator: Iterator = count()
        self.jobs: list[Job] = []

    @property
    def id(self):
        return self.task_info.id

    @property
    def wcet(self) -> SimTime:
        """Worst-Case Execution Time."""
        return self.task_info.wcet

    @property
    def deadline(self) -> SimTime:
        """Relative deadline"""
        return self.task_info.deadline

    @property
    def period(self) -> SimTime:
        """Job arrival cycle or minimum interarrival time"""
        return self.task_info.period

    @property
    def utilization(self) -> float:
        """Job arrival cycle or minimum interarrival time"""
        return self.task_info.utilization

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
            yield self.env.timeout(self.period)
