from __future__ import annotations
import time
from DataClass.AnalyzeResult import AnalyzeResult, Argument, Entity, Frame, Relation
from ltp import LTP # type: ignore
import torch
from loguru import logger
from PerceptionSystem.AnalyzeAbstract import Analyze
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from functools import lru_cache

class LtpAnalyze(Analyze):
    def __init__(self,**kwargs):
        if kwargs.get('ltp', None):
            self.ltp = kwargs['ltp']
        else:
            self.ltp = LTP(kwargs.get("ltp_model_path", r"src\PerceptionSystem\ltp\base"))
            # 将模型移动到 GPU 上
            if torch.cuda.is_available():
                # ltp.cuda()
                self.ltp.to("cuda") # type: ignore
        
        # ---------------------------
        # 2) keywords：tokens + pos + stopwords 过滤
        # ---------------------------
        if kwargs.get('ltp_stopwords', None):
            self.STOPWORDS = kwargs['ltp_stopwords']
        else:
            self.STOPWORDS = self.load_stopwords(kwargs.get("ltp_stopwords_path", r"src\PerceptionSystem\ltp\base\stopwords_full.txt"))



    @lru_cache(maxsize=1)
    def load_stopwords(self, file_path: str) -> set[str]:
        """
        加载停用词文件，自动缓存（只读一次）
        """
        stopwords = set()

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip()
                if w:
                    stopwords.add(w)

        return stopwords
    
    def analyze(self, input_data: str) -> AnalyzeResult:
        analysis_results = self.text_analysis(input_data)
        return analysis_results
    

    def text_analysis(self, text: str) -> AnalyzeResult:
        #  分词 cws、词性 pos、命名实体标注 ner、语义角色标注 srl、依存句法分析 dep、语义依存分析树 sdp、语义依存分析图 sdpg
        output = self.ltp.pipeline(
            [text], 
            tasks=["cws", "pos", "ner", "srl", "dep", "sdp", "sdpg"])

        if output == {} or output is None:
            return AnalyzeResult()
        # 使用字典格式作为返回结果
        res = AnalyzeResult()
        res.raw["ltp"] = dict(output)
        res.keywords = self._keywords(output)
        res.tokens = self._tokens(output)
        res.frames = self._frames(output, res.tokens)
        res.entities = self._entities(output)
        res.relations = self._relations(output, res.tokens)
        res.normalized_text = self._normalized(text)
        

        return res
    def _normalized(self, text: str) -> str:
        """文本规范化处理"""
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    def _keywords(self, output):
        """提取关键词结果"""
        tokens = output.cws[0]

        # 过滤停用词并去除空白
        filtered = [t for t in tokens if t and t.strip() and t not in self.STOPWORDS]

        # 可能还希望去重并保持顺序
        seen = set()
        keywords = []
        for t in filtered:
            k = t.strip()
            if k in seen:
                continue
            seen.add(k)
            keywords.append(k)

        return keywords
    


    def _tokens(self,ltp_output) -> List[Tuple[str,str]]:
        """
        从 LTP 输出中提取并标准化分词与词性标注结果。

        清理原始分词中的首尾空白字符与换行符，生成带唯一 ID 的 token 列表，
        便于后续句法与语义分析模块引用。

        Args:
            ltp_output: LTP 原始输出字典，需包含 'cws' 和 'pos' 字段。

        Returns:
            List[Dict]: 每个元素为 {'id': int, 'text': str, 'pos': str}，
                        id 从 1 开始递增，text 已 strip() 处理。

        Raises:
            ValueError: 当 cws 或 pos 字段缺失、长度不一致时。
        """
        try:
            cws_list: List[str] = ltp_output.cws[0]
            pos_list: List[str] = ltp_output.pos[0]
        except (KeyError, IndexError) as e:
            logger.error("LTP output missing required fields: 'cws' or 'pos'")
            raise ValueError("Invalid LTP output format: missing 'cws' or 'pos'") from e

        if len(cws_list) != len(pos_list):
            logger.error("Length mismatch between 'cws' and 'pos'")
            raise ValueError("Token and POS sequences must have equal length")

        tokens = []
        for idx, (word, pos) in enumerate(zip(cws_list, pos_list)):
            clean_word = word.strip().replace("\n", " ").strip()
            # 跳过纯空白 token（如仅含空格/换行）
            if not clean_word:
                continue
            tokens.append([word, pos])
        return tokens


    def _frames(
            self,
        ltp_output, tokens
    ) -> List[Frame]:
        """
        解析 LTP 语义角色标注（SRL）结果，构建结构化事件表示。

        Args:
            ltp_output: LTP 原始输出字典，需包含 'srl' 字段。
            tokens: 由 extract_tokens 生成的标准 token 列表。

        Returns:
            List[Dict]: 每个元素代表一个谓词事件，
                        包含 predicate 信息和 arguments 列表。
        """
        from DataClass.AnalyzeResult import Argument, Frame

        srl_events = []
        try:
            srl_list = ltp_output.srl[0]
        except (KeyError, IndexError):
            logger.debug("No SRL data found in LTP output")
            return srl_events

        # 构建 token 文本映射
        token_texts = [tok[0] for tok in tokens]

        for pred_info in srl_list:
            if not isinstance(pred_info, dict):
                continue
            
            pred_index = pred_info.get("index", -1)
            predicate_text = pred_info.get("predicate", "")
            arguments_raw = pred_info.get("arguments", [])

            # 验证谓词位置有效性
            if pred_index < 0 or pred_index >= len(token_texts):
                logger.warning(f"Invalid predicate index: {pred_index}")
                continue

            predicate = {
                "text": predicate_text,
                "position": pred_index + 1  # 转为 1-based
            }
            frame = Frame(predicate_text,[pred_index])
            
            for arg in arguments_raw:
                if len(arg) != 4:
                    continue
                role, span_text, start, end = arg
                # 提取实际文本（兼容 token 合并）
                actual_text = "".join(token_texts[start : end + 1])
                argument = Argument(
                    role=role,
                    text=actual_text,
                    span=[start, end]
                )
                frame.arguments.append(argument)

            srl_events.append(frame)
        return srl_events

    def _entities(self, ltp_output) -> List[Entity]:
        """从 LTP 输出中提取命名实体结果"""
        entities = []
        try:
            ner_list = ltp_output.ner[0]
        except (KeyError, IndexError):
            logger.debug("No NER data found in LTP output")
            return entities

        for ner in ner_list:
            if len(ner) != 3:
                continue
            entity_text, entity_type, (start, end) = ner
            entity = Entity(
                text=entity_text,
                typ=entity_type,
                span=[start, end]
            )
            entities.append(entity)

        return entities
    
    def _relations(self, ltp_output, tokens):
        sdpg = ltp_output.sdpg[0]
        rels = []
        for child, head, rel in sdpg:
            s = tokens[child-1][0]
            o = tokens[head-1][0]
            rels.append(Relation(
                subject=s,
                relation=rel,
                obj=o
            ))
        return rels