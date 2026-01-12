from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import uuid4
import re
from DataClass.TagType import TagType
from tools.PromptBuilder import PromptBuilder

@dataclass
class Entity:
    """
    命名实体/可引用对象（来自 NER 或规则/小模型补充）
    - eid: 实体 ID（建议形如 "E1", "E2"...，用于 Frame/Relation 引用）
    - text: 实体原文（例如 "ollama", "qwen3", "Alice"）
    - typ: 实体类型（例如 PERSON/ORG/LOC/TOOL/PROJECT/MODEL/OTHER）
    - span: token span（可选，通常是 [start, end]，按你的 tokens 索引定义）
    """
    text: Optional[str] = None
    typ: Optional[str] = None
    span: Optional[List[int]] = None


@dataclass
class Argument:
    """
    语义角色论元（Frame 的组成部分）
    - role: SRL 角色名（A0/A1/A2/ARGM-XXX 等）
    - text: 论元短语文本（例如 "我", "ollama", "本地"）
    - entity_ref: 可选，若论元可对齐到 Entity，则存 Entity.eid（推荐）
    - span: token span（可选，通常是 [start, end]）
    """
    role: str
    text: str
    entity_ref: Optional[str] = None
    span: Optional[List[int]] = None


@dataclass
class Frame:
    """
    谓词-论元结构（SRL 压缩表示）
    - predicate: 谓词（通常是动词，如 "用"、"实现"、"喜欢"）
    - predicate_span: token span（可选）
    - arguments: 论元列表（A0/A1/ARGM 等）
    """
    predicate: str
    predicate_span: Optional[List[int]] = None
    arguments: List[Argument] = field(default_factory=list)


@dataclass
class Relation:
    """
    轻量关系三元组（可选层）
    - subject / obj：建议优先存 Entity.eid；也可以暂时存实体文本（但去重更难）
    - relation：关系类型（use/build/prefer/dislike/plan/ask/compare 等）
    """
    subject: Optional[str] = None
    relation: Optional[str] = None
    obj: Optional[str] = None


