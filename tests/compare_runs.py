"""
评测对比工具

跑一次全量测试，与上一次结果对比，输出 diff。
支持记录历史 Runs，查看趋势。

用法：
  python tests/compare_runs.py               # 跑测试 + 对比历史
  python tests/compare_runs.py --history     # 查看历史记录
  python tests/compare_runs.py --reset       # 清空历史
"""
import json
import sys
import time
from pathlib import Path

HISTORY_FILE = Path("reports/eval_history.json")
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_history() -> list[dict]:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return []


def save_report(results: dict):
    history = load_history()
    history.append({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": results,
    })
    # 只保留最近 20 次
    HISTORY_FILE.write_text(
        json.dumps(history[-20:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def compare(prev: dict, curr: dict) -> list[dict]:
    """对比两次结果，返回差异列表"""
    diffs = []
    all_keys = set(list(prev.keys()) + list(curr.keys()))
    for key in sorted(all_keys):
        p = prev.get(key)
        c = curr.get(key)
        if p != c:
            if isinstance(p, (int, float)) and isinstance(c, (int, float)):
                delta = c - p
                symbol = "+" if delta > 0 else ""
                diffs.append({
                    "metric": key,
                    "before": p,
                    "after": c,
                    "delta": f"{symbol}{delta:.2%}" if isinstance(delta, float) and delta < 1 else f"{symbol}{delta}",
                })
            else:
                diffs.append({
                    "metric": key,
                    "before": p,
                    "after": c,
                    "delta": "changed",
                })
    return diffs


def print_history():
    history = load_history()
    if not history:
        print("暂无历史记录")
        return
    print(f"{'时间':<20} {'用例数':<8} {'通过率':<8} {'P50ms':<8}")
    print("-" * 50)
    for h in history:
        r = h.get("results", {})
        ts = h["timestamp"][:16]
        total = r.get("total", 0)
        passed = r.get("passed", 0)
        rate = f"{passed/total*100:.0f}%" if total else "-"
        p50 = r.get("p50", "-")
        print(f"{ts:<20} {total:<8} {rate:<8} {p50:<8}")


def run_tests() -> dict:
    """简化测试：跑冒烟并采集结果"""
    import urllib.request
    import json as _json

    BASE = "http://127.0.0.1:8000"
    queries = [
        ("项目使用什么技术栈？", True),
        ("服务器宕机了怎么办？", True),
        ("数据安全分几个等级？", True),
        ("Node.js 版本有要求吗？", False),
        ("你是一个什么样的系统？", True),
    ]

    results = {"total": 0, "passed": 0, "failed": 0, "p50": 0, "p90": 0, "p99": 0}
    latencies = []

    for query, expect_hit in queries:
        data = _json.dumps({"query": query}).encode()
        req = urllib.request.Request(
            f"{BASE}/api/rag/query", data=data,
            headers={"Content-Type": "application/json"},
        )
        t0 = time.perf_counter()
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            raw = resp.read().decode("utf-8", errors="replace")
            elapsed = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed)
            results["total"] += 1
            has_hit = '"sources"' in raw and '未找到' not in raw
            if has_hit == expect_hit:
                results["passed"] += 1
            else:
                results["failed"] += 1
                print(f"  FAIL: {query[:30]} (期望命中={expect_hit}, 实际={has_hit})")
        except Exception as e:
            results["total"] += 1
            results["failed"] += 1
            print(f"  ERR: {query[:30]}: {str(e)[:60]}")

    if latencies:
        sorted_lat = sorted(latencies)
        l = len(sorted_lat)
        results["p50"] = round(sorted_lat[l // 2], 1)
        results["p90"] = round(sorted_lat[int(l * 0.9)], 1)
        results["p99"] = round(sorted_lat[int(l * 0.99)], 1)
        results["latency_avg"] = round(sum(latencies) / l, 1)

    return results


if __name__ == "__main__":
    if "--history" in sys.argv:
        print_history()
        sys.exit(0)

    if "--reset" in sys.argv:
        HISTORY_FILE.write_text("[]", encoding="utf-8")
        print("历史已清空")
        sys.exit(0)

    print(f"正在执行测试...")
    results = run_tests()

    history = load_history()
    last_results = history[-1]["results"] if history else {}

    if last_results:
        print(f"\n对比上一次结果:")
        diffs = compare(last_results, results)
        if diffs:
            print(f"{'指标':<20} {'上次':<10} {'本次':<10} {'变化':<10}")
            print("-" * 50)
            for d in diffs:
                print(f"{d['metric']:<20} {str(d['before']):<10} {str(d['after']):<10} {d['delta']:<10}")
        else:
            print("  无变化")

    save_report(results)

    total = results["total"]
    passed = results["passed"]
    rate = f"{passed/total*100:.0f}%" if total else "-"
    print(f"\n本次结果: {passed}/{total} = {rate}")
    print(f"延迟: P50={results.get('p50','-')}ms  P90={results.get('p90','-')}ms")
    print(f"报告已保存: {HISTORY_FILE}")
