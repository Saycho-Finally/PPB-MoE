# PPB-MoE Spec v0.1（2026-10-04）

> 定位：应用层稀疏 MoE 的编排层——专家注册、路由执行、治理与观测。
> 拆分自 PPBDec-Core（决策层保留 DecisionCore；MoE 层独立成此仓库）。

## 一、拆分依据

原 DecisionCore 包含两层职责：
- **决策层**（DecisionPoint 类型学 / 判定器光谱 / 审计）→ 留 PPBDec-Core
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


## 五、治理层的学术依据（2026-10-04 检索对齐）

**Harness Continual Learning（HCL）** 框架（arXiv）提出 **harness-level forgetting**：
外部组件（prompts / tools / memories / routing）的更新会破坏既有可靠行为，**即使基座
模型冻结**。其四组件（Task Interface / Experience Memory / **Capability Map** /
**Adaptive Router**）与本仓库的治理层 + 专家池 + 编排运行时对应；其
**Guarded Evolution Protocol**（提议 → 评估 → 提交：候选配置须通过"当前性能提升 +
历史行为保持 + 功能有效性"三验收）与本仓库的对应关系：

| HCL 概念 | 本仓库实现 |
|---|---|
| Capability Map | `ExpertRegistry`（能力契约） |
| Adaptive Router | `Orchestrator.route`（bias 调整） |
| 提议-评估-提交 | `Governance.can_load` 预检 + `rebalance` 观测回灌 |
| 历史行为保持 | `CognitiveMonitor`（工具错误率/循环/路由健康）|

**声明**：HCL 为他人工作，本仓库不主张其概念的原创性；此处为应用层的独立实现与映射。
