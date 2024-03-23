import unittest

import simpy
from simpy.core import SimTime
from simpy.resources.resource import Preempted, Release, Request

from simRT.core import PlatformInfo, ProcessorPlatform, ProcessorRequest, SortedQueue


class TestPlatformInfo(unittest.TestCase):
    def setUp(self) -> None:
        self.platforminfos: list[PlatformInfo] = []
        self.platforminfos.append(PlatformInfo())
        self.platforminfos.append(PlatformInfo([1, 3, 2]))
        self.platforminfos.append(PlatformInfo([]))
        self.platforminfos.append(PlatformInfo())
        self.platforminfos.append(PlatformInfo([1, 1, 1]))

    def test_init(self):
        self.assertIsNot(self.platforminfos[0], self.platforminfos[-1])
        self.assertIsNot(
            self.platforminfos[0].speed_list, self.platforminfos[-1].speed_list
        )
        self.assertEqual(self.platforminfos[1].speed_list, [3, 2, 1])
        self.assertEqual(self.platforminfos[0].speed_list, [1])
        self.assertEqual(self.platforminfos[2].speed_list, [1])

        with self.assertRaises(ValueError):
            PlatformInfo([-1, 0, 1])

    def test_S_m(self):
        self.assertEqual(self.platforminfos[0].S_m, 1)
        self.assertEqual(self.platforminfos[1].S_m, 6)

    def test_descending(self):
        self.assertEqual(list(self.platforminfos[1].ascending), [1, 2, 3])

    def test_fastest_speed(self):
        self.assertEqual(self.platforminfos[1].fastest_speed, 3)

    def test_is_homogeneous(self):
        self.assertFalse(self.platforminfos[1].is_homogeneous)
        self.assertTrue(self.platforminfos[4].is_homogeneous)


class TestSortedQueue(unittest.TestCase):
    def setUp(self) -> None:
        self.MAX_LEN = 5
        self.maxlen_sq = SortedQueue(self.MAX_LEN)
        self.sq = SortedQueue()

        self.data = [8, 2, 9, 3, 1]
        for i in self.data:
            self.sq.append(i)
            self.maxlen_sq.append(i)

        self.sorted_data = sorted(self.data)

    def test_init(self):
        self.assertIsNone(self.sq.maxlen)
        self.assertIsNotNone(self.maxlen_sq.maxlen)

    def test_append(self):
        self.assertEqual(self.sorted_data, self.sq)

        with self.assertRaises(RuntimeError):
            self.maxlen_sq.append(1)

    def test_iter(self):
        for i, j in zip(self.sq, self.sorted_data):
            self.assertEqual(i, j)

    def test_getitem(self):
        length = len(self.sorted_data)
        for i in range(length):
            self.assertEqual(self.sq[i], self.sorted_data[i])
            self.assertEqual(self.sq[i:], self.sorted_data[i:])
            self.assertEqual(self.sq[:i], self.sorted_data[:i])

    def test_pop(self):
        self.assertEqual(self.sq.pop(0), self.sorted_data[0])

    def test_index(self):
        for i, j in zip(self.sq, self.sorted_data):
            self.assertEqual(self.sq.index(i), self.sorted_data.index(j))


class TestProcessorRequest(unittest.TestCase):
    def setUp(self) -> None:
        self.env = simpy.Environment()
        self.speed_list = [2, 1, 3]
        self.platform: ProcessorPlatform = ProcessorPlatform(self.env, self.speed_list)
        self.uniprocessor: ProcessorPlatform = ProcessorPlatform(self.env)

        self.requests = SortedQueue()
        prio = [3, 3, 4, 2, 1, 4]
        for p in prio:
            self.requests.append(ProcessorRequest(self.platform, priority=p))

    def tearDown(self) -> None:
        for req in self.requests:
            self.platform.release(req)

    def test_init(self):
        self.speed_list.sort(reverse=True)
        self.assertTrue(self.requests[0].is_on_platform)
        self.assertTrue(self.requests[1].is_on_platform)
        self.assertTrue(self.requests[2].is_on_platform)
        self.assertTrue(self.requests[3].is_preempted)
        self.assertTrue(self.requests[4].is_preempted)
        self.assertTrue(self.requests[5].is_ready)

    def test_lt(self):
        self.assertLess(self.requests[0], self.requests[-1])

    def test_le(self):
        self.assertLessEqual(self.requests[0], self.requests[-1])
        self.assertLessEqual(self.requests[0], self.requests[1])

    def test_eq(self):
        self.assertIs(self.requests[0], self.requests[0])
        self.assertEqual(self.requests[-1].key, self.requests[-2].key)
        self.assertNotEqual(self.requests[-1], self.requests[-2])

    def test_ge(self):
        self.assertGreaterEqual(self.requests[-1], self.requests[0])
        self.assertGreaterEqual(self.requests[0], self.requests[0])

    def test_gt(self):
        self.assertGreater(self.requests[-1], self.requests[0])

    def test_access_speed(self):
        self.speed_list.sort(reverse=True)
        self.assertEqual(self.requests[0].speed, self.speed_list[0])
        self.assertEqual(self.requests[1].speed, self.speed_list[1])
        self.assertEqual(self.requests[2].speed, self.speed_list[2])
        self.assertEqual(self.requests[3].speed, None)
        self.assertEqual(self.requests[4].speed, None)
        self.assertEqual(self.requests[5].speed, 0)


