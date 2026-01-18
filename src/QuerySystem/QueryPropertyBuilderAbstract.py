"""
QuerySystem.QuerySchemaBuilderAbs 的 Docstring

生成 QuerySchema 的抽象基类
"""
from abc import ABC, abstractmethod
from typing import Any, List
from DataClass.AnalyzeResult import AnalyzeResult
from DataClass.ChatMessage import ChatMessage
from DataClass.QuerySchema import QuerySchema



class QueryPropertyBuilderAbstract(ABC):
    @abstractmethod
    def buildProperty(self, msg: ChatMessage) -> List[tuple[str, Any, Any]] | List[tuple[str, Any]]:
        """
        主入口：从 ChatMessage 构建 QuerySchema中的一个属性，返回 (属性名, 属性值, 原因)
        例如：("mode", "keyword")
        """
        raise NotImplementedError("Subclasses must implement build_query_schema method.")
    
    @abstractmethod
    def getPriority(self) -> int:
        """
        可选：返回 builder 的优先级，数值越小优先级越高，默认 100
        """
        return 100