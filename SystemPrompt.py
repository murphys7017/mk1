class SystemPrompt:
    @staticmethod
    def split_buffer_by_topic_continuation_model():
        return "qwen3:1.7b"
    @staticmethod
    def split_buffer_by_topic_continuation_prompt():
        return """
你是一个对话连贯性分析器。请判断新对话轮次中有多少轮延续了已有摘要的话题。

【已有摘要】
{current_summary}

【新对话轮次】（从第0轮开始编号）
{dialogue_turns}

请回答：最多前几轮属于同一话题？
请严格按以下规则作答：
- 判断从第0轮开始，最多连续多少轮属于与已有摘要相同的话题。
- 返回一个非负整数 x，满足 0 ≤ x ≤ 新对话轮次总数。

只输出一个 JSON 对象，格式为：
{{"index": x}}
不要包含任何其他文字、空格、换行、注释或 markdown。

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
        3. 提到了哪些具体实体或主题词？（如人名、地点、事物、概念，例如：“下雨天”、“Python”、“昨天的会议”）
        4. 出现了哪些表达情绪或态度的词语？（如“讨厌”、“希望”、“烦”、“太棒了”）

        仅输出 JSON，不要任何解释或额外文本。使用以下格式：

        {
        "is_question": true,
        "is_self_reference": false,
        "mentioned_entities": ["词1", "词2"],
        "emotional_cues": ["词3"]
        }

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
/no-thoughts
/no-thinking
/no_thinking
        """
    
    @staticmethod
    def summarize_dialogue_model():
        return "qwen3:4b"
    @staticmethod
    def summarize_dialogue_prompt():
        return """
你是一个【阶段性对话摘要系统】。

你的任务是：
在对话达到一个自然阶段结束点时，
将该阶段的对话内容压缩为一条【可长期保存的事实性摘要】，
用于替代原始对话记录。

【重要规则】
- 本摘要用于“对话历史压缩”，不是人格或状态判断
- 只记录已经发生且不会改变的事实
- 不推断未来行为
- 不预测用户意图
- 不保留互动语气或角色扮演风格

【关于已有摘要】
- 如果【已有摘要】存在，且当前对话仍属于同一主题阶段：
  - 在已有摘要上进行补充
- 如果当前对话已明显进入新主题或新阶段：
  - 生成一条新的摘要
  - 不修改旧摘要

【必须保留的信息（仅当明确出现）】
- 讨论过的稳定主题
- 明确表达的用户偏好或否定
- 明确发生的关系变化（如信任、对立）
- 明确的目标、约定或未完成事项
- 明显且持续的情绪倾向（仅当多轮体现）

【必须避免】
- 不记录调侃、语气、角色扮演细节
- 不记录临时情绪或玩笑
- 不包含任何对话原文
- 不编造未出现的信息

【输出要求】
- 使用第三人称
- 中性、客观、简洁
- 一段自然语言
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