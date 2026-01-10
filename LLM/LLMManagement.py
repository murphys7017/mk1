from LLM.QwenFormated import QwenFormated
from LLM.OllamaFormated import Ollama
from SystemPrompt import SystemPrompt
from loguru import logger
from DataClass.PromptTemplate import PromptTemplate
from tools import tools
class LLMManagement():
    def __init__(self):
        self.model_map = {
            "split_buffer_by_topic_continuation": "qwen3:1.7b",
            "text_analysis": "qwen3:1.7b",
            "judge_dialogue_summary": "qwen3:1.7b",
            "summarize_dialogue": "qwen3:4b",
            "judge_chat_state": "qwen3:1.7b",
            "generate_response": "qwen-plus"
        }
        self.llm_map = {
            "QWen": QwenFormated(),
            "qwen3:1.7b": Ollama(),
            "qwen3:4b": Ollama()
        }
        self.system_prompt = SystemPrompt()

    def render_prompt(self, template: PromptTemplate, **kwargs) -> str:
        missing = set(template.required_fields) - set(kwargs.keys())
        if missing:
            logger.warning(f"Missing required fields for prompt '{template.name}': {missing}")
            return ""
        return tools.normalizeBlock(template.template.format(**kwargs))


    def generate(
            self, 
            prompt_name: str,
            options: dict | None = None,
            **kwargs
            ) -> dict:
        prompt_template = self.system_prompt.getPrompt(prompt_name)
        prompt = self.render_prompt(prompt_template, **kwargs)
        model_name = self.model_map.get(prompt_name)
        if model_name is None:
            logger.error(f"Model for prompt '{prompt_name}' not found in model_map.")
            return {}
        if prompt == "":
            return self.llm_map[model_name].failuredResponse()
        llm = self.llm_map.get(model_name)
        if llm is None:
            logger.error(f"Model '{model_name}' not found in LLMManagement.")
            return {}
        return llm.generate(prompt, model_name, options)
        
