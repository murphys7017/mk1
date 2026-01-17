"""
QuerySystem.QuerySchemaBuilderAbs 的 Docstring

生成 QuerySchema 的抽象基类
"""
from abc import ABC, abstractmethod
from DataClass.AnalyzeResult import AnalyzeResult
from DataClass.QuerySchema import QuerySchema



class QuerySchemaBuilderAbs(ABC):
    @abstractmethod
    def build_query_schema(self, analyze: AnalyzeResult) -> QuerySchema:
        """
        主入口：从 AnalyzeResult 构建 QuerySchema
        """
        raise NotImplementedError("Subclasses must implement build_query_schema method.")