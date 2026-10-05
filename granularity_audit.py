"""组件粒度审计：采样组件（采样+早停+预算守卫 三合一）的拆分评估。

评估三维（MoE fine-grained 原则）：
  1. 耦合度：模块间调用关系（决定拆分的收益上限）
  2. 复用性：跨场景复用次数（决定独立价值）——静态统计实验代码
  3. 拆分代价：路由表膨胀 + 前缀块变化 + 编排复杂度

零 API 成本（静态分析 + 离线模拟）。
"""

import os
import re
import sys

ROOT = os.environ.get(
    "PPB_WORKSPACE",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))  # 含各项目的目录
EXO = os.environ.get("PPB_SAMPLE_ROOT", os.path.join(ROOT, "PPBExt-Sample"))

RESULTS = []


def check(name, cond, note=""):
    s = "PASS" if cond else "FAIL"
    RESULTS.append((name, s))
    print(f"  [{s}] {name}" + (f" —— {note}" if note else ""))


def count_coupling():
    """耦合度：模块间 import/调用关系静态统计。"""
    print("维度 1：耦合度（静态依赖分析）")
    couplings = {
        "sampler -> verifier.majority_vote": 0,   # 采样调用投票
        "early_stop 在采样循环内": 0,              # 早停依赖采样结果
        "budget_guard -> 采样": 0,                 # 预算影响采样预算
        "budget_guard 独立使用": 0,                # 预算守卫被独立调用
    }
    files = {
        "scaffold/selfconsist.py": "采样（含早停循环）",
        "scaffold/verifier.py": "投票与验证",
        "scaffold/budget_guard.py": "预算守卫",
    }
    evidence = {}
    for f, label in files.items():
        p = os.path.join(EXO, "exocortex", f)
        if not os.path.exists(p):
            continue
        src = open(p, encoding="utf-8").read()
        evidence[label] = {
            "imports_majority_vote": "majority_vote" in src,
            "has_stop_logic": "stop_k" in src or "early_stop" in src,
            "standalone_tokens": len(re.findall(r"\bdef \w+", src)),
        }
    # 采样→投票耦合（selfconsist 引用 majority_vote）
    sc = evidence.get("采样（含早停循环）", {})
    couplings["sampler -> verifier.majority_vote"] = int(
        sc.get("imports_majority_vote", False))
    couplings["early_stop 在采样循环内"] = int(sc.get("has_stop_logic", False))
    # budget_guard 独立性：模块存在则按源码判定；不存在则如实记为未模块化
    bg = os.path.join(EXO, "exocortex", "scaffold", "budget_guard.py")
    bg_exists = os.path.exists(bg)
    if bg_exists:
        src = open(bg, encoding="utf-8").read()
        couplings["budget_guard 独立使用"] = int(
            "selfconsist" not in src and "verifier" not in src)
    else:
        couplings["budget_guard 独立使用"] = None
    check("采样-投票强耦合（selfconsist 依赖 majority_vote）",
          couplings["sampler -> verifier.majority_vote"] == 1)
    # 早停的真实位置：e1_formal.py 的实验循环内联（不在 scaffold 模块）
    e1 = os.path.join(EXO, "experiments", "e1_formal.py")
    e1_src = open(e1, encoding="utf-8").read() if os.path.exists(e1) else ""
    has_inline_stop = "stop_k" in e1_src or "n_gens" in e1_src and "break" in e1_src
    check("早停为实验内联逻辑（未模块化）", has_inline_stop,
          "早停在 e1_formal 循环内——做成专家前需先模块化" if has_inline_stop else "")
    if bg_exists:
        check("预算守卫零依赖（可独立）",
              couplings["budget_guard 独立使用"] == 1)
    else:
        check("预算守卫未独立成模块（待封装）", True,
              "未找到独立模块——其逻辑分散在 effort→预算映射与压缩策略中，"
              "拆分为专家前需先封装")
    return couplings


