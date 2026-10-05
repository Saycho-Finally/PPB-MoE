"""认知可观测性：组件栈的健康监控（稀疏专家工程实践的三件套 + 路由健康）。

导入自 MoE serving 的监控清单（agent 级 APM）：
  - token velocity：token 消耗速率（上下文膨胀预警）
  - loop exhaustion：循环耗尽（同工具反复调用无进展）
  - tool error rate：工具失败率
  - route health：路由熵 / 专家饿死 / 利用率（消费 ExpertRegistry.snapshot）
"""

from __future__ import annotations

import time
from collections import Counter, deque
from dataclasses import dataclass, field


@dataclass
class ObservabilityEvent:
    ts: float
    kind: str          # token / tool_call / route / output / decision
    payload: dict = field(default_factory=dict)


@dataclass
class SilentFailure:
    """静默失败：调用报成功，但产出实际不可用。"""
    expert: str
    kind: str          # empty_output / degraded_note / placeholder / no_op_echo
    detail: str


# 占位与"其实没做"的标记（小写匹配）
PLACEHOLDER_MARKERS = (
    "占位", "placeholder", "todo", "n/a", "不可用", "not available",
    "unknown", "未实现", "not implemented", "跳过",
)
# 说明性字段：只有这些字段而没有实质产出时，属于"报成功但没干活"
NOTE_KEYS = ("note", "notes", "degraded", "fallback", "orchestrated", "reason")


def detect_silent_failure(expert: str, ok: bool, output,
                          payload: dict | None = None) -> SilentFailure | None:
    """检出四类静默失败（确定性规则，非模型判读）：

      1. empty_output  报成功但产出为空（None / "" / {} / []）
      2. degraded_note 只有说明字段，没有实质产出（如"组件不可用，纪律就位"）
      3. placeholder   产出含占位标记词（词表见 PLACEHOLDER_MARKERS）
      4. no_op_echo    产出与输入相同（无变换）

    显式失败（ok=False）不算静默失败——那已经被记账了。
    """
    if not ok:
        return None
    if output is None or output == "" or output == {} or output == []:
        return SilentFailure(expert, "empty_output", "报成功但产出为空")
    if isinstance(output, dict):
        substantive = {k: v for k, v in output.items()
                       if k not in NOTE_KEYS and v not in (None, "", [], {})}
        if not substantive:
            return SilentFailure(
                expert, "degraded_note",
                f"报成功但只有说明字段：{sorted(output)}")
        text = " ".join(str(v) for v in output.values()).lower()
    else:
        text = str(output).lower()
    hit = [m for m in PLACEHOLDER_MARKERS if m in text]
    if hit:
        return SilentFailure(expert, "placeholder",
                             f"产出含占位标记（{hit[0]}）")
    if payload is not None and output == payload:
        return SilentFailure(expert, "no_op_echo", "产出与输入相同（无变换）")
    return None


class CognitiveMonitor:
    """认知可观测性：为 agent 循环与 MoE 路由提供统一健康台账。"""

    def __init__(self, window: int = 50):
        self.events: deque[ObservabilityEvent] = deque(maxlen=window)
        self.token_history: list[tuple[float, int]] = []
        self.tool_calls: Counter = Counter()
        self.tool_errors: Counter = Counter()
        self.loop_alerts: list[dict] = []
        self.velocity_alerts: list[dict] = []
        self.n_outputs: int = 0
        self.silent_alerts: list[dict] = []

    # ---- 三件套 ----

    def record_tokens(self, n_tokens: int, label: str = "") -> None:
        self.token_history.append((time.time(), n_tokens))
        if len(self.token_history) >= 5:
            recent = [t for _, t in self.token_history[-5:]]
            growth = (recent[-1] - recent[0]) / max(recent[0], 1)
            if growth > 0.5:   # 单轮 50%+ 膨胀 → 预警
                self.velocity_alerts.append(
                    {"ts": time.time(), "label": label, "growth": round(growth, 3)})

    def record_tool_call(self, tool: str, ok: bool = True) -> None:
        self.tool_calls[tool] += 1
        if not ok:
            self.tool_errors[tool] += 1
        self.events.append(ObservabilityEvent(time.time(), "tool_call",
                                              {"tool": tool, "ok": ok}))
        # 循环耗尽：窗口内同工具连续 3 次以上且最近有失败
        last = [e for e in list(self.events)[-6:] if e.kind == "tool_call"]
        if len(last) >= 3 and len({e.payload["tool"] for e in last[-3:]}) == 1 \
                and not last[-1].payload["ok"]:
            self.loop_alerts.append(
                {"ts": time.time(), "tool": tool,
                 "note": "连续同工具调用且末次失败——循环耗尽疑似"})

    def record_route(self, registry_snapshot: dict) -> None:
        self.events.append(ObservabilityEvent(time.time(), "route", registry_snapshot))

    def record_output(self, expert: str, ok: bool, output,
                      payload: dict | None = None) -> SilentFailure | None:
        """为一次执行记账，并检出静默失败（报成功但产出不可用）。

        返回检出的 SilentFailure（无则 None），便于调用方即时处置。
        """
        self.n_outputs += 1
        sf = detect_silent_failure(expert, ok, output, payload)
        if sf is not None:
            self.silent_alerts.append({"ts": time.time(), "expert": sf.expert,
                                       "kind": sf.kind, "detail": sf.detail})
        self.events.append(ObservabilityEvent(
            time.time(), "output",
            {"expert": expert, "ok": ok, "silent": sf.kind if sf else None}))
        return sf

    # ---- 报告 ----

    def report(self) -> dict:
        n_tools = sum(self.tool_calls.values())
        n_err = sum(self.tool_errors.values())
        return {
            "token_events": len(self.token_history),
            "velocity_alerts": self.velocity_alerts[-3:],
            "tool_calls_total": n_tools,
            "tool_error_rate": round(n_err / n_tools, 3) if n_tools else 0.0,
            "loop_alerts": self.loop_alerts[-3:],
            "route_events": sum(1 for e in self.events if e.kind == "route"),
            "outputs_total": self.n_outputs,
            "silent_failures": self.silent_alerts[-3:],
            "silent_rate": (round(len(self.silent_alerts) / self.n_outputs, 3)
                            if self.n_outputs else 0.0),
        }

    def health(self) -> str:
        r = self.report()
        if r["loop_alerts"] or (r["tool_error_rate"] > 0.3) or r["silent_rate"] > 0.2:
            return "degraded"
        if r["velocity_alerts"] or r["silent_failures"]:
            return "watch"
        return "healthy"
