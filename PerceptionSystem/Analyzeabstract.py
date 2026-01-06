from abc import ABC, abstractmethod

from DataClass.ChatMessage import ChatMessage


class Analyze(ABC):
    @abstractmethod
    def analyze(self,input_data) -> ChatMessage:
        pass