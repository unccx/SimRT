import unittest
from pathlib import Path

import numpy as np
from scipy.stats import chi2

from simRT import PlatformInfo, TaskInfo
from simRT.generator import HGConfig, TaskHypergraphGenerator, Taskset


class TestHGConfig(unittest.TestCase):
    def setUp(self) -> None:
        self.config = HGConfig(
            platform_info=PlatformInfo([3, 2, 1]),
            num_node=5000,
            period_bound=(1, 50),
        )

    def test_save_as_json(self):
        self.config.save_as_json(Path("./data/test.json"))

    def test_from_json(self):
        self.config.save_as_json(Path("./data/test.json"))
        config = HGConfig.from_json(Path("./data/test.json"))
        self.assertEqual(config, self.config)

    def tearDown(self) -> None:
        Path("./data/test.json").unlink()


class TestTaskHypergraphGenerator(unittest.TestCase):
    def setUp(self) -> None:
        self.config = HGConfig(
            platform_info=PlatformInfo([3, 2, 1]),
            num_node=10000,
            period_bound=(5, 20),
        )
        self.task_hg_gen = TaskHypergraphGenerator(self.config, Path("./data/"))
        self.task_hg_gen.task_db.clear()

    def tearDown(self) -> None:
        self.task_hg_gen.task_db.close()
        Path("./data/data.sqlite").unlink()
        Path("./data/config.json").unlink()

    def test_generate_tasks(self):
        self.assertEqual(len(self.task_hg_gen.tasks), self.config.num_node)

    def test_select_taskset(self):
        target_utilizations = [0.2, 0.34, 0.4, 0.2, 1.5, 2.4]
        target_taskinfos = self.task_hg_gen._select_taskset(target_utilizations)

        for target_u, target_taskinfo in zip(target_utilizations, target_taskinfos):
            self.assertAlmostEqual(target_u, target_taskinfo.utilization, places=3)

    def test_generate_tasksets(self):
        def is_uniform_distribution(data, bins=10, alpha=0.05):
            """Check if the data follows a uniform distribution."""
            counts, _ = np.histogram(data, bins=bins)
            expected_count = len(data) / bins
            chi_squared_statistic = np.sum(
                (counts - expected_count) ** 2 / expected_count
            )
            critical_value = chi2.ppf(1 - alpha, bins - 1)
            # print(f"counts: {counts}")
            return chi_squared_statistic < critical_value

        tasksets = self.task_hg_gen.generate_tasksets(num_taskset=1000, taskset_size=10)

        S_m = self.task_hg_gen.platform_info.S_m
        utilization_distribution = [
            sum(task.utilization for task in taskset) / S_m for taskset in tasksets
        ]
        self.assertTrue(is_uniform_distribution(utilization_distribution, bins=100))

    def test_generate_hyperedge_list(self):
        schedulable_ratio, sufficient_ratio = self.task_hg_gen.generate_hyperedge_list(
            num_taskset=1000, taskset_size=7, num_process=16, system_utilization=None
        )
        print(
            f"schedulable_ratio: {schedulable_ratio}, sufficient_ratio: {sufficient_ratio}"
        )
