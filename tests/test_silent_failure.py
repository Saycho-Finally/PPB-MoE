"""静默失败检测测试（v0.3 增量）。

静默失败 = 调用**报成功**，但产出实际不可用。与显式失败（ok=False）区分记账：
显式失败会抬高工具错误率，静默失败会抬高静默率——两者的处置不同。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from moecore import (CognitiveMonitor, ExpertAdapter, ExpertSpec,  # noqa: E402
                     Orchestrator, detect_silent_failure)

RESULTS = []


def check(name, cond, note=""):
    s = "PASS" if cond else "FAIL"
    RESULTS.append((name, s))
    print(f"  [{s}] {name}" + (f" ---- {note}" if note else ""))


def test_detect_kinds():
    print("四类静默失败")
    check("显式失败不算静默失败",
          detect_silent_failure("e", False, None) is None)
    for out in (None, "", {}, []):
        sf = detect_silent_failure("e", True, out)
        check(f"空产出 {out!r} → empty_output",
              sf is not None and sf.kind == "empty_output")
    sf = detect_silent_failure("cache", True,
                               {"orchestrated": True, "note": "纪律就位"})
    check("只有说明字段 → degraded_note",
          sf is not None and sf.kind == "degraded_note", sf.detail if sf else "")
    sf = detect_silent_failure("e", True, {"answer": "结果占位，稍后补"})
    check("含占位标记 → placeholder",
          sf is not None and sf.kind == "placeholder")
    sf = detect_silent_failure("e", True, {"x": 1}, payload={"x": 1})
    check("产出等于输入 → no_op_echo",
          sf is not None and sf.kind == "no_op_echo")


def test_no_false_positive():
    print("不误报")
    check("正常产出不报错",
          detect_silent_failure("e", True, {"answer": 42}) is None)
    check("说明字段 + 实质字段 → 正常",
          detect_silent_failure("e", True,
                                {"note": "ok", "answer": 42}) is None)
    check("纯文本实质产出 → 正常",
          detect_silent_failure("e", True, "北京") is None)
    check("无 payload 时不判回显",
          detect_silent_failure("e", True, {"x": 1}) is None)


def test_monitor_accounting():
    print("监控记账")
    mon = CognitiveMonitor()
    mon.record_output("a", True, {"answer": 1})
    mon.record_output("b", True, {"note": "不可用"})
    mon.record_output("c", True, None)
    mon.record_output("d", False, None)          # 显式失败，不计入静默
    r = mon.report()
    check("产出总数计入", r["outputs_total"] == 4)
    check("静默失败 2 例", len(mon.silent_alerts) == 2,
          str([a["kind"] for a in mon.silent_alerts]))
    check("静默率 = 2/4", r["silent_rate"] == 0.5)
    check("显式失败不抬高静默率", all(a["expert"] != "d" for a in mon.silent_alerts))
    check("静默率高 → degraded", mon.health() == "degraded")


def test_health_bands():
    print("健康分档")
    mon = CognitiveMonitor()
    for i in range(10):
        mon.record_output("a", True, {"answer": i})
    check("全正常 → healthy", mon.health() == "healthy")
    mon.record_output("b", True, {"note": "降级"})
    check("少量静默 → watch", mon.health() == "watch",
          f"rate={mon.report()['silent_rate']}")


def test_orchestrator_integration():
    print("编排接线")
    orch = Orchestrator()
    orch.register(ExpertAdapter(
        ExpertSpec(name="noop", capabilities={"do"}, cost_tier=1),
        lambda t: {"orchestrated": True, "note": "组件不可用，纪律就位"},
        "静默失败专家"))
    orch.register(ExpertAdapter(
        ExpertSpec(name="good", capabilities={"work"}, cost_tier=1),
        lambda t: {"answer": 42}, "正常专家"))
    r = orch.execute("t1", {"do"}, {})
    check("执行结果带 silent_failure 字段",
          r["ok"] is True and r["silent_failure"] == "degraded_note",
          str(r["silent_failure"]))
    r2 = orch.execute("t2", {"work"}, {})
    check("正常专家不标静默失败", r2["silent_failure"] is None)
    h = orch.health()
    check("健康报告含静默率",
          h["monitor"]["silent_rate"] == 0.5
          and len(h["monitor"]["silent_failures"]) == 1)


if __name__ == "__main__":
    print("=" * 62)
    print("PPB-MoE v0.3：静默失败检测")
    print("=" * 62)
    test_detect_kinds()
    test_no_false_positive()
    test_monitor_accounting()
    test_health_bands()
    test_orchestrator_integration()
    print("=" * 62)
    n_pass = sum(1 for r in RESULTS if r[1] == "PASS")
    print(f"总计：{n_pass}/{len(RESULTS)} PASS")
    print("SILENT_FAILURE_OK" if n_pass == len(RESULTS) else "SILENT_FAILURE_FAIL")
    sys.exit(0 if n_pass == len(RESULTS) else 1)