@dataclass
class AnalyzeResult:
    """
    AnalyzeResult：感知阶段的结果容器（单条消息级别）

    设计原则：
    - 只承载“结构化语义信号 + 原始证据”
    - 不负责跨轮判断、记忆写入、对话关联（那些属于更外层模块）
    """

    # ========= meta =========
    turn_id: Optional[int] = None
    # 时间戳：建议统一为“毫秒”，如果你用秒也可以，但务必全项目一致
    timestamp: Optional[int] = None
    # 输入媒体类型：目前默认 text，未来可扩展 image/audio/video
    media_type: str = "text"
    # AnalyzeResult 的结构版本号，便于后续 schema 升级/迁移
    schema_version: str = "analyze_v1"

    # ========= structured semantics (主要来自 LTP) =========
    # 命名实体清单（从 NER 规范化而来）
    entities: List[Entity] = field(default_factory=list)
    # 语义事件/谓词结构（从 SRL 规范化而来）
    frames: List[Frame] = field(default_factory=list)

    tokens: List[Tuple[str,str]] = field(default_factory=list)
    # 过滤后的内容词/关键词（用于话题分段、检索、路由；不一定喂给主模型）
    keywords: List[str] = field(default_factory=list)
    # 轻量关系三元组（可选：可由 frames 或规则生成）
    relations: List[Relation] = field(default_factory=list)
    # 规范化文本（清洗后的文本：去多余空白/统一符号等，不改写语义）
    normalized_text: Optional[str] = None

    # ========= lightweight signals (通常来自规则/小模型) =========
    # 是否问句：None 表示“未判定/未分析”，True/False 表示已判定
    is_question: Optional[bool] = None
    # 是否提及 AI 自身/自指：同上，None 表示未判定
    is_self_reference: Optional[bool] = None
    # 情绪线索（只存 cues，不存结论；例如出现的情绪词、标点特征等）
    emotion_cues: List[str] = field(default_factory=list)

    # ========= raw evidence =========
    # 原始分析数据：{ analyzer_name: raw_payload }
    # 例如：raw["ltp"] = {"cws":..., "pos":..., "ner":..., "srl":..., "dep":..., "sdp":..., "sdpg":...}
    raw: Dict[str, Any] = field(default_factory=dict)




    # 假设这些类已按你之前的定义存在：
    # Entity, Argument, Frame, Relation, AnalyzeResult

    @staticmethod
    def _norm_key(s: Optional[str]) -> str:
        """用于去重的轻量规范化：None -> ''，去首尾空白。"""
        return (s or "").strip()

    @staticmethod
    def _span_key(span: Optional[List[int]]) -> Tuple[int, int]:
        """None 视为 (-1,-1)；否则闭区间 (start,end)。"""
        if not span or len(span) < 2:
            return (-1, -1)
        return (int(span[0]), int(span[1]))

    @staticmethod
    def _dedup_keep_order(items: Iterable[Any], key_fn) -> List[Any]:
        seen = set()
        out = []
        for x in items:
            k = key_fn(x)
            if k in seen:
                continue
            seen.add(k)
            out.append(x)
        return out

    @staticmethod
    def _entity_key(e: "Entity") -> Tuple[str, str, Tuple[int, int]]:
        # 同名同类型同 span 视为同一实体；span 缺失就用 (-1,-1)
        return (AnalyzeResult._norm_key(e.text), AnalyzeResult._norm_key(e.typ), AnalyzeResult._span_key(e.span))

    @staticmethod
    def _arg_key(a: "Argument") -> Tuple[str, str, str, Tuple[int, int]]:
        # role + entity_ref/text + span 去重
        return (
            AnalyzeResult._norm_key(a.role),
            AnalyzeResult._norm_key(a.entity_ref),
            AnalyzeResult._norm_key(a.text),
            AnalyzeResult._span_key(a.span),
        )

    @staticmethod
    def _frame_key(f: "Frame") -> Tuple[str, Tuple[int, int], Tuple[Tuple, ...]]:
        # predicate + predicate_span + (arguments...) 去重
        args_sig = tuple(sorted((AnalyzeResult._arg_key(a) for a in f.arguments)))
        return (AnalyzeResult._norm_key(f.predicate), AnalyzeResult._span_key(f.predicate_span), args_sig)

    @staticmethod
    def _relation_key(r: "Relation") -> Tuple[str, str, str]:
        return (AnalyzeResult._norm_key(r.subject), AnalyzeResult._norm_key(r.relation), AnalyzeResult._norm_key(r.obj))
    @staticmethod
    def merge_analyze_results(
        results: Sequence["AnalyzeResult"],
        *,
        prefer_normalized_text: str = "longest",  # "first" | "last" | "longest" | "non_empty_first"
    ) -> "AnalyzeResult":
        """
        合并多个 AnalyzeResult（取并集），忽略 meta 字段：
        - turn_id / timestamp / media_type / schema_version 不参与合并（输出也不承诺保留任何一个的值）
        主要合并：
        - entities / frames / tokens / keywords / relations / normalized_text
        - raw：按 analyzer_name 合并字典；同名冲突时做“列表聚合”
        """

        if not results:
            return AnalyzeResult()

        # ====== 聚合容器 ======
        all_entities: List[Entity] = []
        all_frames: List[Frame] = []
        all_tokens: List[Tuple[str, str]] = []
        all_keywords: List[str] = []
        all_relations: List[Relation] = []
        all_raw: Dict[str, Any] = {}

        # lightweight signals
        any_is_question_true = False
        any_is_question_false = False
        any_is_self_ref_true = False
        any_is_self_ref_false = False
        all_emotion_cues: List[str] = []

        norm_texts: List[str] = []

        # ====== 1) 收集 ======
        for r in results:
            if r is None:
                continue

            all_entities.extend(list(r.entities or []))
            all_frames.extend(list(r.frames or []))
            all_tokens.extend(list(r.tokens or []))
            all_keywords.extend(list(r.keywords or []))
            all_relations.extend(list(r.relations or []))

            # merge lightweight signals
            if r.is_question is True:
                any_is_question_true = True
            elif r.is_question is False:
                any_is_question_false = True

            if r.is_self_reference is True:
                any_is_self_ref_true = True
            elif r.is_self_reference is False:
                any_is_self_ref_false = True

            for cue in (r.emotion_cues or []):
                c = (cue or "").strip()
                if c:
                    all_emotion_cues.append(c)

            if r.normalized_text:
                norm_texts.append(r.normalized_text)

            # raw 合并：同 key 冲突 -> 聚合为 list（保序、去重不做强保证）
            for k, v in (r.raw or {}).items():
                if k not in all_raw:
                    all_raw[k] = v
                else:
                    prev = all_raw[k]
                    if isinstance(prev, list):
                        prev.append(v)
                        all_raw[k] = prev
                    else:
                        all_raw[k] = [prev, v]

        # ====== 2) 去重（保序）======
        merged_entities = AnalyzeResult._dedup_keep_order(all_entities, AnalyzeResult._entity_key)
        merged_frames = AnalyzeResult._dedup_keep_order(all_frames, AnalyzeResult._frame_key)
        # tokens are (token, tag) tuples; dedupe by normalized token and tag
        merged_tokens = AnalyzeResult._dedup_keep_order(
            all_tokens, lambda t: (AnalyzeResult._norm_key(t[0]), AnalyzeResult._norm_key(t[1]))
        )
        merged_keywords = AnalyzeResult._dedup_keep_order(all_keywords, lambda k: AnalyzeResult._norm_key(k))
        merged_relations = AnalyzeResult._dedup_keep_order(all_relations, AnalyzeResult._relation_key)
        merged_emotion_cues = AnalyzeResult._dedup_keep_order(all_emotion_cues, lambda c: AnalyzeResult._norm_key(c))
        # ====== 3) normalized_text 选择策略 ======
        chosen_text: Optional[str] = None
        if prefer_normalized_text == "first":
            chosen_text = norm_texts[0] if norm_texts else None
        elif prefer_normalized_text == "last":
            chosen_text = norm_texts[-1] if norm_texts else None
        elif prefer_normalized_text == "non_empty_first":
            chosen_text = next((t for t in norm_texts if t.strip()), None)
        else:  # "longest"
            chosen_text = max(norm_texts, key=lambda x: len(x), default=None)

        # ====== 4) 输出（meta 不合并，保持默认）======
        merged = AnalyzeResult()
        merged.entities = merged_entities
        merged.frames = merged_frames
        merged.tokens = merged_tokens
        merged.keywords = merged_keywords
        merged.relations = merged_relations
        merged.normalized_text = chosen_text
        merged.raw = all_raw

        # finalize lightweight signals
        if any_is_question_true:
            merged.is_question = True
        elif any_is_question_false:
            merged.is_question = False
        else:
            merged.is_question = None

        if any_is_self_ref_true:
            merged.is_self_reference = True
        elif any_is_self_ref_false:
            merged.is_self_reference = False
        else:
            merged.is_self_reference = None

        merged.emotion_cues = merged_emotion_cues

        return merged


    def _norm_role(self,role: str) -> str:
        """A0/A1/A2 -> ARG0/ARG1/ARG2; ARGM-TMP -> TMP"""
        role = (role or "").strip()
        if re.fullmatch(r"A\d+", role):
            return "ARG" + role[1:]
        m = re.fullmatch(r"ARGM-(.+)", role)
        if m:
            return m.group(1)
        return role


    def _safe(self,s: Optional[str]) -> str:
        if not s:
            return ""
        return s.replace("\n", "\\n").replace("\r", "").strip()


    def analyze_result_to_prompt(self,
        tag: str = "USER_ANALYZE_RESULT_BLOCK",
        max_tokens_pos: int = 120,
        max_keywords: int = 40,
        max_entities: int = 20,
        max_frames: int = 10,
        max_args: int = 8,
    ) -> PromptBuilder:
        """
        AnalyzeResult -> Prompt 结构块
        """
        builder = PromptBuilder(tag)

        builder.add(f'is_question: {str(self.is_question)}')
        builder.add(f'is_self_reference: {str(self.is_self_reference)}')
        builder.add(f'emotion_cues:')
        if not self.emotion_cues:
            builder.add("  []")
        else:
            for cue in self.emotion_cues:
                builder.add(f"  - {self._safe(cue)}")
        
        # ========= tokens + pos =========
        flat_tokens = []

        # 兼容 [[tok,pos], ...]  或  [[[tok,pos],...], [...]]
        if self.tokens and isinstance(self.tokens[0], list):
            if len(self.tokens[0]) == 2 and isinstance(self.tokens[0][0], str):
                flat_tokens = self.tokens
            else:
                for sent in self.tokens:
                    for p in sent:
                        if isinstance(p, list) and len(p) == 2:
                            flat_tokens.append(p)

        if len(flat_tokens) > max_tokens_pos:
            flat_tokens = flat_tokens[:max_tokens_pos] + [["…", "…"]]

        builder.add("tokens_pos:")
        if not flat_tokens:
            builder.add("  []")
        else:
            for tok, pos in flat_tokens:
                builder.add(f'  - ["{self._safe(tok)}","{self._safe(pos)}"]')

        # ========= keywords =========
        kws = list(self.keywords or [])
        if len(kws) > max_keywords:
            kws = kws[:max_keywords] + ["…"]

        builder.add("keywords:")
        if not kws:
            builder.add("  []")
        else:
            for k in kws:
                builder.add(f"  - {self._safe(k)}")

        # ========= entities =========
        ents = list(self.entities or [])
        if len(ents) > max_entities:
            ents = ents[:max_entities]

        builder.add("entities:")
        if not ents:
            builder.add("  []")
        else:
            for e in ents:
                builder.add(
                    f"  - ["
                    f"{self._safe(e.text)}, "
                    f"{self._safe(e.typ)}]"
                )

        # ========= frames (SRL) =========
        frames = list(self.frames or [])
        if len(frames) > max_frames:
            frames = frames[:max_frames]

        builder.add("frames:")
        if not frames:
            builder.add("  []")
        else:
            for f in frames:
                builder.add(f"  - p: {self._safe(f.predicate)}")
                builder.add("    args:")

                args = list(f.arguments or [])
                if len(args) > max_args:
                    args = args[:max_args]

                for a in args:
                    role = self._norm_role(a.role)
                    if a.entity_ref:
                        builder.add(
                            f"      - [{role}, {self._safe(a.text)}, {a.entity_ref}]"
                        )
                    else:
                        builder.add(
                            f"      - [{role}, {self._safe(a.text)}]"
                        )

        builder.add(f"</{tag}>")
        return builder

