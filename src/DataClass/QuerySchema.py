from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple


# -----------------------------
# Enums / Literals
# -----------------------------

SignalDensity = Literal["low", "mid", "high"]

IntentName = Literal[
    "ping_presence",         # 在吗/？/hello
    "general_conversation",  # 普通闲聊延续
    "clarify",               # 澄清/追问
    "world_background",      # 问系统/项目设定、架构、规则
    "environment_status",    # 主机状态/天气/新闻等动态信息
    "knowledge_lookup",      # 查知识库/文档
    "user_memory",           # 回忆用户信息/偏好
    "unknown",
]

SourceName = Literal[
    "short_term",    # recent raw messages
    "mid_term",      # dialogue summaries
    "long_term",     # long memory items
    "user_profile",  # user facts/preferences
    "world_bg",      # world background items (contextual)
    "env",           # environment snapshot (TTL required)
    "kb",            # knowledge base / documents
]

MustIncludeName = Literal[
    "world_core",    # 永远注入：世界核心规则
]

QueryMode = Literal[
    "keyword",  # SQLite FTS5 / BM25 / 关键词
    "vector",   # HNSW / Faiss / embedding
    "hybrid",   # keyword 粗筛 + vector rerank
    "llm",      # 用 LLM 做 rewrite 或直接路由（不建议当唯一检索）
]


# -----------------------------
# QuerySpec / SourcePlan
# -----------------------------

@dataclass(slots=True)
class QuerySpec:
    """
    一条“检索指令”：
    - q: 查询文本（允许为空；例如 env 只拉最新快照）
    - mode: keyword/vector/hybrid/llm
    - tags: 主题过滤（routing tags）
    - filters: 结构化过滤（时间范围、turn_id、recency 等）
    - top_k: 本条指令的候选数量
    - min_score: 向量检索阈值（可选）
    - rerank: 是否进行二次排序（hybrid 常用）
    """
    q: str = ""
    mode: QueryMode = "keyword"
    tags: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    top_k: int = 5
    min_score: Optional[float] = None
    rerank: bool = False


@dataclass(slots=True)
class SourcePlan:
    """
    一个 source 的检索计划：可以包含多条 QuerySpec
    - name: source 名称
    - enabled: 是否启用
    - specs: 多条检索指令（通常 1 条就够；复杂场景可多条合并）
    - weight: 可选，用于跨 source 合并时的优先级
    - ttl_seconds: 针对 env/web 这类动态源的过期要求（env 必填）
    """
    name: SourceName
    enabled: bool = True
    specs: List[QuerySpec] = field(default_factory=list)
    weight: float = 1.0
    ttl_seconds: Optional[int] = None


# -----------------------------
# Injection / Fallback
# -----------------------------

@dataclass(slots=True)
class InjectionPlan:
    """
    控制“怎么注入 prompt”：
    - token_budget: 总预算（所有检索块加起来）
    - max_items_per_source: 每个 source 最多注入几条（默认由 executor/assembler 兜底）
    - format: 注入格式（block/bullets/compact 等）
    - include_diagnostics: 是否把“命中理由/分数”以 debug 形式注入（建议默认 False）
    """
    token_budget: int = 512
    max_items_per_source: Dict[SourceName, int] = field(default_factory=dict)
    format: Literal["block", "bullets", "compact"] = "block"
    include_diagnostics: bool = False


@dataclass(slots=True)
class FallbackStep:
    """
    回退步骤：按顺序执行，直到成功或用尽。
    action:
      - "disable_source": 禁用某 source
      - "reduce_topk": 降低 top_k（每条 spec）
      - "switch_mode": 切换 mode（hybrid->keyword / vector->keyword）
      - "must_include_only": 只注入 must_include（通常 world_core only）
    params: 动作参数
    """
    action: Literal["disable_source", "reduce_topk", "switch_mode", "must_include_only"]
    params: Dict[str, Any] = field(default_factory=dict)


# -----------------------------
# QuerySchema
# -----------------------------

@dataclass(slots=True)
class QuerySchema:
    # 1) routing
    intent: IntentName = "unknown"
    signal_density: SignalDensity = "low"
    retrieve: bool = False

    # 2) always include
    must_include: List[MustIncludeName] = field(default_factory=lambda: ["world_core"])

    # 3) retrieval plan
    source_plans: List[SourcePlan] = field(default_factory=list)

    # tags 分两类：routing_tags 用于检索过滤；debug_tags 仅用于观测
    routing_tags: List[str] = field(default_factory=list)
    debug_tags: List[str] = field(default_factory=list)

    # 4) injection
    injection: InjectionPlan = field(default_factory=InjectionPlan)

    # 5) fallback + observability
    fallback: List[FallbackStep] = field(default_factory=lambda: [
        FallbackStep(action="reduce_topk", params={"factor": 0.5}),
        FallbackStep(action="must_include_only", params={}),
    ])
    reasons: Dict[str, Any] = field(default_factory=dict)

    # -------------------------
    # invariants
    # -------------------------
    def validate(self) -> None:
        if self.signal_density not in ("low", "mid", "high"):
            raise ValueError(f"invalid signal_density={self.signal_density}")

        if not self.retrieve:
            # retrieve=False 时，必须禁用所有 source
            if any(sp.enabled for sp in self.source_plans):
                raise ValueError("retrieve=False but source_plans contains enabled sources")

        # env 源要求 ttl
        for sp in self.source_plans:
            if not sp.enabled:
                continue
            if sp.name == "env" and sp.ttl_seconds is None:
                raise ValueError("env source requires ttl_seconds")
            for spec in sp.specs:
                if spec.top_k < 0:
                    raise ValueError("QuerySpec.top_k must be >= 0")
