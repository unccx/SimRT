from typing import Optional, Sequence

from ..core.processor import PlatformInfo
from ..core.task import TaskInfo
from .schedulability_test import ExactTest, SchedulabilityTest, SufficientTest


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
