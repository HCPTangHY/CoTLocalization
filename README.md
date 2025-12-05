# 使用说明

## 使用前
1. 你的电脑上需要有 [Python][Python] 3.10 环境

## 初始化本项目项目环境
- 安装 [uv](https://docs.astral.sh/uv/#installation)
  - Windows:
    ```shell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
  - macOS / Linux:
    ```shell
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
- 使用 uv 安装项目依赖
  ```shell
  uv sync
  ```