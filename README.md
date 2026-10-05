# PPB-MoE

**一句话**：把外部组件（知识注入 / 前缀缓存 / 采样 / 记忆 / 修复）注册为**专家**，
用一个统一的编排层做路由、执行、审计与负载均衡。

> 作者：Saycho-Finally（独立研究者） ｜ AI 使用声明见 [AI_DISCLOSURE.md](AI_DISCLOSURE.md) ｜ License: MIT ｜ 核心零依赖 ｜ Python ≥3.10

---

## 能做什么

本仓库覆盖**治理**与**编排**两层：

| 模块 | 职责 |
|---|---|
| `moecore.registry` | ExpertSpec 能力契约 + ExpertRegistry（确定性优先路由 / 路由熵 / 饿死检测） |
| `moecore.orchestrator` | ExpertAdapter + Orchestrator：bias 调整路由（得分 = 1/cost_tier × runtime bias）+ 观测回灌 |
| `moecore.governance` | 装载前预检：互斥资源冲突 / 缺依赖 / 版本；`touches` 权限声明 |
| `moecore.observability` | token 速率预警 / 循环耗尽 / 工具错误率 / 路由健康 |

## 与其他仓库的关系

本仓库贯通**治理 / 编排 / 基础设施**三层，是这套系统里横跨多层的仓库，
因此会引用各层实现所在的仓库。专家池中的每项能力由对应仓库提供：

| 能力 | 提供方（仓库） | 所在层 |
|---|---|---|
| 知识注入（内容门 / 技能路由） | [PPBExt-Knowledge](https://github.com/Saycho-Finally/PPBExt-Knowledge) | 组件 |
| 前缀缓存（三区纪律 / 分层判别） | [PPBExt-Cache](https://github.com/Saycho-Finally/PPBExt-Cache) | 组件 |
| 采样（多路采样 / 早停 / 预算守卫） | [PPBExt-Sample](https://github.com/Saycho-Finally/PPBExt-Sample) | 组件 |
| 记忆（分页 / 折叠 / 审计） | [PPBExt-Memory](https://github.com/Saycho-Finally/PPBExt-Memory) | 组件 |
| 修复（四 pass 流水线） | [PPBExt-Repair](https://github.com/Saycho-Finally/PPBExt-Repair) | 组件 |
| 决策核（类型学 / 判定器光谱 / 证据链） | [PPBDec-Core](https://github.com/Saycho-Finally/PPBDec-Core) | 决策 |

数据流向：任务由本仓库路由到组件层的专家；需要判定时消费决策层的能力；
治理与观测由本仓库自带，不下沉到组件层。

接线方式为 `ExpertAdapter`（能力契约 + 执行入口）。上述仓库不是本仓库的硬依赖，
而是**运行时可选接入**：组件不可用时该专家跳过注册，其余部分照常运行
（`orchestration_demo.py` 可离线验证这一降级行为）。

## 运行时闭环

```
任务 → 路由（bias 调整）→ 专家执行 → CognitiveMonitor 记账
  → rebalance（过载降 bias / 饿死升 bias）→ 下一轮路由
```

## 结果

26 项测试全过。可复现的实测点：

- 五专家注册 + 复合任务端到端路由正确（5/6 子任务命中专家）；
  无覆盖能力清晰返回 no expert（不静默降级）
- 过载专家降权 1.0 → 0.95；bias 改变路由结果（bias 2.0 的低频专家战胜 4 倍成本对手）
- 5 专家均匀分布时路由熵达理论最大 log2(5) = 2.32
- 组件粒度审计结论：**二分**（采样+早停合并 / 预算守卫独立），
  依据为耦合度 / 复用性 / 拆分代价的三维静态统计（6/6 检查项）

完整口径与复现路径见 [MOE_ROADMAP.md](MOE_ROADMAP.md) 与 [reports/](reports/)。

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

`orchestration_demo.py` 含五专家注册的完整端到端示例（离线可跑）。

## 仓库结构

```
moecore/         核心库（registry / orchestrator / governance / observability）
tests/           26 项测试（治理与可观测性 + 编排运行时）
results/         组件粒度审计的静态统计输出
reports/         编排运行时验证报告
orchestration_demo.py   五专家注册 + 复合任务端到端示例（离线可跑）
granularity_audit.py    组件粒度审计（三维静态统计）
SPEC.md          设计文档（层级定位 / 接口契约 / 治理依据）
MOE_ROADMAP.md   路线与优化计划
```

## 边界

- 路由 bias 的调整步长（0.05）与阈值（50%）是启发式初值，未做大样本调参
- 观测回灌是"执行后调整"，未做在线学习
- 治理层的宿主版本校验为占位实现（版本解析由调用方注入）
- 编排 demo 依赖各组件所在仓库的源实现；缺失时对应专家跳过注册，其余部分照常运行

## 引用的先行者

- MoE 基础模式：DeepSeek-V3（fine-grained + shared experts + auxiliary-loss-free
  balancing）、GShard / Switch（capacity factor）
- Agent 级能力路由：capability-contract 专家与 RouteDecision 置信度设计（programmer.ie）
- 治理层依据：Harness Continual Learning（harness-level forgetting；
  Guarded Evolution Protocol 的"提议—评估—提交"三验收）

---

## 贡献与引用

- 贡献指南见 [CONTRIBUTING.md](CONTRIBUTING.md)；行为准则见 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- 安全问题请走 [SECURITY.md](SECURITY.md) 的私密渠道（勿开公开 Issue）
- 版本变更见 [CHANGELOG.md](CHANGELOG.md)；学术引用格式见 [CITATION.cff](CITATION.cff)
- 许可：MIT
