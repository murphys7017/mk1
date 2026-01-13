from __future__ import annotations

from DataClass.PromptTemplate import PromptTemplate
from tools.PromptBuilder import PromptBuilder


class SystemPrompt:
    def __init__(self):
        self.prompt_map: dict[str, PromptTemplate] = {}
        self.load_template()

    def load_template(self):
        # ========== 1) split_buffer_by_topic_continuation ==========
        self.prompt_map["split_buffer_by_topic_continuation"] = PromptTemplate(
            name="split_buffer_by_topic_continuation",
            template=SystemPrompt.split_buffer_by_topic_continuation_builder().build(),
            required_fields=["current_summary", "dialogue_turns"],
            output_schema={"continuation_turns": "int"},
        )

        # ========== 2) text_analysis ==========
        self.prompt_map["text_analysis"] = PromptTemplate(
            name="text_analysis",
            template=SystemPrompt.text_analysis_builder().build(),
            required_fields=["input"],
            output_schema={
                "is_question": "bool",
                "is_self_reference": "bool",
                "mentioned_entities": "list[str]",
                "emotional_cues": "list[str]",
            },
        )

        # ========== 3) judge_dialogue_summary ==========
        self.prompt_map["judge_dialogue_summary"] = PromptTemplate(
            name="judge_dialogue_summary",
            template=SystemPrompt.judge_dialogue_summary_builder().build(),
            required_fields=["summary_text", "dialogues_text"],
            output_schema={
                "need_summary": "bool",
                "summary_action": "str",  # merge | new | none
            },
        )

        # ========== 4) summarize_dialogue ==========
        # 注意：这里我给的是“严格协议版”：
        # - new -> summary_id 必须为 null
        # - update -> summary_id 必须引用已有摘要里的某个 id
        # 你代码里已经会 int() 强转/处理 None，这样最对齐。:contentReference[oaicite:3]{index=3}
        self.prompt_map["summarize_dialogue"] = PromptTemplate(
            name="summarize_dialogue",
            template=SystemPrompt.summarize_dialogue_builder().build(),
            required_fields=["summary_text", "dialogues_text"],
            output_schema={
                "action": "str",          # update | new
                "summary_id": "str",      # 兼容旧解析器：new 时要求输出 null；update 时输出数字字符串
                "summary_content": "str",
            },
        )

        # ========== 5) judge_chat_state ==========
        self.prompt_map["judge_chat_state"] = PromptTemplate(
            name="judge_chat_state",
            template=SystemPrompt.judge_chat_state_builder().build(),
            required_fields=["dialogue_turns"],
            output_schema={
                "interaction": "str",
                "user_attitude": "str",
                "emotional_state": "str",
                "leading_approach": "str",
            },
        )

        # ========== 6) RESPONSE_PROTOCOL ==========
        # 这里保留 lines：DefaultGlobalContextAssembler 会逐行 add 到 <RESPONSE_PROTOCOL> tag 里。
        resp_lines = [
            "你将接收到一些结构化上下文。",
            "它们仅用于你理解情况。",
            "",
            "【绝对规则】",
            "- 你的回复必须是纯自然语言",
            "- 不得包含任何 XML、标签、结构化内容",
            "- 不得重复或模仿输入格式",
            "- 直接像真人一样说话",
        ]
        self.prompt_map["RESPONSE_PROTOCOL"] = PromptTemplate(
            name="RESPONSE_PROTOCOL",
            template="\n".join([ln for ln in resp_lines if ln is not None]).strip(),
            required_fields=[],
            output_schema={},
            lines=resp_lines,
        )

    def getPrompt(self, prompt_name: str) -> PromptTemplate:
        return self.prompt_map[prompt_name]

    # -------------------- model selectors (保持你原本风格) --------------------
    @staticmethod
    def split_buffer_by_topic_continuation_model():
        return "qwen3:1.7b"

    # ==================== Builders (v3) ====================

    @staticmethod
    def split_buffer_by_topic_continuation_builder() -> PromptBuilder:
        """
        A 方案：输出 continuation_turns（数量，不是索引）。
        """
        b = PromptBuilder()

        b.add("你是一个对话连贯性分析器。")

        b.add(
            "任务：给定【已有摘要】与【新对话轮次】，判断新对话中“从第0轮开始”有多少轮仍在延续已有摘要的话题。"
        )
        b.add("注意：只统计连续的前缀轮次；一旦某一轮明显转到新话题，必须停止计数。")

        b.add("【已有摘要】")
        b.add("{current_summary}")

        b.add("【新对话轮次】（从第0轮开始编号）")
        b.add("{dialogue_turns}")

        b.add("判定规则（严格执行）：")
        b.add("- continuation_turns = 从第0轮开始连续延续同一话题的轮数（数量，不是索引）。")
        b.add("- 若第0轮就不延续已有摘要话题，则 continuation_turns = 0。")
        b.add("- 只要出现新话题/新目标/新问题且不依赖已有摘要上下文，就视为“话题断开”。")
        b.add("- 若一轮同时包含旧话题和新话题：只要新话题占主导，就视为断开。")

        b.add("输出要求：")
        b.add('- 只输出一个 JSON 对象：{{"continuation_turns": x}}')
        b.add("- 不要输出任何其他文字、空格、换行、注释或 markdown。")
        b.add("- x 为整数，满足 0 ≤ x ≤ 新对话轮次总数。")

        return b

    @staticmethod
    def text_analysis_builder() -> PromptBuilder:
        """
        轻量文本分析：是否问题/自指/实体/情绪线索
        """
        b = PromptBuilder()
        b.add("你是一个文本分析器。")
        b.add("任务：对输入文本进行轻量结构化分析，输出 JSON。")
        b.add("输入：")
        b.add("{input}")
        b.add("输出字段：")
        b.add(
            '只输出 JSON：{{"is_question":bool,"is_self_reference":bool,"mentioned_entities":list[str],"emotional_cues":list[str]}}'
        )
        b.add("不要输出任何解释。")
        return b

    @staticmethod
    def judge_dialogue_summary_builder() -> PromptBuilder:
        b = PromptBuilder()
        b.add("你是一个【对话记忆裁判系统】。")
        b.add("任务：判断最近对话是否需要摘要，并给出 summary_action：merge/new/none。")
        b.add("原则：不创作、不补充细节、不解释原因。只输出 JSON。")

        b.add("【已有摘要】")
        b.add("{summary_text}")
        b.add("【最近对话】")
        b.add("{dialogues_text}")

        b.add("输出要求：")
        b.add('只输出 JSON：{{"need_summary": true|false, "summary_action": "merge"|"new"|"none"}}')
        b.add("不要输出任何其他文字。")
        return b

    @staticmethod
    def summarize_dialogue_builder() -> PromptBuilder:
        """
        严格版：new -> summary_id=null；update -> summary_id 必须来自已有摘要列表。
        这样与“数据库生成新 id”的实现完全对齐。
        """
        b = PromptBuilder()

        b.add("你是一个【阶段性对话摘要系统】。")
        b.add("任务：把【未摘要对话】压缩成一条可长期保存的客观摘要，并决定 update 或 new。")
        b.add("必须遵守：不编造、不过度推断、不添加未出现的信息；不得逐句复述；第三人称、客观中性、简洁。")

        b.add("—— 输出协议（必须严格执行）——")
        b.add("你必须输出且仅输出一个 JSON 对象，包含字段：")
        b.add('{{ "action": "update"|"new", "summary_id": <整数或 null>, "summary_content": "<完整摘要>" }}')
        b.add('约束1：action="new" 时，summary_id 必须为 null（由系统/数据库生成新 id）。')
        b.add('约束2：action="update" 时，summary_id 必须来自【已有摘要】中出现过的某个整数 id（原样返回，不能创造）。')
        b.add("约束3：summary_content 必须是“完整摘要”（不是增量补丁），建议 1~6 句。")

        b.add("—— 判定规则 ——")
        b.add("何时 update：未摘要对话主要在延续/补充/修正某条已有摘要的同一主题/阶段。")
        b.add("何时 new：明显开启新主题/新阶段，或与任何已有摘要无关，或【已有摘要为空】。")

        b.add("—— 内容要求（仅当明确出现时才写入）——")
        b.add("- 稳定主题/项目/任务")
        b.add("- 明确偏好或否定")
        b.add("- 明确目标、约定、未完成事项")
        b.add("- 重要关系变化或长期设定（仅当明确出现）")
        b.add("- 持续多轮体现的稳定情绪倾向（仅当多轮明显且稳定）")

        b.add("—— 必须避免 ——")
        b.add("- 调侃、角色扮演语气、临时情绪玩笑")
        b.add("- 预测未来、推测动机")
        b.add("- 输出对话原句、XML、markdown、代码块")

        b.add("【已有摘要】")
        b.add("{summary_text}")
        b.add("【未摘要对话】")
        b.add("{dialogues_text}")

        b.add("只输出 JSON 对象，不要包含任何其他文字、空格、换行或注释。")
        return b

    @staticmethod
    def judge_chat_state_builder() -> PromptBuilder:
        b = PromptBuilder()
        b.add("你是一个对话状态判定器。")
        b.add("任务：根据对话内容输出当前对话状态 JSON。")
        b.add("【对话】")
        b.add("{dialogue_turns}")
        b.add("只输出 JSON，字段：")
        b.add(
            '{{"interaction": "...", "user_attitude": "...", "emotional_state": "...", "leading_approach": "..."}}'
        )
        b.add("不要输出任何解释。")
        return b
