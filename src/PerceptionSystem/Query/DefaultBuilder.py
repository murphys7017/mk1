# DefaultQuerySchemaBuilder.py
# A production-oriented QuerySchema builder that:
# - Pulls recent user messages directly from RawChatHistory
# - Uses low-signal gating to avoid noisy retrieval
# - Optionally uses an LLM "router" to decide intent/sources/specs (strict JSON)
# - Falls back to a deterministic rule-based plan if LLM fails
#
# Assumptions about your project:
# - RawChatHistory.getHistory(n) returns a list of ChatMessage (oldest->newest or newest->oldest doesn't matter;
#   we re-filter by role and take last N user msgs)
# - ChatMessage has fields: role, content, analyze_result, chat_turn_id (optional), timestamp/timedate (optional)
# - AnalyzeResult has: normalized_text, tokens, keywords, entities, frames, is_question, is_self_reference, emotion_cues
# - LLMManagement-like object provides: generate(prompt_name=..., options=..., **kwargs) -> dict or str (JSON)
#
# You can wire this builder into your pipeline right after PerceptionSystem stores analyze_result in ChatMessage.

from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple, Literal

from DataClass.QuerySchema import (
    QuerySchema,
    SourcePlan,
    QuerySpec,
    InjectionPlan,
    FallbackStep,
    SourceName,
    QueryMode,
    IntentName,
    SignalDensity,
)
from DataClass.AnalyzeResult import AnalyzeResult
from DataClass.ChatMessage import ChatMessage
from RawChatHistory.RawChatHistory import RawChatHistory


# -----------------------------
# Utilities
# -----------------------------

_LOW_SIGNAL_DEFAULT_PATTERNS = {
    "在吗", "在不在", "?", "？", "嗯", "哦", "好", "好的", "ok", "okay", "hello", "hi", "test", "测试"
}

_ENV_MARKERS = (
    "cpu", "内存", "memory", "mem", "磁盘", "disk", "天气", "weather", "新闻", "news",
    "现在", "当前", "多少", "占用", "负载", "温度", "ip", "端口", "进程", "运行", "uptime",
)

_WORLD_BG_MARKERS = (
    "架构", "流程", "模块", "设计", "系统", "prompt", "memory", "事件", "eventbus",
    "sqlite", "数据库", "summary", "摘要", "assembler", "executor", "schema", "queryplan"
)

_KB_MARKERS = (
    "文档", "readme", "接口", "api", "参数", "用法", "说明", "引用", "资料", "手册", "规范"
)

_USER_MEM_MARKERS = (
    "我是谁", "记住我", "我的偏好", "我喜欢", "我不喜欢", "我的习惯", "我的项目", "我的目标"
)


def _safe_json_loads(s: str) -> Optional[dict]:
    s = s.strip()
    if not s:
        return None
    # Try direct
    try:
        return json.loads(s)
    except Exception:
        pass

    # Try extracting JSON object substring
    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _clamp_int(x: Any, lo: int, hi: int, default: int) -> int:
    try:
        v = int(x)
        return max(lo, min(hi, v))
    except Exception:
        return default


def _uniq_keep_order(xs: Sequence[str]) -> List[str]:
    seen = set()
    out = []
    for x in xs:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


# -----------------------------
# Builder
# -----------------------------

