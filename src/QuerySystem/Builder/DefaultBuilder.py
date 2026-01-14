from typing import List, Optional, Literal, cast
from dataclasses import dataclass, field

SignalDensity = Literal["low", "mid", "high"]
SourceName = Literal["short_term", "mid_term", "long_term", "world_core", "user_profile"]

# 假设 QuerySchema 已按前述定义
from DataClass.AnalyzeResult import AnalyzeResult
from DataClass.QuerySchema import QuerySchema
from QuerySystem.QuerySchemaBuilderAbs import QuerySchemaBuilderAbs

class DefaultQuerySchemaBuilder(QuerySchemaBuilderAbs):
    def __init__(self):
        # 可配置阈值（未来可从 config 注入）
        self.low_signal_keyword_threshold = 1      # 关键词少于1个 → low
        self.low_signal_frame_threshold = 1        # 无完整 frame → low
        self.default_sources: List[SourceName] = ["short_term", "mid_term", "user_profile"]
        self.world_core_fallback_sources: List[SourceName] = ["world_core"]

    def build_query_schema(self, analyze: AnalyzeResult) -> QuerySchema:
        """
        主入口：从 AnalyzeResult 构建 QuerySchema
        """
        signal_density: SignalDensity = self._assess_signal_density(analyze)
        retrieve = (signal_density != "low")

        if not retrieve:
            # 低信号：禁止检索，仅允许 WORLD_CORE（由 Assembler 注入）
            return QuerySchema(
                intent=self._infer_intent(analyze),
                signal_density="low",
                retrieve=False,
                sources=cast(List[SourceName], []),
                query=None,
                top_k=0,
                reasons={"low_signal": True}
            )

        # 高/中信号：允许检索
        query_text = analyze.normalized_text or ""
        keywords = analyze.keywords
        tags = self._extract_tags(analyze)

        return QuerySchema(
            intent=self._infer_intent(analyze),
            signal_density=signal_density,
            retrieve=True,
            sources=list(self.default_sources),  # 可根据 intent 动态调整
            tags=tags,
            query=query_text if query_text.strip() else None,
            top_k=5,
            ttl_seconds=86400 * 7,  # 7天（可配置）
            token_budget=512,
            fallback="use_world_core",
            reasons={
                "keywords_count": len(keywords),
                "frames_count": len(analyze.frames),
                "has_question": bool(analyze.is_question),
                "self_reference": bool(analyze.is_self_reference),
            }
        )
    
    def _assess_signal_density(self, analyze: AnalyzeResult) -> SignalDensity:
        # 规则1：典型低信号文本（硬匹配）
        low_signal_patterns = {"在吗", "？", "?", "嗯", "hello", "hi", "ok", "好的"}
        norm_text = (analyze.normalized_text or "").strip().lower()
        if norm_text in low_signal_patterns:
            return "low"

        # 规则2：无关键词 + 无 frame + 非问句 → low
        has_keywords = len(analyze.keywords) >= self.low_signal_keyword_threshold
        has_frames = len(analyze.frames) >= self.low_signal_frame_threshold
        is_question = analyze.is_question is True

        if not (has_keywords or has_frames or is_question):
            return "low"

        # 规则3：自指 + 问句 → high（如“你喜欢我吗？”）
        if analyze.is_self_reference and is_question:
            return "high"

        # 默认 mid
        return "mid"
    def _infer_intent(self, analyze: AnalyzeResult) -> Optional[str]:
        if not analyze.frames:
            return "clarify" if analyze.is_question else "acknowledge"

        # 从 frames/relation 提取高频谓词/关系
        predicates = {f.predicate for f in analyze.frames}
        relations = {r.relation for r in analyze.relations if r.relation}

        # TODO：规则表或小模型判断
        

        return "general_conversation"
    def _extract_tags(self, analyze: AnalyzeResult) -> List[str]:
        tags = set()

        # 从实体类型生成 tag
        for e in analyze.entities:
            if e.typ:
                tags.add(f"type:{e.typ.lower()}")

        # 从关键词生成 tag（可选）
        for kw in analyze.keywords[:5]:  # 限前5个
            tags.add(f"kw:{kw.lower()}")

        # 从情绪线索生成 tag
        for cue in analyze.emotion_cues:
            tags.add(f"emotion:{cue.lower()}")

        return sorted(tags)