class TestProcessorPlatform(unittest.TestCase):
    def setUp(self) -> None:
        self.env = simpy.Environment()
        self.speed_list = [2, 1, 3]
        self.platform: ProcessorPlatform = ProcessorPlatform(self.env, self.speed_list)
        self.uniprocessor: ProcessorPlatform = ProcessorPlatform(self.env)
        self.log = []
        self.proc_list: list = []
        print("\n")

    # def tearDown(self) -> None:
    #     for now, record in self.log:
    #         print(f"[{now}]\t" + record)

    def test_set_speed(self):
        for idx, speed in enumerate(sorted(self.speed_list, reverse=True)):
            self.assertEqual(self.platform.speed_list[idx], speed)

    def test_out_of_order_speed_list(self):
        self.assertEqual(
            self.platform.speed_list, sorted(self.speed_list, reverse=True)
        )

    def test_ProcessorPlatform(self):

        def proc(
            env: simpy.Environment,
            platform: ProcessorPlatform,
            prio,
            name: str,
            duration: SimTime,
        ):
            accumulated_execution = 0
            while accumulated_execution < duration:
                with platform.request(priority=prio) as req:
                    try:
                        yield req
                    except simpy.Interrupt as ir:
                        if not req.is_on_platform:
                            continue

                    self.assertEqual(env.now, req.usage_since)
                    self.log.append(
                        (
                            env.now,
                            f"{name} 申请成功 speed={req.speed} at {req.usage_since}",
                        )
                    )

                    while req.is_on_platform:
                        try:
                            execution_speed: SimTime = req.speed  # type: ignore
                            start: SimTime = env.now
                            yield env.timeout(
                                (duration - accumulated_execution) / execution_speed
                            )
                            accumulated_execution = duration
                            break
                        except simpy.Interrupt as ir:
                            accumulated_execution += (env.now - start) * execution_speed

                            self.assertIsNotNone(ir)
                            self.assertIsInstance(ir.cause, Preempted)
                            cause: Preempted = ir.cause  # type: ignore
                            self.log.append(
                                (
                                    env.now,
                                    f"{name} 被 P{self.proc_list.index(cause.by)} 中断，中断前速度{execution_speed}，中断后速度{req.speed}，已执行{accumulated_execution}/{duration}",
                                )
                            )
            self.log.append(
                (env.now, f"{name} 已完成，已执行{accumulated_execution}/{duration}")
            )

        self.assertEqual(self.platform.capacity, len(self.speed_list))
        self.assertEqual(self.platform.count, 0)

        prio = [1, 2, 1, 0]
        duration_list = [10, 20, 10, 30]
        for i, p in enumerate(prio):
            P = self.env.process(
                proc(self.env, self.platform, p, f"P{i}", duration_list[i])
            )
            self.proc_list.append(P)
            # print(f"P{i}: {P}")

        self.env.run()

        self.assertEqual(
            self.log,
            [
                (0, "P0 申请成功 speed=2 at 0"),
                (0, "P2 申请成功 speed=1 at 0"),
                (0, "P3 申请成功 speed=3 at 0"),
                (5.0, "P0 已完成，已执行10/10"),
                (5.0, "P2 被 P0 中断，中断前速度1，中断后速度2，已执行5.0/10"),
                (5.0, "P1 申请成功 speed=1 at 5.0"),
                (7.5, "P2 已完成，已执行10/10"),
                (7.5, "P1 被 P2 中断，中断前速度1，中断后速度2，已执行2.5/20"),
                (10.0, "P3 已完成，已执行30/30"),
                (10.0, "P1 被 P3 中断，中断前速度2，中断后速度3，已执行7.5/20"),
                (14.166666666666668, "P1 已完成，已执行20/20"),
            ],
        )
