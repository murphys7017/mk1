import time
from typing import Any
from ChatStateSystem.DefaultChatStateSystem import DefaultChatStateSystem
from ContextAssembler.DefaultGlobalContextAssembler import DefaultGlobalContextAssembler
from DataClass.EventType import EventType
from EventBus import EventBus
from LLM.LLMManagement import LLMManagement
from DataClass.ChatMessage import ChatMessage
from PerceptionSystem.PerceptionSystem import PerceptionSystem
from MemorySystem.MemorySystem import MemorySystem
from loguru import logger
from QuerySystem.DefaultQuerySchemaBuilder import DefaultQuerySchemaBuilder
from tools.tools import tools

from PostTreatmentSystem.PostHandleSystem import PostHandleSystem
from PostTurnProcessor import PostTurnProcessor
from RawChatHistory.RawChatHistory import RawChatHistory
from SystemPrompt import SystemPrompt

class Alice:
    """ Alice 聊天机器人主类
    包含感知系统和记忆系统
    
    pipline:
    用户多模态输入 -> 感知系统分析 -> 查询系统查询 -> 记忆系统构建消息 -> LLM生成响应 -> 返回响应 -> 更新记忆系统 

    **kwargs 参数说明**:
    - history_window: 记忆系统中近期消息窗口大小（轮数）
    - dialogue_window: 记忆系统中近期摘要窗口大小（条数）
    - min_raw_for_summary: 记忆系统中生成摘要所需的最少原始消息轮数
    - default_history_length: 原始聊天历史的默认最大长度（轮数） / 缓存多少轮原始消息
    - default_dialogue_length: 原始聊天历史的摘要最大长度（轮数）/缓存多少轮摘要
    - db_path: 聊天历史数据库路径
    - db_echo: 是否开启数据库操作日志
    - analysis_window: 聊天状态分析窗口大小（轮数）


    """
    def __init__(self, **kwargs):
        self.history_window = kwargs.get("history_window", 20)
        self.dialogue_window = kwargs.get("dialogue_window", 4)
        self.min_raw_for_summary = kwargs.get("min_raw_for_summary", 4)

        self.system_prompt = SystemPrompt()
        self.llm_management = LLMManagement(self.system_prompt)
        
        self.event_bus = EventBus()

        self.perception_system = PerceptionSystem(self.llm_management, **kwargs)

        

        
        self.raw_history = RawChatHistory(
                history_length= kwargs.get("default_history_length", 100), 
                dialogue_length= kwargs.get("default_dialogue_length", 20), 
                db_path= kwargs.get("db_path", "chat_history.db"), 
                echo= kwargs.get("db_echo", True)
        )


        self.chat_state_system = DefaultChatStateSystem(
            llm_management=self.llm_management,
            system_prompt=self.system_prompt,
            raw_history=self.raw_history,
            history_window=self.history_window,
        )

        self.query_builder = DefaultQuerySchemaBuilder(
            llm_management=self.llm_management,
            template_path="config/template_input.yaml"
        )


        self.memory_system = MemorySystem(
            self.history_window, 
            self.dialogue_window, 
            self.min_raw_for_summary,
            self.raw_history, self.llm_management
        )
        self.post_handle_system = PostHandleSystem(
            event_bus=self.event_bus,
            llm_management=self.llm_management,
            raw_history=self.raw_history,
            **kwargs
        )

        self.post_tuen_processor = PostTurnProcessor(
            event_bus= self.event_bus,
            memory_system= self.memory_system, 
            chat_state_system= self.chat_state_system,
            raw_history= self.raw_history,
            post_handle_system= self.post_handle_system
            )
        


        self.assembler = DefaultGlobalContextAssembler(
            memory_system=self.memory_system,  # 后续设置
            chat_state_system=self.chat_state_system,  # 后续设置
            system_prompt=self.system_prompt,
            raw_history=self.raw_history,  # 后续设置
            history_window=self.history_window,
            analysis_window=kwargs.get("analysis_window",3),
        )

        

    
    
    async def respond(self, user_inputs: dict[str, Any]) -> str:
        """
        生成对用户输入的响应
        """
        logger.debug(f"Alice received user inputs: {user_inputs}")
        # 处理响应
        user_input = await self.perception_system.analyze(user_inputs)
        logger.debug("User input after perception analysis: " + str(user_input))

        user_input = self.query_builder.addMessage(user_input)
        logger.debug("User input after query schema building: " + str(user_input.query_schema))


        # 添加到数据库
        user_input_id = self.raw_history.addMessage(user_input)

        logger.info(f"Added user input to history with ID: {user_input_id}")


        # 构建消息
        messages = self.assembler.build_messages()
        logger.debug("System Prompt:")
        logger.debug(messages[0]['content'])

        block = tools.formatBlock(
            "Messages:",
            f"{messages[1:]}",
            width=100,
        )
        logger.debug("\n" + block)

        # 调用LLM生成响应
        try:
            response = self.llm_management.chat(messages, "qw8")
        except Exception as e:
            logger.error(f"Error during LLM response: {e}")
            default_error_msg = "抱歉，生成响应时出错。请稍后再试。"
            self.raw_history.deleteMessageById(user_input_id)
            return default_error_msg
        logger.debug(f"Alice response: {response}")



        # 添加助手响应到数据库
        assistant_response_id = self.raw_history.addMessage(ChatMessage(
				sender_name="Alice",
				sender_id=-1,
                role="assistant", content=response,
                timestamp=int(round(time.time() * 1000)),
                timedate=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                ))
        # 触发回合完成事件
        self.event_bus.publish(
            event_type=EventType.ASSISTANT_RESPONSE_GENERATED,
            data=response,
            turn_id=assistant_response_id
        )
        return response
    
