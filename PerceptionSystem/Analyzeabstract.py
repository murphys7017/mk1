from abc import ABC, abstractmethod

class Analyze(ABC):
    @abstractmethod
    def analyze(self,input_data) -> dict:
        pass