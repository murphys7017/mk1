from LLM.OllamaChat import OllamaChat
from LLM.OllamaFormated import OllamaFormated
from loguru import logger
from DataClass.PromptTemplate import PromptTemplate
from SystemPrompt import SystemPrompt
from tools.tools import tools
class LLMManagement():
    def __init__(self,system_prompt: SystemPrompt):
        self.model_map = {
            "split_buffer_by_topic_continuation": "qwen3:1.7b",
            "text_analysis": "qwen3:1.7b",
            "judge_dialogue_summary": "qwen3:1.7b",
            "summarize_dialogue": "qwen3:4b",
            "judge_chat_state": "qwen3:1.7b",
            "qw8": "qwen3:8b"
        }
        self.llm_map = {
            "qwen3:8b": OllamaChat(),
            "qwen3:1.7b": OllamaFormated(),
            "qwen3:4b": OllamaFormated(),
        }
        self.system_prompt = system_prompt

    def render_prompt(self, template: PromptTemplate, **kwargs) -> str:
        missing = set(template.required_fields) - set(kwargs.keys())
        if missing:
            logger.warning(f"Missing required fields for prompt '{template.name}': {missing}")
            return ""
        return tools.normalizeBlock(template.template.format(**kwargs))
    
    def chat(self, messages: list[dict], name: str, options: dict | None = None) -> str:

        if name is None:
            logger.error(f"Model for prompt '{name}' not found in model_map.")
            return ""
        
        model_name = self.model_map.get(name)
        if model_name is None:
            logger.error(f"Model for prompt '{model_name}' not found in model_map.")
            return ""
        
        llm = self.llm_map.get(model_name)
        if llm is None:
            logger.error(f"Model '{model_name}' not found in LLMManagement.")
            return ""
        
        if options:
            return llm.chat(messages, model_name, options)
        else:
            return llm.respond(messages)

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
        
