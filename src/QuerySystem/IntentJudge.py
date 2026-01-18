from __future__ import annotations

from typing import Any, Dict, List
import json
import os

import yaml

from DataClass.ChatMessage import ChatMessage
from QuerySystem.QueryPropertyBuilderAbstract import QueryPropertyBuilderAbstract  # :contentReference[oaicite:1]{index=1}
from LLM.LLMManagement import LLMManagement


_ALLOWED_SOURCES = ["short_term", "mid_term", "long_term", "user_profile", "world_bg", "env", "kb"]


def _clamp_int(x: Any, lo: int, hi: int, default: int) -> int:
    try:
        v = int(x)
    except Exception:
        return default
    return max(lo, min(hi, v))


class IntentJudgeL(QueryPropertyBuilderAbstract):
    """
    YAML 驱动意图分类：
    - allowed_intents = template_input.yaml intents[].name
    - 每个 intent 必有 limits（top_k/token_budget）
    - LLM 只负责从 candidates 中选一个 intent name
    - 系统侧用 YAML 映射 retrieve/sources/limits

    依赖：
      - SystemPrompt 注册 prompt "intent_classifier"（严格 JSON）
      - LLMManagement 映射 "intent_classifier" -> 小模型
    """

    def __init__(
        self,        
        **kwargs
    ):
    
        self.llm = kwargs.get("llm_management", None)
        self.template_path = kwargs.get("template_path", "config/template_input.yaml")
        self.return_reasons = kwargs.get("return_reasons", False)

        self.max_keywords_per_intent = kwargs.get("max_keywords_per_intent", 24)
        self.max_examples_per_intent = kwargs.get("max_examples_per_intent", 6)
        self.min_confidence = float(kwargs.get("min_confidence", 0.35))

        self.top_k_lo, self.top_k_hi = kwargs.get("top_k_range", (1, 50))
        self.tb_lo, self.tb_hi = kwargs.get("token_budget_range", (64, 8192))

        self._cfg = self._load_yaml(self.template_path)
        self._intents_cfg: List[Dict[str, Any]] = list(self._cfg.get("intents", []) or [])
        self._enabled_intents_cfg = [it for it in self._intents_cfg if it.get("enabled", True)]

        # name -> cfg
        self._intent_map: Dict[str, Dict[str, Any]] = {}
        for it in self._enabled_intents_cfg:
            name = str(it.get("name", "")).strip()
            if not name:
                continue
            self._intent_map[name] = it

        self.allowed_intents = list(self._intent_map.keys())

        # 强约束：unknown 必须在 YAML（否则你后续兜底会很尴尬）
        if "unknown" not in self.allowed_intents:
            raise ValueError("template_input.yaml must include an intent named 'unknown'")

        # 强约束：每个 intent 必有 limits
        for name, it in self._intent_map.items():
            if not isinstance(it.get("limits"), dict):
                raise ValueError(f"intent '{name}' must have limits: {{top_k, token_budget}}")
    def getPriority(self) -> int:
        return 2
    def buildProperty(self, msg: ChatMessage) -> List[tuple[str, Any, Any]] | List[tuple[str, Any]]:
        ar = getattr(msg, "analyze_result", None)

        text = ""
        if ar is not None and getattr(ar, "normalized_text", None):
            text = ar.normalized_text or ""
        else:
            text = getattr(msg, "content", "") or ""

        # candidates：只给 LLM 必需字段
        candidates = []
        for it in self._enabled_intents_cfg:
            name = str(it.get("name", "")).strip()
            if not name:
                continue
            kws = [str(k).strip() for k in (it.get("keywords") or []) if str(k).strip()]
            exs = [str(e).strip() for e in (it.get("examples") or []) if str(e).strip()]
            pr = it.get("priority", 0)

            candidates.append(
                {
                    "name": name,
                    "priority": pr,
                    "keywords": kws[: self.max_keywords_per_intent],
                    "examples": exs[: self.max_examples_per_intent],
                }
            )

        router_input_obj = {
            "text": text,
            "allowed_intents": self.allowed_intents,
            "intents": candidates,
        }
        router_input = json.dumps(router_input_obj, ensure_ascii=False)
        if self.llm is None:
            return [
                ("retrieve", False),
                ("intent", "unknown"),
                ("sources", []),
                ("top_k", 5),
                ("token_budget", 512),
            ]
        out = self.llm.generate("intent_classifier", router_input=router_input)

        chosen_intent, confidence = self._parse_output(out)

        # 低置信兜底：直接 unknown（unknown 在 YAML 里，参数齐全）
        if chosen_intent != "unknown" and confidence < self.min_confidence:
            chosen_intent = "unknown"

        bundle = self._map_from_yaml(chosen_intent)




        return [
                ("retrieve", bundle["retrieve"]),
                ("intent", bundle["intent"]),
                ("sources", bundle["sources"]),
                ("top_k", bundle["top_k"]),
                ("token_budget", bundle["token_budget"]),
            ]

    # -----------------------------
    # Internal
    # -----------------------------
    def _load_yaml(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"template_input.yaml not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _parse_output(self, out: Any) -> tuple[str, float]:
        """
        Expect:
          {"intent": str, "confidence": float}
        """


        if not isinstance(out, dict):
            return "unknown", 0.0

        intent = str(out.get("intent", "unknown")).strip() or "unknown"
        try:
            confidence = float(out.get("confidence", 0.0))
        except Exception:
            confidence = 0.0

        # clamp confidence
        if confidence < 0.0:
            confidence = 0.0
        if confidence > 1.0:
            confidence = 1.0

        # whitelist by YAML
        if intent not in self.allowed_intents:
            intent = "unknown"

        return intent, confidence

    def _map_from_yaml(self, intent: str) -> Dict[str, Any]:
        it = self._intent_map[intent]  # intent 一定存在（unknown 兜底）
        limits = it["limits"]          # 已校验必有

        retrieve = bool(it.get("retrieve", True))
        sources = list(it.get("sources") or [])
        sources = [s for s in sources if s in _ALLOWED_SOURCES]

        top_k = _clamp_int(limits.get("top_k"), self.top_k_lo, self.top_k_hi, int(limits.get("top_k")))
        token_budget = _clamp_int(limits.get("token_budget"), self.tb_lo, self.tb_hi, int(limits.get("token_budget")))

        # 若 retrieve=false，强制 sources 为空
        if not retrieve:
            sources = []

        return {
                "retrieve": retrieve,
                "intent": intent,
                "sources": sources,
                "top_k": top_k,
                "token_budget": token_budget
            }
    
