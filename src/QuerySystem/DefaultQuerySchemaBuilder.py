from __future__ import annotations

from typing import Any, List, Optional

from DataClass.ChatMessage import ChatMessage
from DataClass.QuerySchema import QuerySchema
from QuerySystem.QuerySchemaBuilderAbstract import QuerySchemaBuilderAbstract
from QuerySystem.QueryPropertyBuilderAbstract import QueryPropertyBuilderAbstract

# 直接 import 你要用的 builders
from QuerySystem.SignalDensityJudge import SignalDensityJudge
from QuerySystem.IntentJudge import IntentJudgeL


class DefaultQuerySchemaBuilder(QuerySchemaBuilderAbstract):
    def __init__(
        self,
        **kwargs
    ):

        # 1) 直接 new：你想用哪些就写哪些
        builders: List[QueryPropertyBuilderAbstract] = [
            SignalDensityJudge(**kwargs),
            IntentJudgeL(**kwargs),
            # 以后你加别的：直接在这儿 append
            # ModeJudge(...),
            # QueryTextBuilder(...),
        ]

        # 2) 按 priority 排序（越小越先）
        builders.sort(key=lambda b: b.getPriority())
        self.property_builders = builders

    def build_query_schema(self, msg: ChatMessage) -> QuerySchema:
        schema = QuerySchema()

        # 可选：把 reason 收集进 debug_tags

        for b in self.property_builders:
            try:
                props = b.buildProperty(msg)
            except Exception as e:
  
                continue

            for item in props:
                # item: ("k", v) 或 ("k", v, reason)
                if not isinstance(item, tuple) or len(item) not in (2, 3):
                    continue

                key, val = item[0], item[1]
                reason = item[2] if len(item) == 3 else None

                if hasattr(schema, key):
                    setattr(schema, key, val)
                else:
                    # 不存在的属性，跳过
                    continue

        return schema
