from __future__ import annotations

from DataClass.PromptTemplate import PromptTemplate
from tools.PromptBuilder import PromptBuilder
import yaml
import textwrap
from pathlib import Path


class SystemPrompt:
    def __init__(self):
        self.prompt_map: dict[str, PromptTemplate] = {}
        self.load_template()

    def load_template(self):
        # Try to load from YAML first; fall back to builders when missing
        yaml_path = Path(__file__).resolve().parents[1] / "config" / "system_prompt.yaml"
        if yaml_path.exists():
            try:
                raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
                prompts = raw.get("prompts", {})
                for key, p in prompts.items():
                    name = p.get("name", key)
                    template = p.get("template", "")
                    # normalize indentation
                    template = textwrap.dedent(template).strip()
                    required_fields = p.get("required_fields", [])
                    output_schema = p.get("output_schema", {})
                    lines = p.get("lines", []) or []
                    self.prompt_map[name] = PromptTemplate(
                        name=name,
                        template=template,
                        required_fields=required_fields,
                        output_schema=output_schema,
                        lines=lines,
                    )
                # If loaded from YAML, return early
                if self.prompt_map:
                    return
            except Exception:
                # on any YAML error, fallback to original builders
                pass
    def getPrompt(self, prompt_name: str) -> PromptTemplate:
        return self.prompt_map[prompt_name]