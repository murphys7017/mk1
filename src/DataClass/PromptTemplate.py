from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PromptTemplate:
    name: str
    template: str
    required_fields: list[str]
    output_schema: dict
    lines: list[str] = field(default_factory=list)
