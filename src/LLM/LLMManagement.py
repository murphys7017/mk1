from LLM.OllamaChat import OllamaChat
from LLM.OllamaFormated import OllamaFormated
from LLM.QwenFormated import QwenFormated
from logging_config import logger
from DataClass.PromptTemplate import PromptTemplate
from SystemPrompt import SystemPrompt
from tools.tools import tools
import yaml
from pathlib import Path
class LLMManagement():
    def __init__(self,system_prompt: SystemPrompt):
        self.model_map = self.load_config("config/system_prompt.yaml")
        self.llm_map = self.build_llm_map()
        self.system_prompt = system_prompt
    def build_llm_map(self):
        inits = [OllamaChat(), OllamaFormated(), QwenFormated()]
        llm_map = {}
        for llm in inits:
            for model in llm.supportModel():
                llm_map[model] = llm
        return llm_map
    def load_config(self, path: str) -> dict:
        """Load prompt->model mapping from a YAML file.

        If `path` is falsy or the file does not exist, attempt to load
        from the repository config/system_prompt.yaml. Returns a dict
        mapping prompt_name -> model_name.
        """
        model_map: dict[str, str] = {}
        # determine path
        p = Path(path) if path else None
        if p is None or not p.exists():
            # default location: repo_root/config/system_prompt.yaml
            p = Path(__file__).resolve().parents[2] / "config" / "system_prompt.yaml"
        try:
            if not p.exists():
                return model_map
            raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            prompts = raw.get("prompts", {})
            if not isinstance(prompts, dict):
                return model_map
            for name, spec in prompts.items():
                if isinstance(spec, dict):
                    model = spec.get("model")
                    if model:
                        model_map[name] = model
        except Exception:
            # on error, return
            return {
            "split_buffer_by_topic_continuation": "qwen3:1.7b",
            "text_analysis": "qwen3:1.7b",
            "judge_dialogue_summary": "qwen3:1.7b",
            "summarize_dialogue": "qwen3:4b",
            "judge_chat_state": "qwen3:1.7b",
            "motion_intent": "qwen3:1.7b",
            "qw8": "qwen3:8b",
            "query_router": "qwen3:1.7b",
            "intent_classifier": "qwen3:1.7b"
        }
        return model_map

    def render_prompt(self, template: PromptTemplate, **kwargs) -> str:
        missing = set(template.required_fields) - set(kwargs.keys())
        if missing:
            logger.warning(f"Missing required fields for prompt '{template.name}': {missing}")
            return ""
        # Safely handle templates that contain literal JSON-like braces (e.g. {"is_question":bool})
        # Escape all braces first, then un-escape placeholders we actually want to format.
        raw = template.template
        safe = raw.replace("{", "{{").replace("}", "}}")

        # Fields we should keep as real placeholders: required_fields + provided kwargs keys
        placeholder_keys = list(template.required_fields) + list(kwargs.keys())
        # Deduplicate while preserving order
        seen = set()
        keys = [k for k in placeholder_keys if not (k in seen or seen.add(k))]

        for key in keys:
            if not isinstance(key, str) or key == "":
                continue
            # Replace the escaped placeholder {{key}} back to {key}
            safe = safe.replace("{{" + key + "}}", "{" + key + "}")

        try:
            return safe.format(**kwargs)
        except Exception as exc:
            logger.exception(f"Failed to render prompt '{template.name}': {exc}")
            return ""
    
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
        
