from DataClass.PromptTemplate import PromptTemplate


class SystemPrompt:

    def __init__(self):
        self.prompt_map = {}
        self.load_template()

    def load_template(self):
        self.prompt_map['split_buffer_by_topic_continuation'] = PromptTemplate(
            name='split_buffer_by_topic_continuation',
            template=SystemPrompt.split_buffer_by_topic_continuation_prompt(),
            required_fields=["current_summary", "dialogue_turns"],
            output_schema={"continuation_turns": "int"}
        )
        self.prompt_map['text_analysis'] = PromptTemplate(
            name='text_analysis',
            template=SystemPrompt.text_analysis_prompt(),
            required_fields=["input"],
            output_schema={
                "is_question": "bool",
                "is_self_reference": "bool",
                "mentioned_entities": "list[str]",
                "emotional_cues": "list[str]"
            }
        )
        self.prompt_map['judge_dialogue_summary'] = PromptTemplate(
            name='judge_dialogue_summary', 
            template=SystemPrompt.judge_dialogue_summary_prompt(),
            required_fields=["summary_text", "dialogues_text"],
            output_schema={
                "need_summary": "bool",
                "summary_action": "str"
            }
        )
        self.prompt_map['summarize_dialogue'] = PromptTemplate(
            name='summarize_dialogue',
            template=SystemPrompt.summarize_dialogue_prompt(),
            required_fields=["summary_text", "dialogues_text"],
            output_schema={
                            "action": "str",
                            "summary_id": "int|null",
                            "summary_content": "str"
                            }
        )
        self.prompt_map['judge_chat_state'] = PromptTemplate(
            name='judge_chat_state',
            template=SystemPrompt.judgeChatStatePrompt(),
            required_fields=["dialogue_turns"],
            output_schema={
                "interaction": "str",
                "user_attitude": "str",
                "emotional_state": "str",
                "leading_approach": "str"
            }
        )
        self.prompt_map['RESPONSE_PROTOCOL'] = PromptTemplate(
            name='RESPONSE_PROTOCOL',
            template="""
                    你将接收到一些结构化上下文。
                    它们仅用于你理解情况。

                    【绝对规则】
                    - 你的回复必须是纯自然语言
                    - 不得包含任何 XML、标签、结构化内容
                    - 不得重复或模仿输入格式
                    - 直接像真人一样说话
                    """.strip(),
            required_fields=[],
            output_schema={},
            lines=[
                "你将接收到一些结构化上下文。",
                "它们仅用于你理解情况。",
                "【绝对规则】",
                "- 你的回复必须是纯自然语言",
                "- 不得包含任何 XML、标签、结构化内容",
                "- 不得重复或模仿输入格式",
                "- 直接像真人一样说话"
            ]
        )
    def getPrompt(self, prompt_name: str) -> PromptTemplate:
        return self.prompt_map[prompt_name]
        

    @staticmethod
    def split_buffer_by_topic_continuation_model():
        return "qwen3:1.7b"
    @staticmethod
    def split_buffer_by_topic_continuation_prompt():
        return """
你是一个对话连贯性分析器。

任务：给定【已有摘要】与【新对话轮次】，判断新对话中“从第0轮开始”有多少轮仍然在延续已有摘要的话题。
注意：只统计“连续的前缀轮次”，一旦某一轮开始明显转到新话题，就必须停止计数。

【已有摘要】
{current_summary}

【新对话轮次】（从第0轮开始编号）
{dialogue_turns}

判定规则（严格执行）：
- continuation_turns = 从第0轮开始，连续延续同一话题的轮数（数量，不是索引）。
- 若第0轮就不延续已有摘要话题，则 continuation_turns = 0。
- 只要出现新话题/新目标/新问题且不依赖已有摘要上下文，就视为“话题断开”，后面的轮次不再计入。
- 如果一轮内容同时包含旧话题和新话题：只要新话题占主导，就视为断开。

输出要求：
- 只输出一个 JSON 对象
- 不要输出任何解释、额外文本、空格、换行、注释、markdown

输出格式：
{{"continuation_turns": x}}
其中 x 为整数，满足 0 ≤ x ≤ 新对话轮次总数。
"""
    @staticmethod
    def text_analysis_model():
        return "qwen3:1.7b"
    @staticmethod
    def text_analysis_prompt():
        return """
        你是一个客观的文本观察器。请严格根据用户输入的字面内容，回答以下问题：

        1. 是否包含明确的问题（包括疑问句、反问句、设问句）？是 / 否。
        2. 是否提及“你”、“您”、“爱丽丝”或“AI”？是 / 否。
        3. 出现了哪些表达情绪或态度的词语？（如“讨厌”、“希望”、“烦”、“太棒了”）

        仅输出 JSON，不要任何解释或额外文本。使用以下格式：

        {{
        "is_question": true,
        "is_self_reference": false,
        "emotional_cues": ["词1", "词2", "词3"]
        }}

        用户输入：{input}
        """
    @staticmethod
    def judge_dialogue_summary_model():
        return "qwen3:1.7b"
    @staticmethod
    def judge_dialogue_summary_prompt():
        return """
你是一个【对话记忆裁判系统】。

你的任务不是生成对话内容，
而是判断「最近的对话是否需要被摘要，以及应如何处理」。

你必须遵守：
- 不进行创作
- 不补充细节
- 不做情绪渲染
- 不解释原因
- 只返回 JSON

你将收到：
1. 已有摘要（可能为空）
2. 尚未摘要的最近对话列表

你需要判断：
- 是否需要生成摘要
- 如果需要：
  - 是合并到已有摘要（merge）
  - 还是生成新的摘要（new）
- 如果不需要摘要，明确返回 none

判断依据：
- 是否出现新的长期话题
- 是否出现稳定偏好、关系变化、目标、承诺
- 是否只是闲聊、玩笑、短期问答或角色调侃

返回格式必须严格如下：
{
  "need_summary": true | false,
  "summary_action": "merge" | "new" | "none"
}

【已有摘要】
{summary_text}

【最近对话】
{dialogues_text}
"""
    
    @staticmethod
    def summarize_dialogue_model():
        return "qwen3:4b"
    @staticmethod
    def summarize_dialogue_prompt():
        return """
你是一个【阶段性对话摘要系统】。

你的任务是把“未摘要对话片段”压缩成一条可长期保存的客观摘要，并决定：
- 这是更新某条已有摘要（update）
- 还是创建一条新摘要（new）

你必须遵守：
- 不编造、不过度推断、不添加未出现的信息
- 不保留原对话原文（不要逐句复述）
- 使用第三人称、客观中性、简洁
- 只输出 JSON，不要任何解释或额外文本

你将收到：
1) 【已有摘要】列表（可能为空），格式为多行：
- [summary_id]123:[summary_content]...
2) 【未摘要对话】（本次需要压缩的对话片段）

—— 关键判定规则 ——
A. 何时选择 update：
- 未摘要对话主要是在“延续/补充/修正”已有摘要中的同一主题/阶段
- 例如：同一个项目/同一个决定/同一条偏好/同一段计划的推进
- 选择 update 时：你必须从【已有摘要】里选择且仅选择一条 summary_id 来更新

B. 何时选择 new：
- 未摘要对话明显开启了新的主题/阶段
- 或与任何已有摘要都不属于同一主题
- 或【已有摘要为空】
- 选择 new 时：summary_id 必须为 null（由系统/数据库生成新 id）

—— 输出字段约束（必须严格执行） ——
你必须输出且仅输出一个 JSON 对象，包含以下字段：
{
  "action": "update" | "new",
  "summary_id": <整数或 null>,
  "summary_content": "<更新后的完整摘要内容>"
}

约束 1：当 action = "new" 时，summary_id 必须是 null。
约束 2：当 action = "update" 时，summary_id 必须是【已有摘要】中出现过的某一个整数 id（原样返回，不要修改、不要创造）。
约束 3：summary_content 必须是“完整摘要”（不是增量补丁），长度建议 1~6 句，内容以事实为主。

—— 内容要求（仅当明确出现时才写入） ——
- 稳定讨论的主题/项目/任务
- 明确的用户偏好或否定
- 明确的目标、约定、未完成事项
- 重要的关系变化或长期设定（如果明确出现）
- 持续多轮体现的情绪倾向（仅当多轮明显且稳定）

—— 必须避免 ——
- 调侃、角色扮演语气、临时情绪玩笑
- 预测未来、推测动机
- 不要输出对话原句
- 不要输出 XML / markdown / 代码块

【已有摘要】
{summary_text}

【未摘要对话】
{dialogues_text}

只输出 JSON 对象，不要包含任何其他文字、空格、换行或注释。
        """


    @staticmethod
    def judgeChatStateModel():
        return "qwen3:1.7b"
    @staticmethod
    def judgeChatStatePrompt():
        return """
你是一个对话状态分析器。请根据以下对话，判断当前的互动状态。

【最近对话】
{dialogue_turns}

返回格式必须严格如下：
	{{
		"interaction": "闲聊" | "问答" | "角色扮演" | "信息提供" | "任务协助" | "其他",
		"user_attitude": "积极" | "中立" | "消极",
		"emotional_state": "平静" | "激动" | "沮丧" | "愉快" | "紧张" | "其他",
		"leading_approach": "用户主导" | "AI主导" | "平等互动"
	}}
"""