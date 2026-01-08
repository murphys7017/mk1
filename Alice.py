import time
from typing import Any
from openai import OpenAI
from Agent.Agent import Agent
from ChatStateSystem.DefaultChatStateSystem import DefaultChatStateSystem
from ChatStateSystem.ChatStateSystem import ChatStateSystem
from ContextAssembler.DefaultGlobalContextAssembler import DefaultGlobalContextAssembler
from EventBus import EventBus
from LLM.LLMManagement import LLMManagement
from DataClass.ChatMessage import ChatMessage
from PerceptionSystem.PerceptionSystem import PerceptionSystem
from MemorySystem.MemorySystem import MemorySystem
from loguru import logger

from PostTurnProcessor import PostTurnProcessor
from RawChatHistory.RawChatHistory import RawChatHistory
from RawChatHistory.SqlitManagementSystem import SqlitManagementSystem
from SystemPrompt import SystemPrompt

class Alice:
    """ Alice 聊天机器人主类
    包含感知系统和记忆系统
    
    pipline:
    用户多模态输入 -> 感知系统分析 -> 记忆系统构建消息 -> LLM生成响应 -> 返回响应 -> 更新记忆系统 

    """
    def __init__(self,
                 client: Agent, 
                 history_window=20, 
                 dialogue_window=4,
                 min_raw_for_summary=4,
                 default_history_length=100, 
                 default_dialogue_length=20 , 
                 db_path="chat_history.db" , 
                 db_echo=True,
                 **kwargs):
        self.history_window = history_window
        self.dialogue_window = dialogue_window
        self.min_raw_for_summary = min_raw_for_summary

        self.llm_management = LLMManagement()
        self.system_prompt = SystemPrompt()
        self.event_bus = EventBus()

        


        self.perception_system = PerceptionSystem(self.llm_management)

        

        
        self.raw_history = RawChatHistory(
                history_length= default_history_length, 
                dialogue_length= default_dialogue_length , 
                db_path= db_path, 
                echo= db_echo,
        )


        self.chat_state_system = DefaultChatStateSystem(
            llm_management=self.llm_management,
            system_prompt=self.system_prompt,
            raw_history=self.raw_history,
            history_window=self.history_window,
        )

        


        self.memory_system = MemorySystem(
            self.history_window, self.dialogue_window, self.min_raw_for_summary,
            self.raw_history, self.llm_management
        )

        self.post_tuen_processor = PostTurnProcessor(
            memory_long= 100,
            event_bus= self.event_bus,
            memory_system= self.memory_system, 
            chat_state_system= self.chat_state_system,
            raw_history= self.raw_history
            )
        


        self.assembler = DefaultGlobalContextAssembler(
            memory_system=self.memory_system,  # 后续设置
            chat_state_system=self.chat_state_system,  # 后续设置
            system_prompt=self.system_prompt,
            raw_history=self.raw_history,  # 后续设置
            history_window=self.history_window
        )


    
        self.client = client
    
    async def respond(self, user_inputs: dict[str, Any]) -> str:
        """
        生成对用户输入的响应
        """
        # 处理响应
        user_input = await self.perception_system.analyze(user_inputs)

        logger.debug(f"Perceived messages: {user_input}")

        # 添加到数据库
        user_input_id = self.raw_history.addMessage(user_input)
        logger.debug(f"User input added to history: {user_input}")

        # 构建消息
        messages = self.assembler.build_messages()
        logger.debug(f"Built messages for response: {messages}")

        # 调用LLM生成响应
        try:
            response = self.client.respond(messages)
        except Exception as e:
            logger.error(f"Error during LLM response: {e}")
            default_error_msg = "抱歉，生成响应时出错。请稍后再试。"
            self.raw_history.deleteMessageById(user_input_id)
            return default_error_msg
        logger.debug(f"Alice response: {response}")



        # 添加助手响应到数据库
        assistant_response_id = self.raw_history.addMessage(ChatMessage(
                role="assistant", content=response,
                timestamp=int(round(time.time() * 1000)),
                timedate=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                ))
        # 触发回合完成事件
        self.event_bus.publish(
            event_type="ASSISTANT_RESPONSE_GENERATED",
            data=response,
            turn_id=assistant_response_id
        )
        return response
    
