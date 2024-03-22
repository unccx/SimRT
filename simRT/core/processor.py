from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional, Sequence, Type

from simpy import Environment, Interrupt, Resource
from simpy.core import BoundClass, SimTime
from simpy.resources.resource import Preempted, Release, Request

SpeedType = SimTime
Priority = SimTime


class SortedQueue(list):
    """Queue for sorting events by their :attr:`~ProcessorRequest.key`
    attribute.

    """

    def __init__(self, maxlen: Optional[int] = None):
        super().__init__()
        self.maxlen = maxlen
        """Maximum length of the queue."""

    def append(self, item: Any) -> None:
        """Sort *item* into the queue.

        Raise a :exc:`RuntimeError` if the queue is full.

        """
        if self.maxlen is not None and len(self) >= self.maxlen:
            raise RuntimeError("Cannot append event. Queue is full.")

        super().append(item)
        super().sort()

class ProcessorRequest(Request):

    resource: ProcessorPlatform

    def __init__(
        self, resource: Resource, priority: Priority = 0, preempt: bool = True
    ):
        self.priority = priority
        """The priority of this request. A smaller number means higher
        priority."""

        self.preempt = preempt
        """Indicates whether the request should preempt a resource user or not
        (:class:`PriorityResource` ignores this flag)."""

        self.time = resource._env.now
        """The time at which the request was made."""

        self.key = (self.priority, self.time, not self.preempt)
        """Key for sorting events. Consists of the priority (lower value is
        more important), the time at which the request was made (earlier
        requests are more important) and finally the preemption flag (preempt
        requests are more important).
        """

        super().__init__(resource)

    def __lt__(self, other: ProcessorRequest):
        return self.key < other.key

    def __le__(self, other: ProcessorRequest):
        return self.key <= other.key

    def __enter__(self) -> ProcessorRequest:
        return self

    @property
    def is_preempted(self) -> bool:
        """Returns True if the request was triggered but was deleted from self.users"""
        return (
            self.triggered is True
            and self not in self.resource.users
            and self not in self.resource.put_queue
        )

    @property
    def is_on_platform(self) -> bool:
        """Returns True if the request is in users and has been triggered"""
        return (
            self.triggered is True
            and self in self.resource.users
            and self not in self.resource.put_queue
        )

    @property
    def is_ready(self) -> bool:
        """Returns True if the request is still in the put_queue and has not triggered"""
        return (
            self.triggered is False
            and self not in self.resource.users
            and self in self.resource.put_queue
        )

    @property
    def speed(self) -> Optional[SpeedType]:
        """Returns the execution speed of the requested processor.
        Returns None if the processor request is preempted.
        Returns 0 if the processor request is waiting in the queue.
        ProcessorRequest is saved in self.resource.users or self.resource.put_queue
        In self.resource.users means that the processor resource has been occupied
        In self.resource.put_queue, it means that the processor resource is not occupied and is still queued.
        """
        if self.is_on_platform:
            priority = self.resource.users.index(self)
            return self.resource.speed_list[priority]
        elif self.is_preempted:
            return None
        elif self.is_ready:
            return 0
        else:
            assert (
                False
            ), "There are only three states for ProcessorRequest: on_platform, preempted and ready"


class ProcessorRelease(Release):
    def __init__(self, resource: Resource, request: ProcessorRequest):
        self.request: ProcessorRequest = request
        super().__init__(resource, request)


@dataclass(frozen=True, order=True)
class PlatformInfo:
    speed_list: list[SpeedType] = field(default_factory=list)

    def __post_init__(self):
        if len(self.speed_list) == 0:
            self.speed_list.append(1)
        self.speed_list.sort(reverse=True)  # 速度降序排列

        if self.speed_list[-1] <= 0:
            raise ValueError("Processor speed must be > 0.")

    @property
    def descending(self):
        return reversed(self.speed_list)

    @property
    def S_m(self):
        return sum(self.speed_list)

    @property
    def fastest_speed(self):
        return self.speed_list[0]

    @property
    def is_homogeneous(self):
        return self.speed_list[0] == self.speed_list[-1]


