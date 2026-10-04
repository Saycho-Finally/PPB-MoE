# Addenda-MoE ｜ 补遗：应用层稀疏 MoE 的编排层

**一句话**：把 LLM 应用外挂（知识/缓存/思考/决策/记忆）注册为**专家**，用一个统一的
编排层做路由、执行、审计与负载均衡——**"服务端给能力，客户端做路由"** 的运行时实现。

> License: MIT ｜ 核心零依赖 ｜ Python ≥3.10

---

## 四层架构（本仓库覆盖 ①④ 与 ② 的路由侧）

```
① 治理层     Governance（冲突/权限预检）+ CognitiveMonitor（认知可观测性）
② 编排层     Orchestrator（路由/执行/审计）+ ExpertRegistry（专家池）
③ 专家池     知识 / 缓存 / 思考 / 决策 / 记忆（由各外挂仓库提供）
④ 基础设施   Ledger / 进度落盘 / 预热保活（各外挂仓库自带）
```

## 核心组件

| 模块 | 职责 |
|---|---|
| `moecore.registry` | ExpertSpec 能力契约 + ExpertRegistry（确定性优先路由 / 路由熵 / 饿死检测）|
| `moecore.orchestrator` | ExpertAdapter + Orchestrator：**bias 调整路由**（得分 = 1/cost_tier × runtime bias）+ 观测回灌 |
| `moecore.governance` | 装载前预检：互斥资源冲突 / 缺依赖 / 版本；`touches` 权限声明 |
| `moecore.observability` | token 速率预警 / 循环耗尽 / 工具错误率 / 路由健康 |

## 运行时闭环（auxiliary-loss-free balancing 的应用层实现）

```
任务 → 路由（bias 调整）→ 专家执行 → CognitiveMonitor 记账
  → rebalance（过载降 bias / 饿死升 bias）→ 下一轮路由
```

实测（14 项测试）：过载专家降权 1.0 → 0.95；bias 改变路由结果（2.0 bias 的
低频专家战胜 4 倍成本的专家）；5 专家均匀分布时路由熵达理论最大 2.32。

## 快速上手

```python
from moecore import ExpertAdapter, ExpertSpec, Orchestrator

orch = Orchestrator()
orch.register(ExpertAdapter(
    ExpertSpec(name="my_expert", capabilities={"solve"}, cost_tier=1,
               deterministic=True),
    lambda task: {"answer": 42}, "示例专家"))
r = orch.execute("做题", {"solve"}, {})
print(r["expert"], r["output"])        # 路由 → 执行
orch.rebalance()                        # 观测回灌
print(orch.health())                    # 健康报告
```

`orchestration_demo.py` 含五外挂注册的完整端到端示例（离线可跑）。

## 实测与审计

- `MOE_ROADMAP.md`：四层架构路线与缺口状态（7 缺口 6 落地）
- `granularity_audit.py`：外挂粒度审计——**结论：二分**（采样+早停合并 |
  预算守卫独立），依据为耦合度/复用性/拆分代价的三维静态统计（6/6 检查项）
- 全部结论附静态统计口径与诚实标注（含对记忆偏差的纠正）

## 已知局限

- 路由 bias 的调整步长（0.05）与阈值（50%）是启发式初值，未做大样本调参
- 观测回灌的闭环目前是"执行后调整"，未做在线学习
- 治理层的版本校验为占位实现（宿主版本解析由调用方注入）

## 引用的先行者

- MoE 基础模式：DeepSeek-V3（fine-grained + shared experts + auxiliary-loss-free
  balancing）、GShard/Switch（capacity factor）
- Agent 级路由：programmer.ie 的 capability-contract 专家与 RouteDecision 置信度设计
- 治理层对标：DSH 插件冲突检测的工程实践

---

## 贡献与引用

- 贡献指南见 [CONTRIBUTING.md](CONTRIBUTING.md)；行为准则见 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- 安全问题请走 [SECURITY.md](SECURITY.md) 的私密渠道（勿开公开 Issue）
- 版本变更见 [CHANGELOG.md](CHANGELOG.md)；学术引用格式见 [CITATION.cff](CITATION.cff)
- 许可：MIT
