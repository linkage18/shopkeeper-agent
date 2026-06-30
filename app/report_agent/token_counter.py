"""
向后兼容 — token_counter 已移至 app.core.token_counter
"""
from app.core.token_counter import TokenCounter, token_counter  # noqa: F401
