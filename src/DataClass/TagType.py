from enum import StrEnum


class TagType(StrEnum):
    """
    Prompt 标签枚举
    统一所有系统标签定义，避免魔法字符串
    """

    # ===== 记忆系统 =====
    MEMORY_SYSTEM_TAG = "MEMORY_SYSTEM"   # 记忆系统总入口
    USER_PROFILE_TAG = "USER_PROFILE"     # 用户档案
    IMEMORY_LONG_TAG = "MEMORY_LONG"      # 已摘要的长期记忆
    MEMORY_MID_TAG = "MEMORY_MID"         # 已摘要的中期记忆
    MEMORY_SHORT_TAG = "MEMORY_SHORT"     # 已摘要的短期记忆

    # ===== 身份 / 世界观 =====
    IDENTITY_CORE_TAG = "IDENTITY_CORE"   # 核心身份 + 长期自我（不可违背）
    WORLD_SETTING_TAG = "WORLD_SETTING"  # 世界设定 / 运行规则

    # ===== 知识 =====
    KNOWLEDGE_TAG = "KNOWLEDGE"           # 显式知识 / 世界知识

    # ===== 状态 & 分析 =====
    ANALYZE_TAG = "ANALYZE"               # 分析结果
    CHAT_STATE_TAG = "CHAT_STATE"         # 对话状态

    # ===== 回复控制 =====
    RESPONSE_PROTOCOL_TAG = "RESPONSE_PROTOCOL"  # 回答规范

    # ================= 工具方法 =================

    def open(self) -> str:
        """生成起始标签"""
        return f"<{self.value}>"

    def close(self) -> str:
        """生成结束标签"""
        return f"</{self.value}>"

    def wrap(self, content: str) -> str:
        """自动包裹内容"""
        return f"{self.open()}\n{content}\n{self.close()}"

    @classmethod
    def all_tags(cls) -> list[str]:
        """获取全部 tag 字符串"""
        return [t.value for t in cls]

    @classmethod
    def is_valid(cls, tag: str) -> bool:
        """校验 tag 是否合法"""
        return tag in cls.all_tags()
