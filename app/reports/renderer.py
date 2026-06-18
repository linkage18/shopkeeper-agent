from __future__ import annotations
import io
import os
import base64
from pathlib import Path
from datetime import datetime

from app.core.log import logger

CHARTS_DIR = Path("data/charts")
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

_HAS_MPL = False
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    _HAS_MPL = True
except ImportError:
    logger.warning("matplotlib not installed, charts will be skipped")


def _ensure_chinese_font():
    if not _HAS_MPL:
        return None
    import os
    font_candidates = [
        "Microsoft YaHei",
        "Microsoft YaHei UI",
        "SimHei",
        "WenQuanYi Micro Hei",
        "Noto Sans SC",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
        "DengXian",
        "FangSong",
        "KaiTi",
    ]
    # 先尝试用 font name 匹配
    for name in font_candidates:
        try:
            fp = fm.FontProperties(family=name)
            # 验证字体是否真的可用（检查能否渲染中文）
            test_font = fp.get_name()
            if test_font and test_font != "DejaVu Sans":
                return fp
        except Exception:
            continue
    # 用 font_manager 扫描系统字体目录
    try:
        font_dirs = [
            "C:/Windows/Fonts",
            "/usr/share/fonts",
            "/System/Library/Fonts",
        ]
        for font_dir in font_dirs:
            if os.path.isdir(font_dir):
                for root, dirs, files in os.walk(font_dir):
                    for f in files:
                        if f.endswith((".ttf", ".ttc")) and any(k in f.lower() for k in ["yahei", "simhei", "noto", "chinese", "cjk", "deng", "fang", "kai"]):
                            try:
                                fp = fm.FontProperties(fname=os.path.join(root, f))
                                return fp
                            except Exception:
                                continue
    except Exception:
        pass
    return None


def generate_chart(data: list[dict], chart_config: dict, params: dict) -> str | None:
    if not _HAS_MPL:
        return None
    if not data or chart_config.get("type") == "table":
        return None
    try:
        chart_type = chart_config["type"]
        x_field = chart_config["x"]
        y_fields = chart_config["y"]
        title = chart_config.get("title", "")
        for k, v in params.items():
            title = title.replace("{" + k + "}", str(v))

        fp = _ensure_chinese_font()
        if fp:
            # 全局设置中文字体，避免 tick labels 和 legend 乱码
            plt.rcParams["font.family"] = fp.get_name()
            plt.rcParams["axes.unicode_minus"] = False
        fig, ax = plt.subplots(figsize=(10, 5))

        x_vals = [str(row.get(x_field, "")) for row in data]
        y_vals = [float(row.get(y_fields[0], 0)) for row in data]

        if chart_type == "bar":
            ax.bar(x_vals, y_vals, color="#5a8a7a")
            plt.xticks(rotation=45, ha="right")
        elif chart_type == "line":
            ax.plot(x_vals, y_vals, marker="o", color="#c4901a", linewidth=2)
            plt.xticks(rotation=45, ha="right")
        elif chart_type == "pie":
            colors = ["#c4901a", "#5a8a7a", "#1a1a18", "#d6d3d1", "#a8a29e"]
            wedges, texts, autotexts = ax.pie(
                y_vals, labels=x_vals, autopct="%1.1f%%",
                colors=colors[:len(x_vals)], startangle=90,
            )
            if fp:
                for t in texts + autotexts:
                    t.set_fontproperties(fp)

        if fp:
            ax.set_title(title, fontproperties=fp, fontsize=14)
            ax.set_xlabel(chart_config.get("x", ""), fontproperties=fp)
            ax.set_ylabel(y_fields[0] if y_fields else "", fontproperties=fp)
        else:
            ax.set_title(title, fontsize=14)
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150)
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode()
        plt.close(fig)
        return b64
    except Exception as e:
        logger.error(f"chart generation failed: {e}")
        return None


def build_report(params: dict, template: dict, results: dict[str, list[dict]],
                 chart_b64: str | None) -> str:
    template_name = template.get("label", "分析报告")
    metric = params.get("metric", "")
    start = params.get("start_date", "")
    end = params.get("end_date", "")
    dimension = params.get("dimension", "")

    lines = []
    lines.append(f"# {template_name}\n")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    if metric:
        lines.append(f"## 概述\n分析 {metric}")
        if start and end:
            lines.append(f"，时间范围 {start} ~ {end}")
        lines.append("\n")

    if chart_b64:
        lines.append("## 图表\n")
        lines.append(f'![chart](data:image/png;base64,{chart_b64})\n')

    for sql_id, rows in results.items():
        from app.reports.executor import build_markdown_table
        if sql_id.endswith("_error"):
            lines.append(f"## {sql_id}\n> {rows}\n")
            continue
        if not isinstance(rows, list) or not rows:
            lines.append(f"## {sql_id}\n> 无数据\n")
            continue
        if not isinstance(rows[0], dict):
            lines.append(f"## {sql_id}\n> 数据格式异常\n")
            continue
        if sql_id == "total":
            total_val = rows[0].get("total", 0)
            lines.append(f"## 汇总\n总计：**{total_val}**\n")
            continue
        lines.append(f"## {sql_id}\n")
        lines.append(build_markdown_table(rows))
        lines.append("")

    return "\n".join(lines)
