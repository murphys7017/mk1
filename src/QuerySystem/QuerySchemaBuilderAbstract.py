"""
QuerySystem.QuerySchemaBuilderAbs 的 Docstring

生成 QuerySchema 的抽象基类
"""
from abc import ABC, abstractmethod
from DataClass.AnalyzeResult import AnalyzeResult
from DataClass.ChatMessage import ChatMessage
from DataClass.QuerySchema import QuerySchema



class QuerySchemaBuilderAbstract(ABC):
    @abstractmethod
    def build_query_schema(self, msg: ChatMessage) -> QuerySchema:
        """
        主入口：从 AnalyzeResult 构建 QuerySchema
        """
        raise NotImplementedError("Subclasses must implement build_query_schema method.")
    
    
    def addMessage(self, msg: ChatMessage) -> ChatMessage:
        """
        可选：向 builder 添加新的消息（如果需要增量更新）
        """
        msg.query_schema = self.build_query_schema(msg)
        return msg