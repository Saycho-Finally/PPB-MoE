# 变更记录 (Changelog)

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

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

