from enum import StrEnum

class EventType(StrEnum):
    """
    EventType 的 Docstring
    枚举了 Alice 系统中可能发生的各种事件类型
    """


    """UserInputReceived
    什么时候发：用户输入被 Alice 接收Perception 之后都会触发该事件
    用途：触发后续的处理流程，例如文本分析、状态更新等
    订阅者：PerceptionSystem、ChatStateSystem 等组件
    """
    USER_INPUT_RECEIVED = "user_input_received"
    
    """AssistantResponseGenerated
    什么时候发：当助手生成响应后触发
    用途：通知系统响应已生成，可以进行后续处理或发送给用户
    订阅者：
    """
    ASSISTANT_RESPONSE_GENERATED = "assistant_response_generated"
    STATE_UPDATED = "state_updated"
    COMMAND_ISSUED = "command_issued"
    ERROR_OCCURRED = "error_occurred"
    POST_HANDLE_COMPLETED = "post_handle_completed"
    MEMORY_UPDATED = "memory_updated"