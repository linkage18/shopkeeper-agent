"""
Python 预处理沙箱 — 安全的 pandas-only 执行环境
禁止：os/subprocess/sys/eval/exec/__import__ 等危险操作
允许：pandas/numpy/math 基本数据处理
"""
import math
from typing import Any

import pandas as pd
import numpy as np

ALLOWED_MODULES = {"pd": pd, "np": np, "math": math}
BLOCKED_KEYWORDS = [
    "os", "subprocess", "sys", "eval(", "exec(", "__import__",
    "compile(", "open(", "file(", "import os", "import sys",
    "from os", "from sys", "socket", "shutil", "ctypes",
]


class SandboxError(Exception):
    pass


def _check_safety(code: str):
    lower = code.lower()
    for kw in BLOCKED_KEYWORDS:
        if kw.lower() in lower:
            raise SandboxError(f"安全性限制：不允许使用 '{kw}'")
    # 不允许 import
    for line in code.split("\n"):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            mod = stripped.split()[1]
            if mod not in ("pandas", "numpy", "math", "pd", "np"):
                raise SandboxError(f"安全性限制：不允许 import '{mod}'")


def run_pandas(code: str, data: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """
    执行 pandas 预处理代码
    code: 用户生成的 Python 代码
    data: {变量名: DataFrame} — 执行前注入的数据
    返回: {变量名: DataFrame/Scalar} — 执行后提取的结果
    """
    _check_safety(code)

    local_vars: dict[str, Any] = {}
    local_vars.update(ALLOWED_MODULES)
    local_vars.update(data)

    try:
        exec(code, {"__builtins__": {}}, local_vars)
    except Exception as e:
        raise SandboxError(f"Python 执行错误: {e}")

    # 提取结果中新增的 DataFrame 和数值
    result = {}
    for k, v in local_vars.items():
        if k in ALLOWED_MODULES or k in data:
            continue
        if isinstance(v, (pd.DataFrame, pd.Series, int, float, str, list)):
            if isinstance(v, pd.DataFrame):
                result[k] = v.to_dict(orient="records")
            elif isinstance(v, pd.Series):
                result[k] = v.to_list()
            else:
                result[k] = v
    return result