class DefaultQuerySchemaBuilder:
    """
    Build QuerySchema by reading recent user messages from raw history,
    optionally using an LLM router, with safe deterministic fallback.

    Recommended usage:
        builder = DefaultQuerySchemaBuilder(raw_history, llm_management=..., ...)
        schema = builder.build()
        # pass schema to QueryExecutor
    """

    def __init__(
        self,
        raw_history: RawChatHistory,
        *,
        llm_management: Optional[Any] = None,
        llm_prompt_name: str = "query_router",
        llm_temperature: float = 0.0,
        analysis_window: int = 3,
        low_signal_patterns: Optional[set[str]] = None,
        enable_llm_router: bool = True,
    ):
        self.raw_history = raw_history
        self.llm_management = llm_management
        self.llm_prompt_name = llm_prompt_name
        self.llm_temperature = llm_temperature
        self.analysis_window = max(1, analysis_window)
        self.low_signal_patterns = low_signal_patterns or set(_LOW_SIGNAL_DEFAULT_PATTERNS)
        self.enable_llm_router = enable_llm_router

    # -------- public API --------

    def build(self) -> QuerySchema:
        """
        Reads recent user inputs from raw_history, builds QuerySchema.

        Flow:
          1) gather signals from last N user messages (AnalyzeResult + text)
          2) low-signal gating -> retrieve=False
          3) otherwise: try LLM router -> strict JSON -> schema
          4) fallback to rules
          5) schema.validate()
        """
        user_msgs = self._get_recent_user_messages(self.analysis_window)
        analyze, merged_text = self._merge_signals(user_msgs)

        # Step A: density + hard gating
        density = self._assess_signal_density(analyze, merged_text)
        intent_guess = self._infer_intent_rules(analyze, merged_text)

        # Base schema
        schema = QuerySchema(
            intent=intent_guess,
            signal_density=density,
            retrieve=(density != "low"),
            # must_include defaults to ["world_core"] in your QuerySchema dataclass
            routing_tags=self._routing_tags(intent_guess),
            debug_tags=self._debug_tags(analyze),
            injection=InjectionPlan(token_budget=self._budget_for_density(density)),
            reasons=self._reasons_base(analyze, merged_text, density, intent_guess),
        )

        # Low-signal: forbid retrieval
        if density == "low":
            schema.retrieve = False
            schema.source_plans = []
            schema.fallback = [FallbackStep(action="must_include_only", params={})]
            schema.validate()
            return schema

        # Step B: optional LLM routing
        if self.enable_llm_router and self.llm_management is not None:
            llm_schema = self._try_llm_route(analyze, merged_text, schema)
            if llm_schema is not None:
                llm_schema.validate()
                return llm_schema

        # Step C: deterministic fallback routing
        schema = self._apply_rule_based_source_plans(schema, analyze, merged_text)
        schema.validate()
        return schema

    # -------- signal gathering --------

    def _get_recent_user_messages(self, n: int) -> List[ChatMessage]:
        buf = self.raw_history.getHistory(max(20, n * 3))  # fetch a bit more, then filter
        user_msgs = [m for m in buf if getattr(m, "role", None) == "user"]
        return user_msgs[-n:] if user_msgs else []

    def _merge_signals(self, msgs: List[ChatMessage]) -> Tuple[AnalyzeResult, str]:
        """
        Merge: take the latest AnalyzeResult if present; also build a merged_text
        (best-effort) for LLM routing / keyword heuristics.

        If you later want a smarter merge, you can implement AnalyzeResult.merge_analyze_results here.
        """
        merged_text_parts: List[str] = []
        last_analyze: Optional[AnalyzeResult] = None

        for m in msgs:
            c = (getattr(m, "content", "") or "").strip()
            if c:
                merged_text_parts.append(c)
            anl = getattr(m, "analyze_result", None)
            if anl is not None:
                last_analyze = anl

        merged_text = "\n".join(merged_text_parts).strip()

        # If no analyze exists, build a minimal AnalyzeResult-like object (fallback fields)
        if last_analyze is None:
            # Create a minimal stub using your AnalyzeResult constructor signature if available.
            # If AnalyzeResult requires many args, adapt this part.
            last_analyze = AnalyzeResult(
                turn_id=None,
                timestamp=None,
                media_type="text",
                schema_version="analyze_v1",
                entities=[],
                frames=[],
                tokens=[],
                keywords=[],
                relations=[],
                normalized_text=merged_text,
                is_question=False,
                is_self_reference=False,
                emotion_cues=[],
                raw={},
            )

        # Ensure normalized_text exists
        if not getattr(last_analyze, "normalized_text", None):
            last_analyze.normalized_text = merged_text

        return last_analyze, merged_text

    # -------- routing: density, intent, tags --------

    def _assess_signal_density(self, analyze: AnalyzeResult, text: str) -> SignalDensity:
        t = (text or analyze.normalized_text or "").strip().lower()

        # hard low-signal patterns
        if t in self.low_signal_patterns:
            return "low"

        tok_n = len(getattr(analyze, "tokens", []) or [])
        has_keywords = bool(getattr(analyze, "keywords", []) or [])
        has_entities = bool(getattr(analyze, "entities", []) or [])
        has_frames = bool(getattr(analyze, "frames", []) or [])

        # low-signal gate: IMPORTANT: even if is_question=True, still low if no information
        if (len(t) <= 3 or tok_n <= 3) and (not has_keywords) and (not has_entities) and (not has_frames):
            return "low"

        # high: self-reference question or environment markers (time-sensitive)
        if bool(getattr(analyze, "is_self_reference", False)) and bool(getattr(analyze, "is_question", False)):
            return "high"

        if any(m in t for m in _ENV_MARKERS):
            return "high"

        return "mid"

    def _infer_intent_rules(self, analyze: AnalyzeResult, text: str) -> IntentName:
        t = (text or analyze.normalized_text or "").strip().lower()

        if t in self.low_signal_patterns:
            return "ping_presence"

        if any(m in t for m in _ENV_MARKERS):
            return "environment_status"

        if any(m in t for m in _WORLD_BG_MARKERS):
            return "world_background"

        if any(m in t for m in _KB_MARKERS):
            return "knowledge_lookup"

        if any(m in t for m in _USER_MEM_MARKERS):
            return "user_memory"

        if bool(getattr(analyze, "is_question", False)):
            return "clarify"

        return "general_conversation"

    def _routing_tags(self, intent: IntentName) -> List[str]:
        # keep small & stable
        m = {
            "world_background": ["topic:architecture"],
            "environment_status": ["topic:env"],
            "knowledge_lookup": ["topic:knowledge"],
            "user_memory": ["topic:user"],
            "ping_presence": ["topic:chat"],
            "clarify": ["topic:chat"],
            "general_conversation": ["topic:chat"],
            "unknown": ["topic:chat"],
        }
        return m.get(intent, ["topic:chat"])

    def _debug_tags(self, analyze: AnalyzeResult) -> List[str]:
        tags: List[str] = []
        # entities
        for e in (getattr(analyze, "entities", []) or [])[:10]:
            typ = getattr(e, "typ", None) or getattr(e, "type", None)
            if typ:
                tags.append(f"type:{str(typ).lower()}")
        # keywords
        for kw in (getattr(analyze, "keywords", []) or [])[:8]:
            if kw:
                tags.append(f"kw:{str(kw).lower()}")
        # emotions
        for cue in (getattr(analyze, "emotion_cues", []) or [])[:5]:
            if cue:
                tags.append(f"emotion:{str(cue).lower()}")
        return _uniq_keep_order(tags)

    def _budget_for_density(self, density: SignalDensity) -> int:
        if density == "high":
            return 768
        if density == "mid":
            return 512
        return 256

    def _reasons_base(self, analyze: AnalyzeResult, text: str, density: SignalDensity, intent: IntentName) -> Dict[str, Any]:
        t = (text or "").strip()
        return {
            "text_len": len(t),
            "token_count": len(getattr(analyze, "tokens", []) or []),
            "has_keywords": bool(getattr(analyze, "keywords", []) or []),
            "has_entities": bool(getattr(analyze, "entities", []) or []),
            "has_frames": bool(getattr(analyze, "frames", []) or []),
            "is_question": bool(getattr(analyze, "is_question", False)),
            "is_self_reference": bool(getattr(analyze, "is_self_reference", False)),
            "density": density,
            "intent_rules": intent,
        }

    # -------- LLM router --------

    def _try_llm_route(self, analyze: AnalyzeResult, text: str, base_schema: QuerySchema) -> Optional[QuerySchema]:
        """
        Ask an LLM to produce a strict JSON routing decision.
        If parsing/validation fails, return None (fall back to rules).
        """
        # Construct router input (keep concise)
        router_input = {
            "user_text": (text or analyze.normalized_text or "").strip(),
            "signals": {
                "normalized_text": getattr(analyze, "normalized_text", ""),
                "keywords": getattr(analyze, "keywords", []) or [],
                "entities": [
                    {"text": getattr(e, "text", None), "typ": getattr(e, "typ", None)}
                    for e in (getattr(analyze, "entities", []) or [])[:8]
                ],
                "is_question": bool(getattr(analyze, "is_question", False)),
                "is_self_reference": bool(getattr(analyze, "is_self_reference", False)),
                "emotion_cues": getattr(analyze, "emotion_cues", []) or [],
            },
            "constraints": {
                "allowed_intents": [
                    "ping_presence", "general_conversation", "clarify",
                    "world_background", "environment_status", "knowledge_lookup",
                    "user_memory", "unknown"
                ],
                "allowed_sources": ["short_term", "mid_term", "long_term", "user_profile", "world_bg", "env", "kb"],
                "allowed_modes": ["keyword", "vector", "hybrid", "llm"],
                "rules": [
                    "Return STRICT JSON only.",
                    "If low-signal (very short + no keywords/entities/frames), set retrieve=false and source_plans empty.",
                    "Do NOT include world_core as a source (it is always injected).",
                    "If using env source, ttl_seconds must be set (e.g. 120).",
                    "Prefer keyword mode for speed unless knowledge_lookup suggests hybrid.",
                    "Avoid user_profile unless intent is user_memory."
                ],
            },
            "base_guess": {
                "intent": base_schema.intent,
                "signal_density": base_schema.signal_density,
                "routing_tags": base_schema.routing_tags,
            }
        }

        prompt_payload = json.dumps(router_input, ensure_ascii=False)

        try:
            out = self.llm_management.generate(
                prompt_name=self.llm_prompt_name,
                options={"temperature": self.llm_temperature, "top_p": 1},
                router_input=prompt_payload,
            )
        except Exception:
            return None

        # out may be dict or string
        if isinstance(out, dict):
            data = out
        else:
            data = _safe_json_loads(str(out))
        if not data or not isinstance(data, dict):
            return None

        # Expected JSON shape:
        # {
        #   "intent": "...",
        #   "signal_density": "low|mid|high",
        #   "retrieve": true/false,
        #   "routing_tags": ["topic:..."],
        #   "source_plans": [
        #       {"name":"mid_term","ttl_seconds":null,"specs":[{"q":"...","mode":"keyword","tags":[...],"filters":{},"top_k":4,"min_score":null,"rerank":false}]},
        #       ...
        #   ],
        #   "token_budget": 512,
        #   "reasons": {...}
        # }

        intent: IntentName = data.get("intent", base_schema.intent)
        density: SignalDensity = data.get("signal_density", base_schema.signal_density)
        retrieve: bool = bool(data.get("retrieve", base_schema.retrieve))
        routing_tags = data.get("routing_tags", base_schema.routing_tags) or base_schema.routing_tags
        token_budget = _clamp_int(data.get("token_budget", base_schema.injection.token_budget), 128, 2048, base_schema.injection.token_budget)

        # If low-signal, force retrieve off
        if density == "low":
            retrieve = False

        source_plans: List[SourcePlan] = []
        if retrieve:
            raw_sps = data.get("source_plans", [])
            if not isinstance(raw_sps, list):
                raw_sps = []
            for sp in raw_sps:
                if not isinstance(sp, dict):
                    continue
                name = sp.get("name")
                if name not in ("short_term", "mid_term", "long_term", "user_profile", "world_bg", "env", "kb"):
                    continue
                ttl_seconds = sp.get("ttl_seconds", None)
                if name == "env":
                    ttl_seconds = _clamp_int(ttl_seconds, 30, 3600, 120)
                specs: List[QuerySpec] = []
                for spec in (sp.get("specs") or []):
                    if not isinstance(spec, dict):
                        continue
                    mode = spec.get("mode", "keyword")
                    if mode not in ("keyword", "vector", "hybrid", "llm"):
                        mode = "keyword"
                    q = str(spec.get("q", "") or "")
                    tags = spec.get("tags", []) or []
                    if not isinstance(tags, list):
                        tags = []
                    filters = spec.get("filters", {}) or {}
                    if not isinstance(filters, dict):
                        filters = {}
                    top_k = _clamp_int(spec.get("top_k", 5), 0, 50, 5)
                    min_score = spec.get("min_score", None)
                    rerank = bool(spec.get("rerank", False))
                    specs.append(QuerySpec(q=q, mode=mode, tags=tags, filters=filters, top_k=top_k, min_score=min_score, rerank=rerank))
                source_plans.append(SourcePlan(name=name, enabled=True, specs=specs, ttl_seconds=ttl_seconds))

        # Guardrail: avoid user_profile unless user_memory
        if intent != "user_memory":
            source_plans = [sp for sp in source_plans if sp.name != "user_profile"]

        schema = QuerySchema(
            intent=intent,
            signal_density=density,
            retrieve=retrieve,
            must_include=["world_core"],
            routing_tags=routing_tags,
            debug_tags=base_schema.debug_tags,
            source_plans=source_plans if retrieve else [],
            injection=InjectionPlan(token_budget=token_budget),
            fallback=[
                FallbackStep(action="reduce_topk", params={"factor": 0.5}),
                FallbackStep(action="switch_mode", params={"from": "hybrid", "to": "keyword"}),
                FallbackStep(action="must_include_only", params={}),
            ],
            reasons={
                **(base_schema.reasons or {}),
                "llm_router": True,
                "llm_raw": data.get("reasons", data),
            },
        )

        # ensure consistency
        try:
            schema.validate()
        except Exception:
            return None

        return schema

    # -------- rule-based source plans --------

    def _apply_rule_based_source_plans(self, schema: QuerySchema, analyze: AnalyzeResult, text: str) -> QuerySchema:
        intent = schema.intent
        q = self._build_query_text(analyze, text)

        sps: List[SourcePlan] = []

        if intent == "world_background":
            sps.append(self._plan("world_bg", q, schema.routing_tags, mode="keyword", top_k=8))
            sps.append(self._plan("mid_term", q, schema.routing_tags, mode="keyword", top_k=4))

        elif intent == "environment_status":
            sp = self._plan("env", "", ["topic:env"], mode="keyword", top_k=1)
            sp.ttl_seconds = 120
            sps.append(sp)

        elif intent == "knowledge_lookup":
            # hybrid: keyword coarse + vector rerank (executor can implement as two-stage)
            sps.append(self._plan("kb", q, ["topic:knowledge"], mode="hybrid", top_k=12, rerank=True))

        elif intent == "user_memory":
            sps.append(self._plan("user_profile", q, ["topic:user"], mode="keyword", top_k=6))
            sps.append(self._plan("mid_term", q, ["topic:user"], mode="keyword", top_k=4))

        else:
            # default conversation: short + mid, no user_profile
            sps.append(self._plan("short_term", q, schema.routing_tags, mode="keyword", top_k=6))
            sps.append(self._plan("mid_term", q, schema.routing_tags, mode="keyword", top_k=4))

        schema.source_plans = sps
        schema.retrieve = True
        schema.fallback = [
            FallbackStep(action="reduce_topk", params={"factor": 0.5}),
            FallbackStep(action="switch_mode", params={"from": "hybrid", "to": "keyword"}),
            FallbackStep(action="must_include_only", params={}),
        ]
        schema.reasons = {
            **(schema.reasons or {}),
            "llm_router": False,
            "query_text": q,
            "source_plan_names": [sp.name for sp in sps],
        }
        return schema

    def _build_query_text(self, analyze: AnalyzeResult, text: str) -> str:
        t = (text or analyze.normalized_text or "").strip()
        if t:
            return t
        parts = []
        for kw in (getattr(analyze, "keywords", []) or [])[:8]:
            parts.append(str(kw))
        for e in (getattr(analyze, "entities", []) or [])[:5]:
            et = getattr(e, "text", None)
            if et:
                parts.append(str(et))
        return " ".join(parts).strip()

    def _plan(
        self,
        name: SourceName,
        q: str,
        routing_tags: List[str],
        *,
        mode: QueryMode,
        top_k: int,
        rerank: bool = False,
    ) -> SourcePlan:
        spec = QuerySpec(
            q=q,
            mode=mode,
            tags=routing_tags,
            filters={},
            top_k=top_k,
            rerank=rerank,
        )
        return SourcePlan(name=name, enabled=True, specs=[spec], ttl_seconds=None)
