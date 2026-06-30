"""
Python 预处理沙箱 — 安全的 pandas-only 执行环境
使用 AST 静态分析替代子串匹配，防御 __import__('os') 等绕过手段。
禁止：os/subprocess/sys/eval/exec/compile/open/import 等危险操作
允许：pandas/numpy/math 基本数据处理
"""
import ast
import math
from typing import Any, Optional

import pandas as pd
import numpy as np

ALLOWED_MODULES = {"pd": pd, "np": np, "math": math}
ALLOWED_IMPORTS = {"pandas", "numpy", "math", "pd", "np", "plotly"}

# 危险内置函数名 — 执行时从 safe_builtins 中移除
_DANGEROUS_BUILTINS = {"eval", "exec", "compile", "open", "__import__", "input", "breakpoint"}


class SandboxError(Exception):
    pass


class _SafetyAnalyzer(ast.NodeVisitor):
    """AST 安全检查器：在 exec 之前扫描代码中的危险操作"""

    def __init__(self):
        self.errors: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        # 检查危险内置函数调用：eval(...), exec(...), open(...), __import__(...)
        if isinstance(node.func, ast.Name):
            if node.func.id in _DANGEROUS_BUILTINS:
                self.errors.append(f"禁止使用 '{node.func.id}'")
        # 检查危险属性访问：os.system(...), subprocess.run(...)
        if isinstance(node.func, ast.Attribute):
            full_attr = self._get_full_attr(node.func)
            dangerous_attr = [
                "system", "popen", "call", "run", "Popen",
                "check_output", "getoutput",
            ]
            if full_attr and any(d in full_attr.split(".") for d in dangerous_attr):
                self.errors.append(f"禁止调用危险方法: {full_attr}")
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name not in ALLOWED_IMPORTS:
                self.errors.append(f"禁止 import '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.module not in ALLOWED_IMPORTS:
            self.errors.append(f"禁止 from import '{node.module}'")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        full_attr = self._get_full_attr(node)
        if full_attr:
            # 禁止访问 __dunder__ 属性和 _private 属性
            if full_attr.endswith("__") and not full_attr.startswith("pd") and not full_attr.startswith("np"):
                self.errors.append(f"禁止访问 dunder 属性: {full_attr}")
        self.generic_visit(node)

    def _get_full_attr(self, node: ast.Attribute) -> Optional[str]:
        """递归解析属性链，例如 a.b.c → 'a.b.c'"""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value  # type: ignore
        if isinstance(current, ast.Name):
            parts.append(current.id)
        elif isinstance(current, ast.Call):
            return None
        else:
            return None
        return ".".join(reversed(parts))


def _check_safety(code: str):
    """用 AST 静态分析检查代码安全性（替代旧版子串匹配）"""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SandboxError(f"Python 语法错误: {e}")

    analyzer = _SafetyAnalyzer()
    analyzer.visit(tree)
    if analyzer.errors:
        raise SandboxError("安全性限制：" + "；".join(analyzer.errors[:5]))


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
        # 安全内置函数（排除 eval/exec/compile/open/__import__/input/breakpoint）
        safe_builtins = {
            "dict": dict, "list": list, "str": str, "int": int, "float": float,
            "bool": bool, "len": len, "range": range, "zip": zip, "map": map,
            "filter": filter, "min": min, "max": max, "sum": sum, "abs": abs,
            "round": round, "sorted": sorted, "reversed": reversed,
            "enumerate": enumerate, "isinstance": isinstance,
            "True": True, "False": False, "None": None,
            "print": lambda *a: None,
        }
        exec(code, {"__builtins__": safe_builtins}, local_vars)
    except Exception as e:
        raise SandboxError(f"Python 执行错误: {e}")

    # 提取结果中新增的 DataFrame 和数值
    result = {}
    for k, v in local_vars.items():
        if k in ALLOWED_MODULES or k in data:
            continue
        if isinstance(v, (pd.DataFrame, pd.Series, int, float, str, list, dict)):
            if isinstance(v, pd.DataFrame):
                result[k] = v.to_dict(orient="records")
            elif isinstance(v, pd.Series):
                result[k] = v.to_list()
            else:
                result[k] = v
    return result
