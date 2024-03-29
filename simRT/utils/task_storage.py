from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from simRT.core.task import TYPE_MAPPING, TaskInfo

if TYPE_CHECKING:
    from simRT.generator.task_generator import Taskset


class TaskStorage:

    def __init__(self, db_name: Path):
        self.conn = sqlite3.connect(db_name, timeout=60.0)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def __del__(self):
        # self.commit()
        self.close()

    def create_tables(self):
        # 创建任务表
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Task (
                TaskID INTEGER PRIMARY KEY,
                TaskType TEXT,
                WCET REAL,
                Deadline INTEGER,
                Period INTEGER,
                Utilization REAL
            )
            """
        )

        # 创建任务集表
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS TaskSet (
                TaskSetID INTEGER PRIMARY KEY AUTOINCREMENT,
                IsSchedulable BOOLEAN,
                SufficientResult BOOLEAN,
                SystemUtilization REAL,
                TasksetSize INTEGER
            )
            """
        )

        # 创建任务集关联表
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS TaskSetAssociation (
                TaskSetID INT,
                TaskID INT,
                FOREIGN KEY (TaskSetID) REFERENCES TaskSet(TaskSetID),
                FOREIGN KEY (TaskID) REFERENCES Task(TaskID)
            )
            """
        )
        self.commit()

    def insert_task(self, task: TaskInfo):
        """
        插入任务
        """
        self.cursor.execute(
            "INSERT INTO Task (TaskID, TaskType, WCET, Deadline, Period, Utilization) VALUES (?, ?, ?, ?, ?, ?)",
            (
                task.id,
                str(task.type),
                task.wcet,
                task.deadline,
                task.period,
                task.utilization,
            ),
        )
        return self.cursor.lastrowid

    def insert_taskset(
        self,
        taskset: Taskset,
        is_schedulable: bool,
        sufficient: bool,
        system_utilization: float,
    ):
        """
        插入任务集
        在TaskSet中插入可调度性信息
        在TaskSetAssociation中插入关联关系
        """
        self.cursor.execute(
            "INSERT INTO TaskSet (IsSchedulable, SufficientResult, SystemUtilization, TasksetSize) VALUES (?, ?, ?, ?)",
            (is_schedulable, sufficient, system_utilization, len(taskset)),
        )
        if self.cursor.lastrowid is None:
            self.cursor.close()
            self.conn.rollback()
            raise RuntimeError("Failed to insert data: no row was inserted")
        taskset_id: int = self.cursor.lastrowid
        for task in taskset:
            self.insert_task_set_association(task, taskset_id)
        return self.cursor.lastrowid

    def insert_task_set_association(self, task: TaskInfo, taskset_id: int):
        self.cursor.execute(
            """
            INSERT OR IGNORE INTO TaskSetAssociation (TaskSetID, TaskID)
            VALUES (?, ?)
            """,
            (taskset_id, task.id),
        )

    def get_tasksets_dict(
        self, is_schedulable: Optional[bool] = None, sufficient: Optional[bool] = None
    ) -> dict[tuple[TaskInfo, ...], tuple[bool, bool]]:
        tasksets_dict: dict[tuple[TaskInfo, ...], tuple[bool, bool]] = {}

        # 构建查询语句
        sql = (
            "SELECT TaskSetID, IsSchedulable, SufficientResult FROM TaskSet WHERE 1 = 1"
        )
        params = []

        # 构建条件
        if is_schedulable is not None:
            sql += " AND IsSchedulable = ?"
            params.append(is_schedulable)
        if sufficient is not None:
            sql += " AND SufficientResult = ?"
            params.append(sufficient)

        # 执行查询
        self.cursor.execute(sql, tuple(params))
        tasksets_rows = self.cursor.fetchall()

        for taskset_row in tasksets_rows:
            taskset_id, is_schedulable, sufficient = taskset_row
            taskinfos = self.get_taskinfos_for_tasksetid(taskset_id)
            tasksets_dict[tuple(taskinfos)] = (bool(is_schedulable), bool(sufficient))

        return tasksets_dict

    def get_taskinfos_for_tasksetid(self, taskset_id: int) -> list[TaskInfo]:
        task_infos: list[TaskInfo] = []

        self.cursor.execute(
            """
            SELECT Task.TaskID, Task.TaskType, Task.WCET, Task.Deadline, Task.Period
            FROM TaskSetAssociation
            JOIN Task ON TaskSetAssociation.TaskID = Task.TaskID
            WHERE TaskSetID = ?
            """,
            (taskset_id,),
        )
        task_rows = self.cursor.fetchall()

        for task_row in task_rows:
            task_id, task_type_str, wcet, deadline, period = task_row
            task_type = TYPE_MAPPING.get(task_type_str)
            if task_type is None:
                raise ValueError(f"Unknown task type: {task_type_str}")

            task_info = TaskInfo(
                id=task_id, type=task_type, wcet=wcet, deadline=deadline, period=period
            )
            task_infos.append(task_info)

        return task_infos

    def get_all_taskinfos_in_tasksets(self) -> list[TaskInfo]:
        task_infos: list[TaskInfo] = []

        self.cursor.execute(
            """
            SELECT DISTINCT Task.TaskID, Task.TaskType, Task.WCET, Task.Deadline, Task.Period
            FROM Task
            JOIN TaskSetAssociation ON Task.TaskID = TaskSetAssociation.TaskID
            """
        )
        task_rows = self.cursor.fetchall()

        for task_row in task_rows:
            task_id, task_type_str, wcet, deadline, period = task_row
            task_type = TYPE_MAPPING.get(task_type_str)
            if task_type is None:
                raise ValueError(f"Unknown task type: {task_type_str}")

            task_info = TaskInfo(
                id=task_id, type=task_type, wcet=wcet, deadline=deadline, period=period
            )
            task_infos.append(task_info)

        return task_infos

    def clear_table(self, table_name: str):
        self.cursor.execute(f"DELETE FROM {table_name}")
        self.commit()

    def clear(self):
        self.clear_table("Task")
        self.clear_table("TaskSet")
        self.clear_table("TaskSetAssociation")

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
