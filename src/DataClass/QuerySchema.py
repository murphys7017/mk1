"""
DataClass.QuerySchema 的 Docstring
查询模式的定义，主要用于区分不同类型的查询请求。
类似信息密度，查询那些记忆，查询参数等
ueryPlan 是一个强 schema 的结构体，它必须回答这些问题：

这轮输入的 意图是什么

输入的信息密度属于哪一档（low / mid / high）

是否允许检索

允许检索哪些信息源

允许使用哪些主题标签

用什么 query（或不用）

最多取多少条

是否需要 TTL

允许注入多少 token

失败时如何回退

为什么做出这些决定（reasons）
"""
from dataclasses import dataclass, field
from typing import Any, Any, Literal


@dataclass
class QuerySchema:
    # 1. 意图识别（intent）
    intent: str | None = None
    # 说明：高层语义意图（如 "recall_event", "check_preference", "clarify"），由 AnalyzeResult 推导而来。
    # 作用：供 Executor 和 Assembler 理解上下文，但不触发行为。

    # 2. 信息密度（signal_density）
    signal_density: Literal["low", "mid", "high"] = "low"
    # 说明：直接对应 checklist 第5条。决定是否允许检索的关键开关。

    # 3. 是否允许检索（retrieve）
    retrieve: bool = False
    # 说明：硬闸门控制。若为 False，则 Executor 必须跳过所有 source 查询。

    # 4. 允许的信息源（sources）
    sources: list[Literal["short_term", "mid_term", "long_term", "world_core", "user_profile"]] = field(default_factory=list)
    # 说明：明确授权可查范围。Executor 仅遍历此列表。

    # 5. 主题标签过滤（tags）
    tags: list[str] = field(default_factory=list)
    # 说明：用于在支持 tag 的 source 中做预过滤（如 SQLite 的 WHERE tag IN (...)）。

    # 6. 查询语句（query）
    query: str | None = None
    # 说明：原始或重写的查询字符串。若为 None 且 retrieve=True，可能表示全量拉取（需谨慎）。

    # 7. 结果数量限制（top_k）
    top_k: int = 3
    # 说明：每个 source 最多返回条目数。Executor 必须遵守，不得自行扩大。

    # 8. 生存时间约束（ttl_seconds）
    ttl_seconds: int | None = None
    # 说明：仅用于带时间戳的记忆（如 short/mid term）。Executor 在 source 层过滤过期项。

    # 9. Token 预算（token_budget）
    token_budget: int | None = None
    # 说明：供 Assembler 或后续模块做截断参考，非 Executor 职责，但可提前声明。

    # 10. 回退策略（fallback）
    fallback: Literal["none", "use_world_core", "empty_context"] = "none"
    # 说明：当 retrieve=True 但无结果时的行为。由 Assembler 执行，但由 Schema 声明。

    # 11. 决策理由（reasons）
    reasons: dict[str, Any] = field(default_factory=dict)
    # 说明：调试/日志用。例如 {"low_signal": True, "intent_unclear": True}。
    # 不参与执行逻辑，仅用于可观测性。@dataclass