class ProcessorPlatform(Resource):

    PutQueue = SortedQueue
    """Queue of pending *put* requests."""
    GetQueue = list
    """Queue of pending *get* requests."""

    def __init__(
        self,
        env: Environment,
        processorinfos: Optional[PlatformInfo | Sequence[SpeedType]] = None,
    ):
        if processorinfos is None:
            self.platform_info = PlatformInfo()
        elif isinstance(processorinfos, Sequence):
            self.platform_info = PlatformInfo(list(processorinfos))
        elif isinstance(processorinfos, PlatformInfo):
            self.platform_info = processorinfos
        elif processorinfos is None:
            self.platform_info = PlatformInfo()
        else:
            assert False, f"processorsinfo type is not {type(processorinfos)}"

        super().__init__(env, capacity=len(self.speed_list))
        self.users: SortedQueue = SortedQueue(maxlen=len(self.speed_list))
        """List of :class:`ProcessorRequest` events for the processes that are currently
        using the resource."""

    @property
    def speed_list(self):
        return self.platform_info.speed_list

    if TYPE_CHECKING:

        def request(
            self, priority: Priority = 0, preempt: bool = True
        ) -> ProcessorRequest:
            """Request a usage slot with the given *priority*."""
            return ProcessorRequest(self, priority, preempt)

        def release(  # type: ignore[override]
            self, request: ProcessorRequest
        ) -> Release:
            """Release a usage slot."""
            return ProcessorRelease(self, request)

    else:
        request = BoundClass(ProcessorRequest)
        release = BoundClass(ProcessorRelease)

    def _do_put(  # type: ignore[override]
        self, event: ProcessorRequest
    ) -> Optional[bool]:
        """如果请求满足资源获取条件，则将请求放入资源 users
        如果满足放置 event 的条件，该方法必须触发事件。例如，使用适当的值调用 :meth:`Event.succeed()`
        一旦返回False, 则提前停止遍历put_queue
        """
        # 在 self.user 中寻找比 event 优先级低的 request，中断 request
        # 因为 self.user 按照优先级从高到低排列，所以结果为 self.users[index:]
        # 如果 self.users 中存在与 event 相等的元素，则返回相等元素的最右边位置
        index = bisect_right(self.users, event)

        if index >= self.capacity:
            # 因为 _trigger_put() 对 put_queue 的遍历是从左往右（优先级从高到低）
            # 如果 index >= self.capacity，则说明 ProcessorPlatform 已经满了
            # put_queue 最左侧的 request 的优先级小于 users 中最右侧的 request 的优先级
            """
            capacity = 6
                               prio > prio
                ┌──┬──┬──┬──┬──┬──┐   ┌──┬──┬──┬──┬──┬──┐
                │l │  │  │  │  │ r│   │l │  │  │  │  │ r│
                └──┴──┴──┴──┴──┴──┘   └──┴──┴──┴──┴──┴──┘
                    user                   put_queue
            """
            return False  # put_queue 之后的元素不需要被 _trigger_put() 遍历了

        """
        被中断的 request 有两种结果：
            1. request 仍然占有处理器，但是处理器速度变化需要在 Process 中重新计算 speed

            2. request 被踢出 ProcessorPlatform.users 需要重新 ProcessorPlatform.request()
            这种 request 需要经历 ProcessorPlatform.release(request) 或 离开 with scope 才能重新 request()
        """

        # 将优先级比 event 低的 request 中断
        interrupted: ProcessorRequest  # type hint
        for interrupted in self.users[index:]:
            if interrupted.proc is not None:
                # 被中断的 request.proc 会产生 Interruption，如果被 Process 中的逻辑捕获会立即回调 Process._resume()
                interrupted.proc.interrupt(
                    Preempted(
                        by=event.proc,
                        usage_since=interrupted.usage_since,
                        resource=self,
                    )
                )

        if len(self.users) == self.capacity and index < self.capacity and event.preempt:
            # If self.users is full, and we can preempt another process
            self.users.pop(-1)

        return super()._do_put(event)

    def _do_get(self, event: ProcessorRelease) -> None:
        if event.request.is_on_platform:
            idx = self.users.index(event.request)
            interrupted: ProcessorRequest  # type hint
            for interrupted in self.users[idx + 1 :]:
                if interrupted.proc is not None:
                    interrupted.proc.interrupt(
                        Preempted(
                            by=event.request.proc,
                            usage_since=interrupted.usage_since,
                            resource=self,
                        )
                    )

        return super()._do_get(event)
