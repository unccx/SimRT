import bisect
import functools
import json
import os
import time
from dataclasses import asdict, dataclass
from math import ceil
from multiprocessing import Pool
from pathlib import Path
from random import random, uniform
from typing import Optional

import psutil
from tqdm import tqdm

from simRT import PeriodicTask, PlatformInfo, Simulator, TaskInfo
from simRT.core.model import SimTime
from simRT.generator.task_generator import TaskGenerator, Taskset
from simRT.utils.schedulability import Schedulability
from simRT.utils.task_storage import TaskStorage


@dataclass(frozen=True, eq=True)
class HGConfig:
    platform_info: PlatformInfo
    num_node: int  # 任务节点数量太少会导致被选择任务的利用率与期望的利用率相差过大
    period_bound: tuple[int, int]

    def save_as_json(self, file_path: Path):
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open(mode="w") as json_file:
            json.dump(asdict(self), json_file, indent=4)

    @classmethod
    def from_json(cls, file_path: Path):
        with file_path.open(mode="r") as json_file:
            data = json.load(json_file)
            data["platform_info"] = PlatformInfo(data["platform_info"]["speed_list"])
            data["period_bound"] = tuple(data["period_bound"])
            return cls(**data)


class TaskHypergraphGenerator:

    def __init__(self, hg_info: HGConfig, data_path: Optional[Path] = None):
        self.hg_info = hg_info
        self.task_gen = TaskGenerator(
            PeriodicTask, self.period_bound, self.platform_info
        )
        self.tasks: list[TaskInfo] = self._generate_tasks()

        current_time = time.localtime()
        formatted_time = time.strftime("%Y-%m-%d_%H-%M-%S", current_time)
        self.data_id: str = formatted_time

        self.data_path: Path = (
            (Path(f"./data/") / self.data_id) if data_path is None else data_path
        )

        self.data_path.mkdir(parents=True, exist_ok=True)

        self.hg_info.save_as_json(self.data_path / "config.json")
        self.task_db = TaskStorage(self.data_path / "data.sqlite")

        self.task_db.clear()
        for task in self.tasks:
            self.task_db.insert_task(task)
        self.task_db.commit()

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
        self.task_utilizations = []
        for _ in range(self.num_node):
            self.task_utilizations.append(uniform(0, self.platform_info.fastest_speed))

        self.task_utilizations.sort()
        return self.task_gen.generate_task(self.task_utilizations)

    def _select_taskset(self, target_utilizations: list[float]) -> Taskset:
        """
        从candidate_taskinfos中选择与target_utilizations中利用率相近的任务作为任务集
        任务节点数量太少会导致被选择任务的利用率与期望的利用率相差过大
        """
        target_taskinfos = []
        for target_u in target_utilizations:
            index = bisect.bisect_left(self.task_utilizations, target_u)

            if index == 0:
                target_taskinfo = self.tasks[0]
            if index == len(self.tasks):
                target_taskinfo = self.tasks[-1]
            else:
                before = self.tasks[index - 1]
                after = self.tasks[index]
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
        如果 system_utilization is None，则随机生成系统利用率
        """
        tasksets: list[Taskset] = []
        for _ in range(num_taskset):
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
    def schedulability_test(
        taskset: Taskset,
        platform_info: PlatformInfo,
        db_path: Optional[Path] = None,
        cutoff: Optional[SimTime] = None,
        return_data: bool = False,
    ) -> Optional[tuple[Taskset, bool, bool]]:

        # 可调度性充分非必要条件
        sufficient = Schedulability.G_EDF_sufficient_test(taskset, platform_info)

        # 如果充分测试为可调度，则必定满足充要条件
        if sufficient is False:
            # 可调度性充要条件
            sim = Simulator(taskset, platform_info)
            ns_result = sim.run(until=cutoff)
        else:
            ns_result = True

        if db_path is not None:
            task_db = TaskStorage(db_path)
            taskset_u = sum(task.utilization for task in taskset)
            sys_u = taskset_u / platform_info.S_m
            task_db.insert_taskset(taskset, ns_result, sufficient, sys_u)
            task_db.commit()

        if return_data:
            return taskset, ns_result, sufficient

    @staticmethod
    def init_process():
        # 获取当前进程的PID
        pid = os.getpid()
        # 获取当前进程对象
        current_process = psutil.Process(pid)
        # 将当前进程的优先级设置为高
        current_process.nice(psutil.HIGH_PRIORITY_CLASS)

    def parallel_simulate(
        self,
        num_process: int = 4,
        tasksets: Optional[list[Taskset]] = None,
        cutoff: Optional[SimTime] = None,
        return_ratio: bool = False,
    ):
        if tasksets is None:
            tasksets = self.tasksets
        num_taskset = len(tasksets)

        self.schedulable_num = 0
        self.sufficient_num = 0

        with Pool(processes=num_process, initializer=self.init_process) as pool:
            results = pool.imap_unordered(
                functools.partial(
                    self.schedulability_test,
                    platform_info=self.platform_info,
                    db_path=self.data_path / "data.sqlite",
                    cutoff=cutoff,
                ),
                tasksets,
                # chunksize=ceil(num_taskset / (num_process)),
            )
            for result in tqdm(results, total=num_taskset):
                if result is not None:
                    taskset, is_schedulable, sufficient = result
                    taskset_u = sum(task.utilization for task in taskset)
                    sys_u = taskset_u / self.platform_info.S_m
                    self.task_db.insert_taskset(
                        taskset, is_schedulable, sufficient, sys_u
                    )
                    if is_schedulable:
                        self.schedulable_num += 1
                    if sufficient:
                        self.sufficient_num += 1

        self.task_db.commit()

        if return_ratio:
            return self.schedulable_num / num_taskset, self.sufficient_num / num_taskset

    def generate_hyperedge_list(
        self,
        num_taskset: int,
        taskset_size: int,
        num_process: int = 4,
        system_utilization: Optional[float] = None,
        cutoff: Optional[SimTime] = None,
    ):
        self.tasksets = self.generate_tasksets(
            num_taskset, taskset_size, system_utilization
        )

        self.parallel_simulate(num_process, self.tasksets, cutoff)
