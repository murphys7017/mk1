from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
import math

from DataClass.ChatMessage import ChatMessage  # :contentReference[oaicite:3]{index=3}
from DataClass.AnalyzeResult import AnalyzeResult
from QuerySystem.QueryPropertyBuilderAbstract import QueryPropertyBuilderAbstract  # :contentReference[oaicite:4]{index=4}


# -----------------------------
# 可解释原因结构（建议保留，方便调参/打日志）
# -----------------------------
@dataclass
class DensityReason:
    key: str
    contribution: float          # 该项对 raw 的贡献（已乘权重/含加减）
    detail: Dict[str, Any]


@dataclass
class DensityDecision:
    density: float               # 0~1
    raw: float                   # 映射前 raw
    reasons: List[DensityReason]


# -----------------------------
# 工具函数
# -----------------------------
def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))

def _saturate(x: float) -> float:
    return _clip(x, 0.0, 1.0)

def _sigmoid01(x: float, center: float, scale: float) -> float:
    # scale 越小越陡，建议 0.10~0.18
    z = (x - center) / max(scale, 1e-6)
    return 1.0 / (1.0 + math.exp(-z))


# -----------------------------
# SignalDensityJudge：QueryPropertyBuilderAbstract 实现
# -----------------------------
class SignalDensityJudge(QueryPropertyBuilderAbstract):
    """
    从 AnalyzeResult 的结构信号判断“信息密度”：
    - 强信号：entities / frames / relations
    - 中信号：keywords / tokens / normalized_text
    - 语用修正：is_question / is_self_reference / emotion_cues

    返回：
      ("signal_density", density, reasons) 或 ("signal_density", density)
    """

    def __init__(
        self,
        **kwargs
    ):
        self.return_reasons = kwargs.get("return_reasons", False)
        self.use_sigmoid = kwargs.get("use_sigmoid", True)
        self.sigmoid_center = kwargs.get("sigmoid_center", 0.45)
        self.sigmoid_scale = kwargs.get("sigmoid_scale", 0.12)

        self.w_entities = kwargs.get("w_entities", 0.22)
        self.w_frames = kwargs.get("w_frames", 0.18)
        self.w_relations = kwargs.get("w_relations", 0.20)
        self.w_tokens = kwargs.get("w_tokens", 0.10)
        self.w_keywords = kwargs.get("w_keywords", 0.15)
        self.w_norm = kwargs.get("w_norm", 0.15)

    def getPriority(self) -> int:
        return 1
    # QueryPropertyBuilderAbstract 要求的主入口 :contentReference[oaicite:5]{index=5}
    def buildProperty(self, msg: ChatMessage) -> List[tuple[str, Any, Any]] | List[tuple[str, Any]]:
        ar = msg.analyze_result  # ChatMessage.analyze_result :contentReference[oaicite:6]{index=6}

        # 没有 analyze_result：按“低密度”处理，理由写清楚（避免后续流程误判）
        if ar is None:
            if self.return_reasons:
                reasons = [DensityReason("missing_analyze_result", 0.0, {"note": "msg.analyze_result is None"})]
                return [("signal_density", 0.0, reasons)]
            return [("signal_density", 0.0)]

        decision = self._judge_analyze_result(ar, raw_text=msg.content)

        if self.return_reasons:
            return [("signal_density", decision.density, decision.reasons)]
        else:
            return [("signal_density", decision.density)]

    # -----------------------------
    # 核心逻辑：基于 AnalyzeResult 的评分
    # -----------------------------
    def _judge_analyze_result(self, ar: AnalyzeResult, *, raw_text: str) -> DensityDecision:
        reasons: List[DensityReason] = []

        # ========= 1) Entities =========
        # AnalyzeResult.entities 是 List[Entity] :contentReference[oaicite:7]{index=7}
        entities = list(ar.entities or [])
        # 轻量去重：text+typ（span 若你要更严谨，可用 AnalyzeResult._entity_key :contentReference[oaicite:8]{index=8}）
        uniq_ent = {((getattr(e, "text", None) or "").strip(), (getattr(e, "typ", None) or "").strip()) for e in entities}
        uniq_ent = {x for x in uniq_ent if x[0]}  # text 为空的丢掉
        n_ent = len(uniq_ent)

        ent_types = {t for _, t in uniq_ent if t}
        n_types = len(ent_types)
        # 这里不强依赖你的 typ 枚举，先用字符串启发；后面你可以把 TIME/LOC 的 type 统一后再精确匹配
        has_time_loc = any(t.lower() in {"time", "date", "loc", "location", "geo"} for t in ent_types)

        ent_score = _clip(_saturate(n_ent / 6.0) + 0.1 * _saturate(n_types / 4.0) + (0.1 if has_time_loc else 0.0))
        ent_contrib = self.w_entities * ent_score
        reasons.append(DensityReason(
            "entities",
            ent_contrib,
            {"n_unique": n_ent, "n_types": n_types, "has_time_or_location": has_time_loc, "score": ent_score, "weight": self.w_entities},
        ))

        # ========= 2) Frames =========
        # AnalyzeResult.frames 是 List[Frame] :contentReference[oaicite:9]{index=9}
        frames = list(ar.frames or [])
        n_frames = len(frames)

        # 如果你的 Frame 里暂时没 confidence，就按“有就加分、越多越饱和”。
        # 后续你若在 raw["ltp"] 或别处补 confidence，再把 avg_conf 接上即可。
        frames_score = _clip(0.6 * _saturate(n_frames / 2.0) + 0.4 * 0.6)  # 0.6 作为“默认中等可信”
        frames_contrib = self.w_frames * frames_score
        reasons.append(DensityReason(
            "frames",
            frames_contrib,
            {"n_frames": n_frames, "score": frames_score, "weight": self.w_frames, "note": "confidence not provided -> default used"},
        ))

        # ========= 3) Relations =========
        # AnalyzeResult.relations 是 List[Relation] :contentReference[oaicite:10]{index=10}
        relations = list(ar.relations or [])
        n_rel = len(relations)
        # relation 类型（Relation.relation 字段） :contentReference[oaicite:11]{index=11}
        rel_types = {(getattr(r, "relation", None) or "").strip() for r in relations}
        rel_types = {x for x in rel_types if x}
        n_rel_types = len(rel_types)

        rel_score = _clip(_saturate(n_rel / 4.0) + 0.1 * _saturate(n_rel_types / 3.0))
        rel_contrib = self.w_relations * rel_score
        reasons.append(DensityReason(
            "relations",
            rel_contrib,
            {"n_relations": n_rel, "n_relation_types": n_rel_types, "score": rel_score, "weight": self.w_relations},
        ))

        # ========= 4) Tokens =========
        # AnalyzeResult.tokens: List[Tuple[str,str]] :contentReference[oaicite:12]{index=12}
        tokens = list(ar.tokens or [])
        n_tokens = len(tokens)
        token_score = _saturate(n_tokens / 120.0)
        token_contrib = self.w_tokens * token_score
        reasons.append(DensityReason(
            "tokens",
            token_contrib,
            {"n_tokens": n_tokens, "score": token_score, "weight": self.w_tokens},
        ))

        # ========= 5) Keywords =========
        # AnalyzeResult.keywords :contentReference[oaicite:13]{index=13}
        keywords = list(ar.keywords or [])
        uniq_kw = {k.strip() for k in keywords if (k or "").strip()}
        n_kw = len(uniq_kw)

        # 简化版：只看数量饱和。你后面可以把“领域词 / 泛化词”区分后再加惩罚项
        kw_score = _saturate(n_kw / 10.0)
        kw_contrib = self.w_keywords * kw_score
        reasons.append(DensityReason(
            "keywords",
            kw_contrib,
            {"n_unique_keywords": n_kw, "score": kw_score, "weight": self.w_keywords},
        ))

        # ========= 6) Normalized text =========
        # AnalyzeResult.normalized_text :contentReference[oaicite:14]{index=14}
        normalized_text = (ar.normalized_text or "").strip()
        raw_len = max(len(raw_text or ""), 1)
        norm_len = len(normalized_text)

        # 有些消息 normalized_text 可能为空，但 raw_text 有内容：此时有效率偏低
        effective_ratio = norm_len / raw_len

        # 粗略冗余 proxy：唯一字符比例越低，冗余越高（你也可以换成 n-gram 重复率）
        if norm_len > 0:
            uniq_char_ratio = len(set(normalized_text)) / norm_len
            repeat_ratio_proxy = 1.0 - uniq_char_ratio
        else:
            repeat_ratio_proxy = 1.0

        norm_score = _clip(
            0.5 * _saturate(effective_ratio / 0.65) +
            0.5 * (1.0 - _saturate(repeat_ratio_proxy / 0.25))
        )
        norm_contrib = self.w_norm * norm_score
        reasons.append(DensityReason(
            "normalized_text",
            norm_contrib,
            {
                "raw_len": raw_len,
                "normalized_len": norm_len,
                "effective_ratio": effective_ratio,
                "repeat_ratio_proxy": repeat_ratio_proxy,
                "score": norm_score,
                "weight": self.w_norm,
            },
        ))

        # ========= 7) Pragmatics: is_question / self_ref / emotion =========
        # AnalyzeResult.is_question/is_self_reference/emotion_cues :contentReference[oaicite:15]{index=15}
        structure_strength = (ent_score + frames_score + rel_score) / 3.0

        # 7.1 is_question：明确问题在结构强时加分更大
        question_bonus = 0.0
        if ar.is_question is True:
            question_bonus = 0.08 if structure_strength >= 0.35 else 0.02
        reasons.append(DensityReason(
            "is_question_bonus",
            question_bonus,
            {"is_question": ar.is_question, "structure_strength": structure_strength},
        ))

        # 7.2 is_self_reference：自指在结构弱时更可能是“状态/情绪表达”，会稀释可执行信息
        self_penalty = 0.0
        if ar.is_self_reference is True:
            self_penalty = -0.10 if structure_strength < 0.30 else -0.03
        reasons.append(DensityReason(
            "self_reference_penalty",
            self_penalty,
            {"is_self_reference": ar.is_self_reference, "structure_strength": structure_strength},
        ))

        # 7.3 emotion_cues：同理，结构弱时惩罚更重
        # 你这里 emotion_cues 是 List[str] :contentReference[oaicite:16]{index=16}
        emotion_penalty = 0.0
        n_emotion = len([c for c in (ar.emotion_cues or []) if (c or "").strip()])
        if n_emotion > 0:
            # 先用数量饱和得到强度
            emotion_strength = _saturate(n_emotion / 6.0)
            emotion_penalty = (-0.12 if structure_strength < 0.30 else -0.04) * emotion_strength
        reasons.append(DensityReason(
            "emotion_penalty",
            emotion_penalty,
            {"n_emotion_cues": n_emotion, "structure_strength": structure_strength},
        ))

        # ========= 8) 合成 raw =========
        raw = (
            ent_contrib +
            frames_contrib +
            rel_contrib +
            token_contrib +
            kw_contrib +
            norm_contrib +
            question_bonus +
            self_penalty +
            emotion_penalty
        )
        reasons.append(DensityReason("raw_sum", raw, {"note": "sum of contributions"}))

        # ========= 9) 映射到 0~1 =========
        if self.use_sigmoid:
            density = _sigmoid01(raw, center=self.sigmoid_center, scale=self.sigmoid_scale)
            reasons.append(DensityReason("sigmoid_map", density, {"center": self.sigmoid_center, "scale": self.sigmoid_scale}))
        else:
            density = _clip(raw, 0.0, 1.0)
            reasons.append(DensityReason("clip_map", density, {"note": "density = clip(raw)"}))

        return DensityDecision(density=density, raw=raw, reasons=reasons)
