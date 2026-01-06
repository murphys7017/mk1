from enum import StrEnum

class TagType(StrEnum):
    IDENTITY_CORE_TAG = "IDENTITY_CORE" # 核心身份 + 长期自我（不可违背）
    WORLD_SETTING_TAG = "WORLD_SETTING" # 世界设定 / 运行规则
    IMEMORY_LONG_TAG = "MEMORY_LONG" # 已摘要的长期记忆
    MEMORY_MID_TAG = "MEMORY_MID" # 已摘要的中期记忆
    KNOWLEDGE_TAG = "KNOWLEDGE" # 显式知识 / 世界知识
    
    RESPONSE_PROTOCOL_TAG = "RESPONSE_PROTOCOL" # 回答规范
    CHAT_STATE_TAG = "CHAT_STATE" # 对话状态