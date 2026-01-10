from __future__ import annotations
import time
from DataClass.AnalyzeResult import AnalyzeResult, Argument, Entity, Frame, Relation
from ltp import LTP # type: ignore
import torch
from loguru import logger
from PerceptionSystem.Analyzeabstract import Analyze
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from functools import lru_cache

class LtpAnalyze(Analyze):
    def __init__(self):
        self.ltp = LTP(r"PerceptionSystem\ltp\base")
        # 将模型移动到 GPU 上
        if torch.cuda.is_available():
            # ltp.cuda()
            self.ltp.to("cuda")
        
        # ---------------------------
        # 2) keywords：tokens + pos + stopwords 过滤
        # ---------------------------
        self.STOPWORDS = self.load_stopwords(r"PerceptionSystem\ltp\stopwords.txt")



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
        if output is {} or output is None:
            return AnalyzeResult()
        # 使用字典格式作为返回结果
        res = AnalyzeResult()
        res.raw["ltp"] = output

        return res