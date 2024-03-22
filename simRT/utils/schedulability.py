import math
import re
from math import floor
from typing import Optional, Sequence

from simpy.core import SimTime

from simRT.core.processor import PlatformInfo, SpeedType
from simRT.core.task import TaskInfo


class Schedulability:
    @staticmethod
    def DBF(tau: TaskInfo, delta_t: SimTime) -> SimTime:
        """
        Demand Bound Function
        """
        return max(0, (floor((delta_t - tau.deadline) / tau.period) + 1) * tau.wcet)

    @staticmethod
    def LOAD(Gamma: Sequence[TaskInfo]):
        hyper_period = math.lcm(*[math.ceil(tau.period) for tau in Gamma])
        load = []
        for delta_t in range(1, hyper_period):
            load.append(
                sum(Schedulability.DBF(tau, delta_t) for tau in Gamma) / delta_t
            )
        return max(load)

    @staticmethod
    def G_EDF_sufficient_test(Gamma: Sequence[TaskInfo], processors: PlatformInfo):
        """
        Sufficient test for multi-core Global-EDF.
        """
        assert (
            len(processors.speed_list) > 1
        ), "This sufficient test is for multi-core platforms"
        speed_list = list(processors.descending)

        varphi_max = max(tau.density for tau in Gamma)

        lambda_pi = max(
            [sum(speed_list[i:]) / speed_list[i] for i in range(1, len(speed_list))]
        )

        mu = processors.S_m - lambda_pi * varphi_max
        v = max([l for l in range(len(speed_list)) if sum(speed_list[l:]) < mu])

        return mu - v * varphi_max >= Schedulability.LOAD(Gamma)
