import asyncio
import sys

import pytest
from LLM.LLMManagement import LLMManagement
from PerceptionSystem.PerceptionSystem import PerceptionSystem
from SystemPrompt import SystemPrompt
from loguru import logger

# 添加标准输出（推荐在主入口或测试 setup 中调用一次）
logger.add(sys.stderr, level="DEBUG")


@pytest.mark.asyncio
async def test_ltp():
    llm_management = LLMManagement(SystemPrompt())
    kwargs = {
        "ltp_model_path": r"D:\BaiduSyncdisk\Code\mk1\src\PerceptionSystem\ltp\base",
        "ltp_stopwords_path": r"D:\BaiduSyncdisk\Code\mk1\src\PerceptionSystem\ltp\base\stopwords_full.txt"
    }
    perception_system = PerceptionSystem(llm_management, **kwargs)
    user_input = {
        "text": "请根据以下内容，帮我总结出三个关键要点：\n1. 人工智能在保定的发展趋势\n2. 机器学习的基本原理\n3. 深度学习的应用领域",
    }
    response =  await perception_system.analyze(user_input)
    print(response)
        





        
if __name__ == "__main__":
    asyncio.run(test_ltp())


        




    
    
