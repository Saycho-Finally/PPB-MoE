# Addenda-MoE Spec v0.1（2026-10-04）

> 定位：应用层稀疏 MoE 的编排层——专家注册、路由执行、治理与观测。
> 拆分自 Addenda-Decide（决策层保留 DecisionCore；MoE 层独立成此仓库）。

## 一、拆分依据

原 DecisionCore 包含两层职责：
- **决策层**（DecisionPoint 类型学 / 判定器光谱 / 审计）→ 留 Addenda-Decide
- **编排层**（专家池 / 路由运行时 / 治理 / 观测）→ 本仓库

拆分接口：Decide 的 route 决策需要专家池——通过 `moecore.registry` 可选依赖
（Decide 核心保持零依赖，route 增强需要 moecore）。

## 二、核心设计

1. **能力契约路由**：ExpertSpec(capabilities, cost_tier, deterministic)——不按人格化
   角色；确定性专家优先（程序验证 > LLM）
2. **bias 调整路由**：得分 = 1/cost_tier × runtime_bias——运行时可调，不改任务定义
3. **观测回灌**：CognitiveMonitor 记账 → rebalance（过载降/饿死升）→ 路由偏好变化
   （auxiliary-loss-free 的应用层实现）
4. **治理预检**：装载前互斥资源/依赖/版本检查，`can_load` 不注册即可拦截
5. **清晰的失败**：无覆盖能力返回 no expert（不静默降级）

## 三、与各外挂的接口

| 外挂 | 提供的能力 | 接线方式 |
|---|---|---|
| 知识 | knowledge_gate | curator 规则门 |
| 缓存 | prefix_orchestration | PrefixBank 三区 |
| 思考 | solve / compute（采样+早停）| 采样器 + 投票 |
| 决策 | verify / judge | DecisionCore 判定器 |
| 记忆 | remember / recall | MemoryStore + 折叠 |

## 四、红线

- 不做组件级首创声明（能力路由/负载均衡/gating 均有 MoE 文献先例）
- 增量是**应用层接线**：把 MoE 的路由纪律落到 LLM 应用外挂（prompt/API 级）
- 所有结论带静态统计或实测口径
