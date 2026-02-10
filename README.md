<!-- markdownlint-disable MD033 MD041 -->
<p align="center">
  <a href="https://cli.nonebot.dev/"><img src="https://cli.nonebot.dev/logo.png" width="200" height="200" alt="nonebot"></a>
</p>

<div align="center">

# NB CLI Plugin Docker

_✨ NoneBot2 命令行工具 Docker 插件 ✨_

</div>

<p align="center">
  <a href="https://raw.githubusercontent.com/nonebot/nb-cli-plugin-docker/master/LICENSE">
    <img src="https://img.shields.io/github/license/nonebot/cli-plugin-docker" alt="license">
  </a>
  <a href="https://pypi.python.org/pypi/nb-cli-plugin-docker">
    <img src="https://img.shields.io/pypi/v/nb-cli-plugin-docker" alt="pypi">
  </a>
  <img src="https://img.shields.io/badge/python-3.10+-blue" alt="python">
  <a href="https://results.pre-commit.ci/latest/github/nonebot/nb-cli-plugin-docker/master">
    <img src="https://results.pre-commit.ci/badge/github/nonebot/cli-plugin-docker/master.svg" alt="pre-commit" />
  </a>
  <br />
  <a href="https://jq.qq.com/?_wv=1027&k=5OFifDh">
    <img src="https://img.shields.io/badge/QQ%E7%BE%A4-768887710-orange?style=flat-square" alt="QQ Chat Group">
  </a>
  <a href="https://qun.qq.com/qqweb/qunpro/share?_wv=3&_wwv=128&appChannel=share&inviteCode=7b4a3&appChannel=share&businessType=9&from=246610&biz=ka">
    <img src="https://img.shields.io/badge/QQ%E9%A2%91%E9%81%93-NoneBot-5492ff?style=flat-square" alt="QQ Channel">
  </a>
  <a href="https://t.me/botuniverse">
    <img src="https://img.shields.io/badge/telegram-botuniverse-blue?style=flat-square" alt="Telegram Channel">
  </a>
  <a href="https://discord.gg/VKtE6Gdc4h">
    <img src="https://discordapp.com/api/guilds/847819937858584596/widget.png?style=shield" alt="Discord Server">
  </a>
</p>

## 准备

在使用本插件前请确保 Docker CLI 以及 Docker Compose Plugin 已经安装，且可以从命令行直接使用。

详细安装方法请参考 [Docker 文档](https://docs.docker.com/engine/install/)

Docker 官方 Linux 快速安装一键脚本：

```bash
curl -fsSL https://get.docker.com | sudo sh
```

## 安装插件

### uv tool / uvx（推荐）

首先需要[安装 uv](https://docs.astral.sh/uv/#installation)。

直接使用：

```bash
uvx --from nb-cli --with nb-cli-plugin-docker nb docker
# 或
uv tool run --from nb-cli --with nb-cli-plugin-docker nb docker
```

安装：

```bash
uv tool install --with nb-cli-plugin-docker nb-cli

# 更新环境变量（如果需要）
uv tool update-shell
```

### 通用方式

```bash
nb self install nb-cli-plugin-docker
```

## 使用插件

```bash
nb docker
# 其他别名
# nb deploy
# nb compose
```

### generate

生成 `Dockerfile` 和 `docker-compose.yml`。

#### 什么时候需要（重新）生成？

- 在项目中首次使用本插件时；
- 更换了机器人项目的管理器时。

#### 传递项目依赖

对于使用了 `uv`, `pdm` 或 `poetry` 的机器人项目，本插件会自动检查相应的依赖固定信息（即 `*.lock` 文件）判断并调用相应工具自动向容器内传递依赖。

对于其他管理方式的机器人项目，则需要手动导出一份 `requirements.txt` 来传递项目依赖到容器内，例如：

```bash
source .venv/bin/activate
pip freeze > requirements.txt
```

### build

构建机器人镜像。

### up / down

部署/取消部署机器人实例。

### logs

查看机器人日志。

### ps

查看机器人运行状态。
