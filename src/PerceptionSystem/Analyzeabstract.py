from abc import ABC, abstractmethod

from DataClass.AnalyzeResult import AnalyzeResult

class Analyze(ABC):
    @abstractmethod
    def analyze(self,input_data) -> AnalyzeResult:
        pass