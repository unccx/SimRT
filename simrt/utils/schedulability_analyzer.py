import math
from abc import ABC, abstractmethod
from math import ceil, floor
from typing import Optional, Sequence

from simpy.core import SimTime
from tqdm import trange

from ..core import Simulator
from ..core.processor import PlatformInfo
from ..core.task import TaskInfo


class SchedulabilityTest(ABC):
    @abstractmethod
    def test(self, Gamma: Sequence[TaskInfo], processors: PlatformInfo) -> bool:
        pass


class SufficientTest(SchedulabilityTest):
    pass


class ExactTest(SchedulabilityTest):
    pass


class GlobalEDFTest(SufficientTest):

    def __init__(
        self, sampling_rate: float = 0.00001, show_progress: bool = False
    ) -> None:
        self.sampling_rate = sampling_rate
        self.show_progress = show_progress

    @staticmethod
    def _DBF(tau: TaskInfo, delta_t: SimTime) -> SimTime:
        if delta_t >= tau.deadline:
            return max(0, (floor((delta_t - tau.deadline) / tau.period) + 1) * tau.wcet)
        else:
            return tau.wcet

    @staticmethod
    def _LOAD(
        Gamma: Sequence[TaskInfo],
        implicit_deadline: bool = False,
        sampling_rate: float = 0.00001,
        show_progress: bool = False,
    ):
        hyper_period = math.lcm(*[math.ceil(tau.period) for tau in Gamma])

        if implicit_deadline:
            delta_t = hyper_period
            return sum(GlobalEDFTest._DBF(tau, delta_t) for tau in Gamma) / delta_t

        load = 0
        step = ceil(hyper_period * sampling_rate)
        range_func = trange if show_progress else range
        for delta_t in range_func(1, hyper_period + 1, step):
            load = max(
                load,
                sum(GlobalEDFTest._DBF(tau, delta_t) for tau in Gamma) / delta_t,
            )
        return load

    def test(self, taskset: Sequence[TaskInfo], processors: PlatformInfo) -> bool:
        assert (
            len(processors.speed_list) > 1
        ), "This sufficient test is for multi-core platforms"
        speed_list = processors.speed_list

        varphi_max = max(tau.density for tau in taskset)
        lambda_pi = max(
            sum(speed_list[i + 1 :]) / speed_list[i]
            for i in range(0, len(speed_list) - 1)
        )
        mu = processors.S_m - lambda_pi * varphi_max
        v = max([i + 1 for i in range(0, len(speed_list)) if sum(speed_list[i:]) < mu])

        implicit_deadline = all(
            taskinfo.deadline == taskinfo.period for taskinfo in taskset
        )

        load = self._LOAD(
            taskset, implicit_deadline, self.sampling_rate, self.show_progress
        )

        return mu - v * varphi_max >= load


class SimulationTest(ExactTest):

    def __init__(
        self, cutoff: Optional[SimTime] = None, show_progress: bool = False
    ) -> None:
        self.cutoff = cutoff
        self.show_progress = show_progress

    def test(self, taskset: Sequence[TaskInfo], processors: PlatformInfo) -> bool:
        sim = Simulator(taskset, processors)
        return sim.run(until=self.cutoff, show_progress=self.show_progress)


class TestFactory:
    @staticmethod
    def create_test(test_type: str, **kwargs) -> SchedulabilityTest:
        if test_type == "GlobalEDFTest":
            return GlobalEDFTest(**kwargs)
        if test_type == "SimulationTest":
            return SimulationTest(**kwargs)
        raise ValueError(f"Unsupported test type: {test_type}")


# 上下文类
class SchedulabilityAnalyzer:
    def __init__(self):
        self.sufficient_test = None
        self.exact_test = None

    def set_sufficient_test(self, test: SchedulabilityTest):
        if isinstance(test, SufficientTest):
            self.sufficient_test = test
        else:
            raise TypeError("Expected SufficientTest instance")

    def set_exact_test(self, test: SchedulabilityTest):
        if isinstance(test, ExactTest):
            self.exact_test = test
        else:
            raise TypeError("Expected ExactTest instance")

    def analyze(
        self, taskset: Sequence[TaskInfo], platform: PlatformInfo
    ) -> dict[str, Optional[bool]]:
        """
        taskset 为需要进行可调度性测试的任务集
        platform_info 为测试的处理器平台
        """

        assert (
            self.sufficient_test is not None or self.exact_test is not None
        ), "At least one schedulability test needs to be specified"

        suff_test_result = None
        exact_test_result = None

        if self.sufficient_test is not None:
            suff_test_result = self.sufficient_test.test(taskset, platform)

        # 如果充分测试结果为可调度，则必定满足充要条件
        if suff_test_result is True:
            exact_test_result = True
            return {
                "exact_test_result": exact_test_result,
                "suff_test_result": suff_test_result,
            }

        if self.exact_test is not None:
            exact_test_result = self.exact_test.test(taskset, platform)

        return {
            "exact_test_result": exact_test_result,
            "suff_test_result": suff_test_result,
        }
