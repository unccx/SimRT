import bisect
import functools
import json
import time
from dataclasses import asdict, dataclass
from multiprocessing import Pool
from pathlib import Path
from random import random, uniform
from typing import Optional

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
        self.data_id = int(time.time())

        self.data_path: Path = (
            Path(f"./data/{self.data_id}") if data_path is None else data_path
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
        task_utilizations = []
        for _ in range(self.num_node):
            task_utilizations.append(uniform(0, self.platform_info.fastest_speed))

        return self.task_gen.generate_task(task_utilizations)

    def _select_taskset(self, target_utilizations: list[float]) -> Taskset:
        """
        从candidate_taskinfos中选择与target_utilizations中利用率相近的任务作为任务集
        任务节点数量太少会导致被选择任务的利用率与期望的利用率相差过大
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
        如果 system_utilization is None，则随机生成系统利用率
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
    def schedulability_test(
        taskset: Taskset,
        platform_info: PlatformInfo,
        db_path: Optional[Path] = None,
        cutoff: Optional[SimTime] = None,
    ) -> tuple[Taskset, bool, bool]:
        sim = Simulator(taskset, platform_info)
        # 可调度性充要条件
        ns_result = sim.run(until=cutoff)
        # 可调度性充分非必要条件
        sufficient = Schedulability.G_EDF_sufficient_test(taskset, platform_info)
        if db_path is not None:
            task_db = TaskStorage(db_path)
            taskset_u = sum(task.utilization for task in taskset)
            sys_u = taskset_u / platform_info.S_m
            task_db.insert_taskset(taskset, ns_result, sufficient, sys_u)
            task_db.commit()
        return taskset, ns_result, sufficient

    def generate_hyperedge_list(
        self,
        num_taskset: int,
        taskset_size: int,
        num_process: int = 4,
        system_utilization: Optional[float] = None,
        cutoff: Optional[SimTime] = None,
    ) -> tuple[float, float]:
        self.tasksets = self.generate_tasksets(
            num_taskset, taskset_size, system_utilization
        )

        self.schedulable_num = 0
        self.sufficient_num = 0
        with Pool(processes=num_process) as pool:
            results = pool.imap_unordered(
                functools.partial(
                    self.schedulability_test,
                    platform_info=self.platform_info,
                    db_path=self.data_path / "data.sqlite",
                    cutoff=cutoff,
                ),
                self.tasksets,
            )
            for taskset, is_schedulable, sufficient in tqdm(
                results, total=len(self.tasksets)
            ):
                # self.task_db.insert_taskset(taskset, is_schedulable, sufficient)
                if is_schedulable:
                    self.schedulable_num += 1
                if sufficient:
                    self.sufficient_num += 1

        self.task_db.commit()
        self.task_db.close()

        return self.schedulable_num / num_taskset, self.sufficient_num / num_taskset
