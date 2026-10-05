# PPB-MoE Spec v0.2（2026-10-05）

> 定位：**应用层稀疏 MoE 的编排层**——专家注册、能力路由、执行编排、装载期治理与
> 运行时观测。本仓库覆盖治理与编排两层，并把基础设施（路由记录与健康报告）内置于运行时。
>
> 与决策子层的关系：本仓库提供专家能力契约与路由分布统计，决策子层可消费它们；
> 本仓库核心保持零依赖，不反向依赖决策子层。

## 一、层级定位

| 层 | 本仓库是否覆盖 | 内容 |
|---|---|---|
| 治理 | 是 | 装载前冲突 / 依赖 / 版本预检 + 认知可观测性 |
| 编排 | 是 | 专家注册、能力路由、bias 调整、执行、审计 |
| 决策 | 否（消费方） | 决策类型学与判定器光谱由决策子层提供 |
| 组件 | 否（消费方） | 知识注入 / 缓存 / 采样 / 记忆 / 修复由各自实现提供 |

## 二、核心设计

1. **能力契约路由**：ExpertSpec(capabilities, cost_tier, deterministic)——不按人格化
   角色；确定性专家优先（程序验证 > LLM）
2. **bias 调整路由**：得分 = 1/cost_tier × runtime_bias——运行时可调，不改任务定义
3. **观测回灌**：CognitiveMonitor 记账 → rebalance（过载降 / 饿死升）→ 路由偏好变化
   （auxiliary-loss-free 的应用层实现）
4. **治理预检**：装载前互斥资源 / 依赖 / 版本检查，`can_load` 不注册即可拦截
5. **清晰的失败**：无覆盖能力返回 no expert（不静默降级）

## 三、接口契约

本仓库对外提供的能力与消费方式：

| 能力 | 提供者 | 消费方式 |
|---|---|---|
| knowledge_gate | 知识注入组件 | 规则门 |
| prefix_orchestration | 缓存组件 | 三区前缀编排 |
| solve / compute | 采样组件 | 采样器 + 投票早停 |
| verify / judge | 决策子层 | 判定器 |
| remember / recall | 记忆组件 | 存储 + 折叠 |
| 修复链 | 修复组件 | 四 pass 流水线 |

接线方式为 `ExpertAdapter`（能力契约 + 执行入口）。组件缺失时该专家跳过注册，
其余部分照常运行。

## 四、红线

- 不做组件级首创声明（能力路由 / 负载均衡 / gating 均有 MoE 文献先例）
- 增量是**应用层接线**：把稀疏专家的路由纪律落到 LLM 应用组件（prompt/API 级）
- 所有结论带静态统计或实测口径

## 五、治理层的学术依据

**Harness Continual Learning（HCL）** 框架提出 **harness-level forgetting**：
外部组件（prompts / tools / memories / routing）的更新会破坏既有可靠行为，**即使基座
模型冻结**。其四组件（Task Interface / Experience Memory / **Capability Map** /
**Adaptive Router**）与本仓库的治理 + 专家池 + 编排运行时对应；其
**Guarded Evolution Protocol**（提议 → 评估 → 提交：候选配置须通过"当前性能提升 +
历史行为保持 + 功能有效性"三验收）与本仓库的对应关系：

| HCL 概念 | 本仓库实现 |
|---|---|
| Capability Map | `ExpertRegistry`（能力契约） |
| Adaptive Router | `Orchestrator.route`（bias 调整） |
| 提议—评估—提交 | `Governance.can_load` 预检 + `rebalance` 观测回灌 |
| 历史行为保持 | `CognitiveMonitor`（工具错误率 / 循环 / 路由健康） |

**声明**：HCL 为他人工作，本仓库不主张其概念的原创性；此处为应用层的独立实现与映射。
