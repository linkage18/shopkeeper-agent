"""
Report Renderer — 从 SQL 结果构建 ECharts 兼容的 chart_data
"""
from typing import Any


def build_chart_data(data: list[dict], chart_info: dict) -> dict[str, Any] | None:
    """从 SQL 结果和图表配置生成 chart_data"""
    if not data:
        return None
    chart_type = chart_info.get("chart_type", "bar")
    title = chart_info.get("chart_title", "")

    # 自动选择 x 轴和 y 轴字段
    keys = list(data[0].keys())
    if len(keys) < 2:
        return None

    # 找数值字段作为 y 轴
    x_field = keys[0]
    y_field = None
    for k in keys:
        if isinstance(data[0][k], (int, float)):
            y_field = k
            break
    if not y_field:
        y_field = keys[1]

    labels = [str(row.get(x_field, "")) for row in data]
    values = [float(row.get(y_field, 0)) for row in data]

    return {
        "chart_type": chart_type,
        "title": title,
        "labels": labels,
        "values": values,
    }
