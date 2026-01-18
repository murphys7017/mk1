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
        # SystemPrompt.py (inside load_template)
        self.prompt_map["motion_intent"] = PromptTemplate(
            name="motion_intent",
            template=SystemPrompt.motion_intent_builder().build(),
            required_fields=["analyze_block", "base_motion_list"],
            output_schema={
                "base_motion": "str",
                "duration": "float",
                "emotion": "str",
                "intensity": "float",
                "speaking": "bool",
                "energy": "float",
                "blink_at": "list[float]",
                "beats": "list[dict]",
                "gaze": "dict",
                "loop": "bool",
            },
        )
        # ========== 7) query_router ==========
        # 轻量路由器：只做 intent/source/mode/topk/ttl/token_budget 的“建议”
        # 注意：低信号闸门仍应在系统侧规则执行，LLM 不得推翻 hard gate。
        self.prompt_map["query_router"] = PromptTemplate(
            name="query_router",
            template=SystemPrompt.query_router_builder().build(),
            required_fields=["router_input"],
            output_schema={
                "intent": "str",
                "confidence": "float",
                "retrieve": "bool",
                "source_plans": "list[dict]",
                "routing_tags": "list[str]",
                "token_budget": "int",
                "reasons": "dict",
            },
        )
        self.prompt_map["intent_classifier"] = PromptTemplate(
            name="intent_classifier",
            template=SystemPrompt.intent_classifier_builder().build(),
            required_fields=["router_input"],
            output_schema={
                "intent": "str",
                "confidence": "float",
                "evidence": "dict",
            },
        )


    @staticmethod
    def query_router_model():
        # 你可以换成更小更快的模型，只要能稳定输出严格 JSON
        return "qwen3:1.7b"
    @staticmethod
    def query_router_builder() -> PromptBuilder:
        """
        Query Router: 只做“路由决策建议”，不做检索、不拼 prompt。
        输入 router_input（JSON 字符串），输出严格 JSON（不允许额外文字）。
        """
        b = PromptBuilder()
        b.add("你是一个【检索路由器】。")
        b.add("任务：根据输入的 router_input（JSON），输出一份检索计划建议（严格 JSON）。")
        b.add("")
        b.add("【重要约束】")
        b.add("- 你必须只输出一个 JSON 对象，不能输出任何其他文字、空格、换行、注释或 markdown。")
        b.add("- 不要编造来源：sources 只能从 allowed_sources 里选。")
        b.add("- world_core 永远不作为 source（它是系统固定注入的 must_include）。")
        b.add("- 如果输入显示 low-signal（很短且无关键词/实体/frames），必须设置 retrieve=false 且 source_plans=[].")
        b.add("- 如果使用 env 作为 source，则必须为该 source 提供 ttl_seconds（建议 120）。")
        b.add("- 优先 keyword 模式以保证速度；仅 knowledge_lookup 场景推荐 hybrid（keyword 粗筛 + vector rerank）。")
        b.add("- 除非 intent=user_memory，否则不要选择 user_profile。")
        b.add("")
        b.add("【输入 router_input】")
        b.add("{router_input}")
        b.add("")
        b.add("【输出 JSON 结构】")
        b.add(
            '{{'
            '"intent": "ping_presence|general_conversation|clarify|world_background|environment_status|knowledge_lookup|user_memory|unknown",'
            '"confidence": 0.0,'
            '"retrieve": true,'
            '"routing_tags": ["topic:chat|topic:architecture|topic:env|topic:knowledge|topic:user"],'
            '"token_budget": 512,'
            '"source_plans": ['
            '  {{'
            '    "name": "short_term|mid_term|long_term|user_profile|world_bg|env|kb",'
            '    "ttl_seconds": null,'
            '    "specs": ['
            '      {{'
            '        "q": "string",'
            '        "mode": "keyword|vector|hybrid|llm",'
            '        "tags": ["topic:..."],'
            '        "filters": {{}},'
            '        "top_k": 5,'
            '        "min_score": null,'
            '        "rerank": false'
            '      }}'
            '    ]'
            '  }}'
            '],'
            '"reasons": {{"marker_hits": [], "notes": ""}}'
            '}}'
        )
        return b


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

    @staticmethod
    def motion_intent_builder() -> PromptBuilder:
        b = PromptBuilder()
        b.add("你是 Live2D 动作意图抽取器。")
        b.add("输入：AnalyzeResult（结构化分析）+ 候选基础 motion 文件名列表。")
        b.add("输出：一个 JSON 对象（intent.json），用于后续合成临时 motion3.json。")

        b.add("【硬性要求】")
        b.add("- 只输出一个 JSON 对象，不要输出任何解释、不要 markdown、不要多余文本。")
        b.add("- base_motion 必须从候选列表中选择一个（精确字符串匹配）。")
        b.add("- 允许缺字段：缺失字段由系统默认填充。")

        b.add("【候选基础 motion 列表】")
        b.add("{base_motion_list}")

        b.add("【AnalyzeResult】")
        b.add("{analyze_block}")

        b.add("【输出 JSON 格式】")
        b.add(
            '{{'
            '"base_motion": string,'
            '"duration": number,'
            '"emotion": "neutral|happy|sad|angry|surprised|shy|thinking",'
            '"intensity": number,'
            '"speaking": boolean,'
            '"energy": number,'
            '"blink_at": number[],'
            '"beats": [{{"t": number, "type": "emphasis"}}],'
            '"gaze": {{"x": number, "y": number}},'
            '"loop": boolean'
            '}}'
        )
        return b
    # 同时加 model 选择（保持一致风格）
    @staticmethod
    def intent_classifier_model():
        return "qwen3:1.7b"

    @staticmethod
    def intent_classifier_builder() -> PromptBuilder:
        b = PromptBuilder()

        # 角色与目标
        b.add("你是一个【意图分类器】。")
        b.add("任务：仅根据 router_input 中提供的 intents（每个 intent 的 keywords/examples），为 text 选择一个最匹配的 intent.name。")
        b.add("你不得使用外部知识，不得发明新的意图。")
        b.add("")

        # 强约束：输出格式
        b.add("【输出硬性要求】")
        b.add("- 你必须只输出一个 JSON 对象，且必须是单行输出。")
        b.add("- 不要输出任何其他文字、解释、空格、换行、注释、markdown。")
        b.add('- 输出字段只能包含：{"intent":..., "confidence":...}，不得包含其他字段。')
        b.add("- intent 必须从 router_input.allowed_intents 中选择一个；且必须等于 router_input.intents[].name 中的某一项（或 unknown）。")
        b.add("- confidence 为 0.0~1.0 的小数；若不确定或候选很接近，降低 confidence。")
        b.add("")

        # 输入结构（关键：讲清层级）
        b.add("【router_input 结构说明】")
        b.add("router_input 是一个 JSON 字符串，包含字段：")
        b.add("- text: 当前用户输入文本")
        b.add("- allowed_intents: 允许输出的 intent 名称列表（白名单）")
        b.add("- intents: 候选意图数组，每个元素包含：")
        b.add('  - name: intent 名称（字符串）')
        b.add('  - keywords: 关键词列表（list[str]）')
        b.add('  - examples: 示例句列表（list[str]）')
        b.add('  - priority: 数字，越大表示越优先（用于同分/接近时裁决，可选）')
        b.add("")

        # 判定准则（让小模型知道怎么对齐）
        b.add("【判定准则（严格执行）】")
        b.add("1) 优先匹配 keywords：text 中出现 keywords 越多越相关。")
        b.add("2) 再匹配 examples：text 与某个 example 语义越接近越相关。")
        b.add("3) 若多个 intent 很接近：选择 priority 更高的那个。")
        b.add('4) 若 text 很短、信息不足或无法匹配：输出 intent="unknown" 且 confidence <= 0.35。')
        b.add("")

        # 证据字段（可选但很有用）
        b.add("【evidence 字段要求】")
        b.add("- keyword_hits：列出你认为命中的关键词（最多 6 个）")
        b.add("- best_example：列出最接近的一条 example 原文（最多 1 条）")
        b.add("- notes：一句话说明选择理由（尽量短）")
        b.add("")

        # 输入
        b.add("【输入 router_input】")
        b.add("{router_input}")
        b.add("")

        # 输出模板（固定骨架，减少模型发挥空间）
        b.add("【输出 JSON（必须严格遵守字段与格式）】")
        b.add('{{"intent":"unknown","confidence":0.0,}}')
        return b
