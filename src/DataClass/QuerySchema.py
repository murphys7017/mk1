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


QueryMode = Literal[
    "keyword",  # SQLite FTS5 / BM25 / 关键词
    "vector",   # HNSW / Faiss / embedding
    "hybrid",   # keyword 粗筛 + vector rerank
    "llm",      # 用 LLM 做 rewrite 或直接路由（不建议当唯一检索）
]


@dataclass(slots=True)
class Filters:
    """
    结构化过滤条件
    先暂时使用dict结构体，后续根据实际使用情况，构建一个 关键词 关系（= > < != IN） 值 以及node子节点 和 与其他同级关系 的过滤类，类似简单orm，不过是针对非结构化文本的。
    """
    keyword: Optional[str] = None

@dataclass
class QuerySchema:

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
    # 查询基于的文本 某条对话或者摘要
    query_text: str = ""
    # 查询的方式 关键词 向量 混合
    mode: QueryMode = "keyword"
    # 关键词列表
    keywords: List[str] = field(default_factory=list)

    # 结构化过滤条件
    filters: Dict[str, Any] = field(default_factory=dict)
    top_k: int = 5
    min_score: Optional[float] = None
    rerank: bool = False


    # 1) routing
    intent: IntentName = "unknown"
    signal_density: SignalDensity = "low"
    retrieve: bool = False




    # tags 分两类：routing_tags 用于检索过滤；debug_tags 仅用于观测
    routing_tags: List[str] = field(default_factory=list)
    debug_tags: List[str] = field(default_factory=list)





    reasons: Dict[str, Any] = field(default_factory=dict)

