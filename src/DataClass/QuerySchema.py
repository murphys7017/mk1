"""
QuerySchema: 强 schema 的“检索/注入计划书”。

职责边界：
- QuerySchema 只描述“要不要检索、检索哪些源、用什么条件、注入预算与回退”。
- 不做任何实际检索、不拼 prompt、不访问数据库。

设计要点：
- must_include 用于“永远注入”的块（如 world_core），避免把它当成可检索 source。
- retrieve 是硬闸门：Executor 必须以它为准，retrieve=False 时禁止任何查询。
- sources/tags/query/top_k/ttl/token_budget 是执行参数。
- reasons 用于可解释性与调试，绝不参与执行逻辑。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Literal


# ---------- enums / literals ----------

SignalDensity = Literal["low", "mid", "high"]

# 注意：source 表示“需要检索的数据源”，不是“固定注入的设定块”
SourceName = Literal[
    "short_term",    # recent raw messages
    "mid_term",      # dialogue summaries
    "long_term",     # long memory items
    "user_profile",  # user facts/preferences
    "world_bg",      # world background items (contextual)
    "env",           # environment snapshot (ttl required)
    "kb",            # knowledge base / documents
    "web",           # external web/news (if allowed)
]

MustIncludeName = Literal[
    "world_core",    # always injected, not retrieved
]

IntentName = Literal[
    "ping_presence",         # 在吗/hello/?
    "general_conversation",  # 普通闲聊延续
    "clarify",               # 澄清/追问
    "world_background",      # 问系统/项目设定、架构、规则
    "environment_status",    # 主机状态/天气/新闻等动态信息
    "knowledge_lookup",      # 查知识库/文档
    "user_memory",           # 回忆用户信息/偏好
    "unknown",
]


class FallbackPolicy(str, Enum):
    """
    当 retrieve=True 但检索结果为空 / 执行失败时，Assembler/Executor 应采取的策略。
    """
    USE_MUST_INCLUDE_ONLY = "use_must_include_only"  # 只注入 must_include（通常等价于 world_core only）
    EMPTY_CONTEXT = "empty_context"                  # 不注入任何检索块（仍然可以有 system/core）
    RELAX_FILTERS = "relax_filters"                  # 放宽过滤（例如扩大 top_k / 降低 min_score），由 Executor 决定怎么做
    NONE = "none"


# ---------- schema ----------

@dataclass(slots=True)
class QuerySchema:
    # (1) routing
    intent: IntentName = "unknown"
    signal_density: SignalDensity = "low"
    retrieve: bool = False

    # (2) fixed injection
    must_include: List[MustIncludeName] = field(default_factory=lambda: ["world_core"])

    # (3) retrieval authorization
    sources: List[SourceName] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    query: Optional[str] = None
    top_k: int = 3

    # (4) freshness / budget
    ttl_seconds: Optional[int] = None          # env/web 之类强烈建议有
    token_budget: Optional[int] = None         # 注入总预算（给 Assembler 做截断）
    max_items_per_source: Dict[str, int] = field(default_factory=dict)

    # (5) fallback & observability
    fallback: FallbackPolicy = FallbackPolicy.USE_MUST_INCLUDE_ONLY
    reasons: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """
        运行时自检（可选，但强烈推荐在 builder 末尾调用一次）。
        发现不一致就抛错，避免“静默乱注入”。
        """
        if self.signal_density not in ("low", "mid", "high"):
            raise ValueError(f"invalid signal_density={self.signal_density}")

        if self.top_k < 0:
            raise ValueError("top_k must be >= 0")

        # retrieve 是硬闸门：retrieve=False 时必须没有 sources
        if not self.retrieve and self.sources:
            raise ValueError("retrieve=False but sources is not empty")

        # env/web 一般需要 ttl（你也可以按需放宽）
        if self.retrieve and any(s in ("env", "web") for s in self.sources):
            if self.ttl_seconds is None:
                raise ValueError("env/web sources require ttl_seconds")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "signal_density": self.signal_density,
            "retrieve": self.retrieve,
            "must_include": list(self.must_include),
            "sources": list(self.sources),
            "tags": list(self.tags),
            "query": self.query,
            "top_k": self.top_k,
            "ttl_seconds": self.ttl_seconds,
            "token_budget": self.token_budget,
            "max_items_per_source": dict(self.max_items_per_source),
            "fallback": self.fallback.value if isinstance(self.fallback, FallbackPolicy) else self.fallback,
            "reasons": dict(self.reasons),
        }
