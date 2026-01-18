# SignalDensityJudge.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Literal, Optional

from DataClass.ChatMessage import ChatMessage
from QuerySystem.SignalDensity.PrototypeCosineRouter import PrototypeCosineRouter, CosineRouteResult
from QuerySystem.QueryPropertyBuilderAbstract import QueryPropertyBuilderAbstract
from DataClass.QuerySchema import SignalDensity


@dataclass(slots=True)
class DensityDecision:
    density: SignalDensity
    reasons: dict[str, Any]


class SignalDensityJudge():
    def __init__(
        self,
        *,
        cosine_router: PrototypeCosineRouter,
        low_len: int = 3,
        low_token_count: int = 3,
        high_cosine_threshold: float = 0.35,
        return_reasons: bool = False,
    ):
        self.router = cosine_router
        self.low_len = low_len
        self.low_token_count = low_token_count
        self.high_cosine_threshold = high_cosine_threshold
        self.return_reasons = return_reasons

    def buildProperty(self, msg: ChatMessage) -> List[tuple[str, Any, Any]] | List[tuple[str, Any]]:
        density_or_decision = self.judge(msg)
        if self.return_reasons:
            return [("signal_density", density_or_decision.density, density_or_decision.reasons)]
        else:
            return [("signal_density", density_or_decision.density)]
    
    def judge(self, msg: ChatMessage) -> DensityDecision:
        text = (msg.content or "").strip()
        ar = msg.analyze_result

        t = (ar.normalized_text.strip() if (ar and ar.normalized_text) else text).lower()
        token_count = len(ar.tokens) if (ar and ar.tokens) else 0

        has_keywords = bool(ar.keywords) if ar else False
        has_entities = bool(ar.entities) if ar else False
        has_frames = bool(ar.frames) if ar else False

        is_question = bool(ar.is_question) if (ar and ar.is_question is not None) else False
        is_self_reference = bool(ar.is_self_reference) if (ar and ar.is_self_reference is not None) else False

        # --- hard low gate: config/template_input.yaml ---
        low_pattern_hit = t in self.router.low_signal_patterns

        reasons: dict[str, Any] = {
            "text_len": len(t),
            "token_count": token_count,
            "has_keywords": has_keywords,
            "has_entities": has_entities,
            "has_frames": has_frames,
            "is_question": is_question,
            "is_self_reference": is_self_reference,
            "low_pattern_hit": low_pattern_hit,
        }

        if msg.role != "user":
            reasons["rule"] = "non_user_message"
            return self._ret("mid", reasons)

        if low_pattern_hit:
            reasons["rule"] = "low_signal_pattern"
            return self._ret("low", reasons)

        if (
            (len(t) <= self.low_len or token_count <= self.low_token_count)
            and not has_keywords and not has_entities and not has_frames
        ):
            reasons["rule"] = "short_or_few_tokens_and_no_struct_signals"
            return self._ret("low", reasons)

        # --- high by semantic prototype similarity (cosine) ---
        route: CosineRouteResult = self.router.route(msg)
        reasons["proto_best_label"] = route.best_label
        reasons["proto_best_score"] = route.best_score
        reasons["proto_scores"] = route.scores

        # 自指问句也直接 high（很常见是“你/系统”类）
        if is_question and is_self_reference:
            reasons["rule"] = "self_reference_question"
            return self._ret("high", reasons)

        if route.best_score >= self.high_cosine_threshold:
            reasons["rule"] = "prototype_high"
            return self._ret("high", reasons)

        reasons["rule"] = "default_mid"
        return self._ret("mid", reasons)

    def _ret(self, density: SignalDensity, reasons: dict[str, Any]) ->  DensityDecision:

        return DensityDecision(density=density, reasons=reasons)

