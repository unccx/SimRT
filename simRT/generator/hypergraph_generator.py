import bisect
import csv
import functools
import json
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path
from random import random, uniform
from typing import Optional

from tqdm import tqdm

from simRT import PeriodicTask, PlatformInfo, Simulator, TaskInfo

from .task_generator import TaskGenerator, Taskset


@dataclass(frozen=True, eq=True)
class HGConfig:
    platform_info: PlatformInfo
    num_node: int
    period_bound: tuple[int, int]

    def save_as_json(self, file_path: Path):
        with open(file_path, "w") as json_file:
            json.dump(self.__dict__, json_file, indent=4)

    @classmethod
    def from_json(cls, file_path: Path):
        with open(file_path, "r") as json_file:
            data = json.load(json_file)
            return cls(**data)


class TaskHypergraphGenerator:
    def __init__(self, hg_info: HGConfig):
        self.hg_info = hg_info
        self.task_gen = TaskGenerator(
            PeriodicTask, self.period_bound, self.platform_info
        )
        self.tasks: list[TaskInfo] = self._generate_tasks()

    @property
    def platform_info(self):
        return self.hg_info.platform_info

    @property
    def num_node(self):
        return self.hg_info.num_node

    @property
    def period_bound(self):
        return self.hg_info.period_bound

    def _generate_tasks(self) -> list[TaskInfo]:
        task_utilizations = []
        for _ in range(self.num_node):
            task_utilizations.append(uniform(0, self.platform_info.fastest_speed))

        return self.task_gen.generate_task(task_utilizations)

    def _select_taskset(self, target_utilizations: list[float]) -> Taskset:
        """
        从candidate_taskinfos中选择与target_utilizations中利用率相近的任务作为任务集
        """
        candidate_taskinfos = self.tasks
        candidate_taskinfos.sort(key=lambda x: x.utilization)
        candidate_utilizations = [
            taskinfo.utilization for taskinfo in candidate_taskinfos
        ]

        target_taskinfos = []
        for target_u in target_utilizations:
            index = bisect.bisect_left(candidate_utilizations, target_u)

            if index == 0:
                target_taskinfo = candidate_taskinfos[0]
            if index == len(candidate_taskinfos):
                target_taskinfo = candidate_taskinfos[-1]
            else:
                before = candidate_taskinfos[index - 1]
                after = candidate_taskinfos[index]
                target_taskinfo = min(
                    [after, before], key=lambda x: abs(x.utilization - target_u)
                )

            target_taskinfos.append(target_taskinfo)

        return target_taskinfos

    def generate_tasksets(
        self,
        num_taskset: int,
        taskset_size: int,
        system_utilization: Optional[float] = None,
    ) -> list[Taskset]:
        """
        根据系统利用率和任务集数量，任务集大小生成待判定可调度性的超边（任务集）列表
        """
        tasksets: list[Taskset] = []
        while len(tasksets) < num_taskset:
            if system_utilization is None:
                taskset_utilization = random() * self.platform_info.S_m
            else:
                taskset_utilization = system_utilization * self.platform_info.S_m

            utilizations = self.task_gen.UUniFast(
                taskset_utilization, taskset_size, self.platform_info.fastest_speed
            )
            taskset = self._select_taskset(utilizations)
            tasksets.append(taskset)
        return tasksets

    @staticmethod
    def nece_suff_test(
        taskset: Taskset, platform_info: PlatformInfo
    ) -> tuple[Taskset, bool]:
        sim = Simulator(taskset, platform_info)
        return taskset, sim.run()

    def generate_hyperedge_list(
        self,
        num_taskset: int,
        taskset_size: int,
        num_process: int = 4,
        system_utilization: Optional[float] = None,
    ) -> list[Taskset]:
        self.tasksets = self.generate_tasksets(
            num_taskset, taskset_size, system_utilization
        )

        self.schedulable: list[Taskset] = []
        with Pool(processes=num_process) as pool:
            results = pool.imap_unordered(
                functools.partial(
                    self.nece_suff_test, platform_info=self.platform_info
                ),
                self.tasksets,
            )
            for taskset, is_schedulable in tqdm(results, total=len(self.tasksets)):
                if is_schedulable:
                    self.schedulable.append(taskset)

        return self.schedulable

    def save_hyperedge_list(self, file_path: Path):
        with open(file_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            for hyperedge in self.schedulable:
                writer.writerow([task.id for task in hyperedge])
