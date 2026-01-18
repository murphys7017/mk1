# PrototypeCosineRouter.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import math
import yaml  # PyYAML

from DataClass.ChatMessage import ChatMessage
from DataClass.AnalyzeResult import AnalyzeResult


@dataclass(slots=True)
class CosineRouteResult:
    best_label: Optional[str]
    best_score: float
    scores: Dict[str, float]          # label -> score
    debug: Dict[str, Any]             # optional debug info


class PrototypeCosineRouter:
    """
    使用 TF-IDF + cosine，将输入与各类 prototypes 做相似度比较。
    - 特征：优先用 AnalyzeResult.tokens（分词结果），否则退回简易切词（不推荐）
    - 性能：原型向量预计算 + 查询向量即时计算
    """

    def __init__(
        self,
        *,
        config_path: str = "config/template_input.yaml",
        prototypes_key: str = "prototypes",
        low_patterns_key: str = "low_signal_patterns",
        max_terms: int = 2000,
        token_pos_whitelist: Optional[set[str]] = None,
    ):
        if yaml is None:
            raise RuntimeError("PyYAML not installed. Please install pyyaml to load config/template_input.yaml")

        self.config_path = config_path
        self.prototypes_key = prototypes_key
        self.low_patterns_key = low_patterns_key
        self.max_terms = max_terms

        # 可选：用 POS 过滤噪声（你 tokens=(word,pos)）
        # 不确定你的 POS 集合细节时先别开也行
        self.token_pos_whitelist = token_pos_whitelist

        self.low_signal_patterns: set[str] = set()
        self.prototypes: Dict[str, List[str]] = {}

        # TF-IDF 模型缓存
        self._idf: Dict[str, float] = {}
        self._vocab: Dict[str, int] = {}
        self._proto_vecs: Dict[str, List[Tuple[Dict[str, float], float]]] = {}
        # label -> list of (sparse_vec, norm)

        self.reload()

    # ---------------- public ----------------

    def reload(self) -> None:
        cfg = self._load_yaml(self.config_path)
        self.low_signal_patterns = set(map(str, cfg.get(self.low_patterns_key, []) or []))

        raw_protos = cfg.get(self.prototypes_key, {}) or {}
        self.prototypes = {str(k): [str(x) for x in (v or [])] for k, v in raw_protos.items()}

        # build tf-idf from prototypes
        self._build_tfidf_from_prototypes()

    def route(self, msg: ChatMessage) -> CosineRouteResult:
        tokens = self._extract_tokens(msg)
        q_vec = self._tfidf_vector(tokens)
        q_norm = self._norm(q_vec)

        scores: Dict[str, float] = {}
        best_label: Optional[str] = None
        best_score = 0.0

        if q_norm == 0.0:
            return CosineRouteResult(
                best_label=None,
                best_score=0.0,
                scores={label: 0.0 for label in self.prototypes.keys()},
                debug={"reason": "empty_query_vector"},
            )

        for label, vec_list in self._proto_vecs.items():
            # label score = max cosine over its prototypes
            max_s = 0.0
            for p_vec, p_norm in vec_list:
                if p_norm == 0.0:
                    continue
                s = self._cosine_sparse(q_vec, q_norm, p_vec, p_norm)
                if s > max_s:
                    max_s = s
            scores[label] = max_s
            if max_s > best_score:
                best_score = max_s
                best_label = label

        return CosineRouteResult(
            best_label=best_label,
            best_score=best_score,
            scores=scores,
            debug={
                "query_terms": tokens[:30],
                "query_term_count": len(tokens),
            },
        )

    # ---------------- internal: yaml ----------------

    def _load_yaml(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    # ---------------- internal: tf-idf ----------------

    def _build_tfidf_from_prototypes(self) -> None:
        # 1) collect documents (each prototype sentence is a doc)
        docs: List[List[str]] = []
        doc_labels: List[str] = []

        for label, texts in self.prototypes.items():
            for t in texts:
                toks = self._tokenize_text_fallback(t)
                docs.append(toks)
                doc_labels.append(label)

        # 2) build DF
        df: Dict[str, int] = {}
        for toks in docs:
            for term in set(toks):
                df[term] = df.get(term, 0) + 1

        # 3) vocab cap
        # keep top max_terms by df (or you can keep all; cap helps memory)
        terms_sorted = sorted(df.items(), key=lambda x: x[1], reverse=True)
        terms_sorted = terms_sorted[: self.max_terms]
        self._vocab = {term: i for i, (term, _) in enumerate(terms_sorted)}

        # 4) idf
        N = max(1, len(docs))
        self._idf = {}
        for term, dfi in df.items():
            if term not in self._vocab:
                continue
            # smooth idf
            self._idf[term] = math.log((N + 1) / (dfi + 1)) + 1.0

        # 5) precompute prototype vectors per label
        self._proto_vecs = {label: [] for label in self.prototypes.keys()}
        for toks, label in zip(docs, doc_labels):
            vec = self._tfidf_vector(toks)
            norm = self._norm(vec)
            self._proto_vecs[label].append((vec, norm))

    def _tfidf_vector(self, toks: List[str]) -> Dict[str, float]:
        # sparse dict: term -> weight
        tf: Dict[str, int] = {}
        for term in toks:
            if term in self._vocab:
                tf[term] = tf.get(term, 0) + 1
        if not tf:
            return {}

        # tf-idf (log-tf)
        vec: Dict[str, float] = {}
        for term, cnt in tf.items():
            idf = self._idf.get(term, 0.0)
            if idf <= 0.0:
                continue
            w = (1.0 + math.log(cnt)) * idf
            vec[term] = w
        return vec

    @staticmethod
    def _norm(vec: Dict[str, float]) -> float:
        return math.sqrt(sum(v * v for v in vec.values()))

    @staticmethod
    def _cosine_sparse(
        a: Dict[str, float],
        a_norm: float,
        b: Dict[str, float],
        b_norm: float,
    ) -> float:
        if a_norm == 0.0 or b_norm == 0.0:
            return 0.0
        # iterate smaller dict
        if len(a) > len(b):
            a, b = b, a
            a_norm, b_norm = b_norm, a_norm
        dot = 0.0
        for k, av in a.items():
            bv = b.get(k)
            if bv is not None:
                dot += av * bv
        return dot / (a_norm * b_norm)

    # ---------------- token extraction ----------------

    def _extract_tokens(self, msg: ChatMessage) -> List[str]:
        """
        取 tokens 的 word 部分（可选按 POS 过滤）
        """
        ar: Optional[AnalyzeResult] = msg.analyze_result
        if ar and ar.tokens:
            out: List[str] = []
            for w, pos in ar.tokens:
                if not w:
                    continue
                if self.token_pos_whitelist is not None and pos not in self.token_pos_whitelist:
                    continue
                out.append(str(w).lower())
            return out
        # fallback: simple tokenize the raw text
        return self._tokenize_text_fallback(msg.content or "")

    @staticmethod
    def _tokenize_text_fallback(text: str) -> List[str]:
        """
        非中文友好，仅兜底：把字母数字串当词，中文按连续块拆。
        强烈建议生产环境总是用 AnalyzeResult.tokens。
        """
        text = (text or "").strip().lower()
        if not text:
            return []
        # 简易：按空白切 + 再拆连续中文/数字/字母
        import re
        parts = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", text)
        return parts
