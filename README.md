# casperfpga (Python 3 维护版)

> **Language / 语言**
> - [English](#english)
> - [中文](#中文)

---

<!-- ==================== English ==================== -->

<a id="english"></a>

# English

`casperfpga` is a Python library used to interact with and interface with [**CASPER** Hardware](https://github.com/casper-astro/casper-hardware). This repository is a **Python 3 maintenance fork** of the original [casper-astro/casperfpga](https://github.com/casper-astro/casperfpga), focused on keeping the library compatible with modern Python 3 environments.

> The original README is preserved in [README_BACKUP.md](README_BACKUP.md).

## Table of Contents

1. [Version Design Notes](#version-design-notes)
2. [Installation](#installation)
3. [Compatibility Testing](#compatibility-testing)

---

<a id="version-design-notes"></a>

### Version Design Notes

This repository is dedicated to maintaining a **Python 3 version** of `casperfpga`.

- **Vendored tftpy (based on v0.8.7).** The library includes a vendored copy of [tftpy](https://github.com/pHantomU94/tftpy/releases/tag/v0.8.7.post1) located under [`casperfpga/_vendor/tftpy/`](casperfpga/_vendor/tftpy/) (source tree: [`src/_vendor/tftpy/`](src/_vendor/tftpy/)). This vendored version fixes several design issues present in the official tftpy library, including logger hierarchy leakage and packaging namespace problems. See the `VENDORED_FROM.txt` in that directory for details:

  ```text
  Vendored from:
  https://github.com/pHantomU94/tftpy/releases/tag/v0.8.7.post1

  Original package:
  tftpy 0.8.7.post1

  Local adaptation:
  - relocated under `casperfpga._vendor.tftpy`
  - no functional source changes beyond packaging namespace use
  ```

- **progska.** The SKARAB programming utility `progska` is built as an optional extension package and shipped as a compiled extension (e.g., [`progska.cpython-310-darwin.so`](casperfpga/progska.cpython-310-darwin.so)).

---

<a id="installation"></a>

### Installation

The simplest way to install is to **download the pre-built `.whl` file** from the [GitHub Releases](https://github.com/pHantomU94/casperfpga/releases) page, then install it into your Python environment or virtual environment using `pip`.

**Step 1 — Download the wheel file**

Go to the [Releases](https://github.com/pHantomU94/casperfpga/releases) page of this repository, locate the release version you want (e.g., `v0.4.9`), and download the corresponding `.whl` file from the release assets (e.g., `casperfpga-0.4.9-py3-none-any.whl`).

**Step 2 — (Optional) Create and activate a virtual environment**

```bash
# Create a virtual environment (replace with your Python version if needed)
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows
```

**Step 3 — Install the wheel file with pip**

```bash
# Replace the file name with the actual wheel file you downloaded
pip install dist/casperfpga-<version>-py3-none-any.whl

# Example:
# pip install dist/casperfpga-0.4.9-py3-none-any.whl
```

**Step 4 — Verify the installation**

```python
$ ipython
In [1]: import casperfpga
In [2]: casperfpga.__version__
```

---

<a id="compatibility-testing"></a>

### Compatibility Testing

This fork has been tested and confirmed to work with:

| Python Version | Status |
| :------------: | :----: |
| 3.8            | ✅     |
| 3.10           | ✅     |

If you encounter issues with other Python versions, please [open an issue](https://github.com/pHantomU94/casperfpga/issues).

---

<!-- ==================== 中文 ==================== -->

<a id="中文"></a>

# 中文

`casperfpga` 是一个用于与 [**CASPER** 硬件](https://github.com/casper-astro/casper-hardware)交互的 Python 库。本仓库是原始 [casper-astro/casperfpga](https://github.com/casper-astro/casperfpga) 的 **Python 3 维护分支**，专注于保持该库在现代 Python 3 环境中的兼容性。

> 原 README 内容已备份到 [README_BACKUP.md](README_BACKUP.md)。

## 目录

1. [版本设计说明](#版本设计说明)
2. [安装方式](#安装方式)
3. [兼容性测试](#兼容性测试)

---

<a id="版本设计说明"></a>

### 版本设计说明

本仓库专门用于维护 **Python 3 版本** 的 `casperfpga`。

- **内置 tftpy（基于 v0.8.7）。** 本库包含一份 [tftpy](https://github.com/pHantomU94/tftpy/releases/tag/v0.8.7.post1) 的 vendored 副本，位于 [`casperfpga/_vendor/tftpy/`](casperfpga/_vendor/tftpy/)（源码树：[`src/_vendor/tftpy/`](src/_vendor/tftpy/)）。该 vendored 版本修复了官方 tftpy 库中的若干设计问题，包括 logger 层级泄露和包命名空间问题。详情见该目录下的 `VENDORED_FROM.txt`：

  ```text
  Vendored from:
  https://github.com/pHantomU94/tftpy/releases/tag/v0.8.7.post1

  Original package:
  tftpy 0.8.7.post1

  Local adaptation:
  - relocated under `casperfpga._vendor.tftpy`
  - no functional source changes beyond packaging namespace use
  ```

- **progska。** SKARAB 编程工具 `progska` 作为可选扩展包构建，以编译扩展形式提供（如 [`progska.cpython-310-darwin.so`](casperfpga/progska.cpython-310-darwin.so)）。

---

<a id="安装方式"></a>

### 安装方式

最简单的安装方式是 **从 [GitHub Releases](https://github.com/pHantomU94/casperfpga/releases) 页面下载预构建的 `.whl` 文件**，然后在对应的 Python 环境或虚拟环境中使用 `pip` 安装。

**第一步 — 下载 wheel 文件**

进入本仓库的 [Releases](https://github.com/pHantomU94/casperfpga/releases) 页面，找到你需要的发布版本（如 `v0.4.9`），下载该版本下对应的 `.whl` 文件（如 `casperfpga-0.4.9-py3-none-any.whl`）。

**第二步 —（可选）创建并激活虚拟环境**

```bash
# 创建虚拟环境（如需指定 Python 版本请自行替换）
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows
```

**第三步 — 使用 pip 安装 wheel 文件**

```bash
# 将文件名替换为你实际下载的 wheel 文件名
pip install dist/casperfpga-<version>-py3-none-any.whl

# 示例：
# pip install dist/casperfpga-0.4.9-py3-none-any.whl
```

**第四步 — 验证安装**

```python
$ ipython
In [1]: import casperfpga
In [2]: casperfpga.__version__
```

---

<a id="兼容性测试"></a>

### 兼容性测试

本分支已测试并确认支持以下 Python 版本：

| Python 版本 | 状态 |
| :---------: | :--: |
| 3.8         | ✅   |
| 3.10        | ✅   |

如果在其他 Python 版本上遇到问题，请[提交 Issue](https://github.com/pHantomU94/casperfpga/issues)。
