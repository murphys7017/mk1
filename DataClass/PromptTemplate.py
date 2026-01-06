from dataclasses import dataclass


@dataclass
class PromptTemplate:
    name: str
    template: str
    required_fields: list[str]
    output_schema: dict
