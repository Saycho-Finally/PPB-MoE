# 变更记录 (Changelog)

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added

- `reports/外部对照_查新_2026-10-06.md`：失败分类学逐类对照（O2）、ALF-LB 作用层
  区分（O4）、静默失败检测的业界实践定位（O3 补充）。确认监控缺口：陈旧上下文与
  证据矛盾两类超出确定性监控范围，如实记录

## [0.3.0] - 2026-10-05

### Added

- **静默失败检测**（认知可观测性的第五个维度）：区分"调用报成功但产出实际不可用"
  与显式失败。四类确定性规则——空产出 / 只有说明字段 / 含占位标记 / 产出等于输入
- `detect_silent_failure()` 与 `SilentFailure`；`CognitiveMonitor.record_output()`
  记账并累计 `outputs_total` / `silent_rate`；健康分档纳入静默率
- 编排执行结果新增 `silent_failure` 字段；演示脚本展示每个子任务的静默失败标记
- `tests/test_silent_failure.py`：22 项测试

### Fixed

- 演示脚本的缓存专家导入了一个**不存在的符号**（`PrefixBank`），
  被宽泛的 `except` 吞掉后降级为"纪律就位"的说明性输出——即一个真实的静默失败。
  修正为 `PrefixBankSession`，并改为离线验证前缀**字节稳定性**
  （同配置两会话的 prefix 与 log 指纹一致），不再降级

## [0.2.0] - 2026-10-05

### Added

- `reports/编排运行时验证_2026-10-05.md`：路由偏置与观测回灌的实测报告

### Fixed

- 编排 demo 的记忆专家注册失败：移除了对决策核的错误依赖（决策核为可选注入，
  缺失时不应阻断专家注册）。修复后五专家全部注册，路由熵达 log2(5)=2.32
- 编排 demo 的兄弟仓库路径改为当前仓库名，并支持环境变量覆盖

### Changed

- 术语统一：清单类型改为 `ComponentManifest`；治理报告字段改为 `n_components`
- 文档口径统一为可复现的实际数字

## [0.1.0] - 2026-10-04

- 首个版本：专家池 / 路由运行时 / 装载前治理 / 认知可观测性四模块
- 五专家接线 demo + 组件粒度审计（二分结论）

