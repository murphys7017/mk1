
import time
from ltp import LTP
import torch
from loguru import logger
from PerceptionSystem.Analyzeabstract import Analyze


class LtpAnalyze(Analyze):
    def __init__(self):
        self.ltp = LTP(r"PerceptionSystem\ltp\base")
        # 将模型移动到 GPU 上
        if torch.cuda.is_available():
            # ltp.cuda()
            self.ltp.to("cuda")

    
    def analyze(self, input_data: str) -> dict:
        analysis_results = self.text_analysis(input_data)
        return analysis_results
    

    def text_analysis(self, text: str) -> dict:
        #  分词 cws、词性 pos、命名实体标注 ner、语义角色标注 srl、依存句法分析 dep、语义依存分析树 sdp、语义依存分析图 sdpg
        output = self.ltp.pipeline(
            [text], 
            tasks=["cws", "pos", "ner", "srl", "dep", "sdp", "sdpg"])
        # 使用字典格式作为返回结果
        print(output.cws)  # print(output[0]) / print(output['cws']) # 也可以使用下标访问
        print(output.pos)
        print(output.sdp)
        logger.debug(f"Text Analysis Response: {output}")
        # data = None

        if output is {} or output is None:
            return {
                "is_question": False,
                "is_self_reference": False,
                "mentioned_entities": [],
                "emotional_cues": []
            }
        else:
            return output
