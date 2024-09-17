# SimRT

这个项目是一个用于模拟实时调度算法的调度过程的 Python 库。

## 目录

- [SimRT](#simrt)
  - [目录](#目录)
  - [简介](#简介)
  - [安装](#安装)
  - [使用方法](#使用方法)
  - [贡献指南](#贡献指南)

## 简介

SimRT 是一个用于模拟实时调度算法的调度过程的 Python 库。
- 支持在异构处理器平台上的 job level 迁移抢占
- 支持随机生成实时任务集，以及从给定大量任务中随机挑选任务组成任务集
- 实现 Global-EDF 充分性可调度性测试
- 支持通过多进程并行判定大量任务集的可调度性

## 安装

### 通过 pip 安装

```shell
pip install git+https://github.com/unccx/SimRT.git
```

### 通过 poetry 安装
```shell
poetry add git+https://github.com/unccx/SimRT.git
```

### 从源代码安装

1. 克隆这个仓库：
    ```shell
    git clone https://github.com/unccx/SimRT.git
    ```
2. 进入项目目录：
    ```shell
    cd SimRT
    ```
3. 安装依赖：
   - 使用 conda/mamba 安装依赖环境
    ```shell
    conda env create -f .\environment.yml
    conda activate simrt
    ```
   - 使用 poetry 安装依赖环境
    ```shell
    poetey install
    poetry shell
    ```

## 使用方法
模拟周期性实时任务的调度过程，判断模拟过程中是否出现错过任务期限
```python
from simrt import TaskInfo, Simulator, PeriodicTask

# 每个任务使用三元组 (C, D, T) 来刻画
# 其中 C 是最坏执行时间、D 是相对截止时间、T 是周期
triplets = [
    (1, 37, 37),
    (1, 43, 43),
    (1, 5, 5),
    (1, 25, 25),
    (1, 47, 47),
    (1, 26, 26),
    (1, 45, 45),
]
taskinfos = [
    TaskInfo(i, PeriodicTask, *triplet) for i, triplet in enumerate(triplets)
]
sim = Simulator(taskinfos)
ret = sim.run()
print(ret)
```

## 贡献指南

欢迎任何形式的贡献，无论是代码、文档、报告问题，还是其他建议。以下是参与贡献的指南：

### 报告问题

- 如果你发现了 bug 或有改进建议，请首先检查 [issue 列表](https://github.com/unccx/SimRT/issues) 以确定是否已有相关的报告。
- 如果没有，请在 [issue 页面](https://github.com/unccx/SimRT/issues/new) 创建一个新的 issue，描述问题的详细信息和复现步骤。

### 提出功能请求
- 如果你有新功能的想法或建议，请在 [issue 页面](https://github.com/unccx/SimRT/issues/new) 提出一个新的 issue，并详细描述你希望添加的功能和它的用途。

### 贡献代码

1. Fork 这个仓库到你的 GitHub 账户。

2. 克隆你自己的仓库到本地：

  ```bash
  git clone https://github.com/你的用户名/SimRT.git
  ```

3. 在你的本地仓库中，创建一个新的分支来进行你的更改：

  ```bash
  git checkout -b feature/你的功能
  ```

4. 在这个分支上进行你的更改。确保你的代码遵循项目的代码风格，并包括足够的测试和文档说明。

5. 提交你的更改：

  ```bash
  git add .
  git commit -m '添加了新功能/修复了 bug'
  ```

6. 将你的更改推送到 GitHub：

  ```bash
  git push origin feature/你的功能
  ```


7. 访问 [Pull Requests 页面](https://github.com/unccx/SimRT/pulls) 并创建一个新的 Pull Request。描述你的更改，并确保在提交时指明你的分支。

### 代码风格和规范

- **代码风格**：遵循 [PEP 8](https://pep8.org) 代码风格指南。使用 [black](https://black.readthedocs.io/en/stable/) 包格式化代码。如果你使用 VSCode 编写代码，你可以使用 [Black Formatter](https://marketplace.visualstudio.com/items?itemName=ms-python.black-formatter)  插件来格式化代码。
- **文档**：尽可能确保你的代码有足够的文档注释和说明。
- **测试**：添加或更新测试以验证你的更改。测试位于 ``tests/`` 文件夹下，您可以在 ``tests/`` 内的子文件夹中为您实现的功能补充新的测试文件。请确保所有测试都通过。
