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

请回答：最多前几轮属于同一话题？（若第1轮就切换，回答0；若全部延续，回答总轮数）

只输出一个整数x，{"index": x }，不要任何其他文字。
x必须是一个非负整数，且不能大于新对话轮次的总数。

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
你是一个对话记忆裁判系统。

你的任务不是生成对话内容，
而是判断「最近的对话是否需要被摘要，以及如何处理」。

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
- 如果需要，是合并到已有摘要，还是生成新的摘要

判断依据：
- 是否出现新的长期话题
- 是否出现稳定偏好、关系变化、目标、承诺
- 是否只是闲聊 / 短期问答

返回格式必须严格如下：
{
  "need_summary": true | false
}

        """
    
    @staticmethod
    def summarize_dialogue_model():
        return "qwen3:1.7b"
    @staticmethod
    def summarize_dialogue_prompt():
        return """
你是一个长期记忆摘要系统。

你的任务是将多轮对话压缩为一段「可长期保存的记忆」。

摘要要求：
- 如果【已有摘要】不为空，则在此基础上更新和扩展
- 使用第三人称
- 不使用修辞
- 不编造未出现的信息
- 不包含对话原文
- 保留以下内容（如存在）：
  - 稳定话题
  - 用户偏好
  - 关系变化
  - 明确目标或承诺
  - 情绪倾向（仅在明显时）

风格要求：
- 中性
- 简洁
- 可被未来系统直接使用
        """
