from openai import OpenAI


class QwenClient:
    def __init__(self, api_key: str):
        self.model = "qwen-plus"
        self.temperature = 1.2
        self.top_p = 0.7
        self.chat_history_limit = 10
        self.chat_list = []

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    
    def respond(self, messages):
        """
        生成对用户输入的响应，负责语言模型的交互
        """
        completion = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            top_p=self.top_p,
            messages=messages
        )

        response = completion.choices[0].message.content

        return response