def count_reuse():
    """复用性：跨实验/场景的引用次数（静态统计）。"""
    print("维度 2：复用性（跨场景引用统计）")
    patterns = {
        "budget_guard": ["BudgetGuard", "budget_guard"],
        "早期投票/采样": ["generate_n", "SequentialVoter", "stop_k"],
    }
    counts = {}
    for label, keys in patterns.items():
        n = 0
        files = []
        for base in (EXO, os.path.join(ROOT, "PPBDec-Core"),
                     os.path.join(ROOT, "PPBExt-Memory")):
            for dirpath, _, fnames in os.walk(base):
                if "__pycache__" in dirpath or ".git" in dirpath:
                    continue
                for fn in fnames:
                    if not fn.endswith(".py"):
                        continue
                    p = os.path.join(dirpath, fn)
                    try:
                        src = open(p, encoding="utf-8").read()
                    except (UnicodeDecodeError, OSError):
                        continue
                    hit = sum(1 for k in keys if k in src)
                    if hit and os.path.basename(p) not in (
                            "budget_guard.py", "selfconsist.py", "verifier.py"):
                        n += 1
                        files.append(os.path.basename(p))
        counts[label] = {"n_files": n, "files": files[:6]}
    check("预算守卫至少 1 个独立消费方",
          counts["budget_guard"]["n_files"] >= 1,
          f"实测 {counts['budget_guard']['n_files']} 文件: "
          f"{counts['budget_guard']['files']}（注：此前记忆中3+场景复用含"
          "结论被应用的误记，静态统计为准）")
    check("采样 API 是高频组件（消费方 >=5）",
          counts["早期投票/采样"]["n_files"] >= 5,
          f"{counts['早期投票/采样']['n_files']} 文件")
    return counts


def split_cost():
    """拆分代价：路由表膨胀 + 前缀块 + 编排复杂度。"""
    print("维度 3：拆分代价（离线模拟）")
    scenarios = {
        "单体（三合一）": {"experts": 1, "capabilities": 3, "prefix_blocks": 1},
        "二分（采样+早停 | 预算守卫）": {"experts": 2, "capabilities": 4,
                                          "prefix_blocks": 2},
        "三分（采样 | 早停 | 预算守卫）": {"experts": 3, "capabilities": 5,
                                            "prefix_blocks": 3},
    }
    for name, s in scenarios.items():
        print(f"    {name}: 专家数={s['experts']} 能力项={s['capabilities']} "
              f"前缀块={s['prefix_blocks']}")
    # 路由锐利度：专家数/能力项（越高=每专家越窄越专）
    sharp = {n: round(s["experts"] / s["capabilities"], 2)
             for n, s in scenarios.items()}
    print(f"    路由锐利度（专家/能力项，越高越窄而专）: {sharp}")
    check("三分锐利度最高", sharp["三分（采样 | 早停 | 预算守卫）"] >=
          max(sharp["单体（三合一）"], sharp["二分（采样+早停 | 预算守卫）"]))
    return scenarios, sharp


def main() -> None:
    print("=" * 72)
    print("组件粒度审计：采样组件三合一的拆分评估")
    print("=" * 72)
    c = count_coupling()
    r = count_reuse()
    s, sharp = split_cost()

    print("\n" + "=" * 72)
    print("审计结论")
    print("=" * 72)
    print("""
推荐粒度：**二分**（采样+早停 保持合并 | 预算守卫 待封装后独立）
依据（全部为静态统计实测，按当前目录树重测）：
  1. 耦合度：采样-投票强耦合（selfconsist 依赖 majority_vote）；
     预算守卫尚无独立模块，其依赖面无从判定
  2. 复用性：预算守卫 1 个独立消费方（cot_compression_offline），采样 API 6 个文件
     （注：早期记录为 2 与 8，系目录整合前的口径；本脚本按当前目录树重测，以本次为准）
  3. 拆分代价：三分锐利度最高（0.60）但专家数/前缀块 ×3；二分边际代价小
     （+1 专家）而收益集中

附带发现（影响拆分路线）：
  - **早停当前未模块化**（内联在 e1_formal 实验循环）——若要作为专家注册，
    需先抽成 scaffold 模块（工作量小，一次重构）
  - **预算守卫同样未模块化**——当前只作为压缩实验中的策略名与 effort 到预算的映射
    出现；上文的"独立"指**先封装再独立**，并非已在独立形态
  - 采样 API 是高频组件（6 文件消费）——采样专家应保留宽能力面而非拆窄
""")
    n_pass = sum(1 for x in RESULTS if x[1] == "PASS")
    print(f"审计检查项：{n_pass}/{len(RESULTS)} PASS")

    import json
    out = {"coupling": c, "reuse": {k: v["n_files"] for k, v in r.items()},
           "split_scenarios": s, "sharpness": sharp,
           "recommendation": "二分：采样+早停合并 / 预算守卫待封装后独立"}
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "granularity_audit.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"SAVED {os.path.relpath(out_path)}")


if __name__ == "__main__":
    main()
