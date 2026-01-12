from abc import ABC, abstractmethod

class LLM(ABC):
    @abstractmethod
    def generate(self, prompt: str, model: str, options: dict | None = None) -> dict:
        pass
    @abstractmethod
    def failuredResponse(self) -> dict:
        pass