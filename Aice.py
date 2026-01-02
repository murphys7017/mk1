from openai import OpenAI
from PerceptionSystem import PerceptionSystem
from MemorySystem import MemorySystem

class Alice:
    def __init__(self, api_key: str):
        self.memory_system = MemorySystem()
        self.perception_system = PerceptionSystem()

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        self.model = "qwen-flash"
        self.temperature = 1.2
        self.top_p = 0.7
        self.chat_history_limit = 10
        self.chat_list = []

    def respond(self, user_input: str) -> str:
        user_input = self.perception_system.analyze(user_input)
        self.chat_list.append({"role": "user", "content": user_input})


        completion = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            top_p=self.top_p,
            messages=self.memory_system.build_message(self.chat_list)
        )

        response = completion.choices[0].message.content
        self.messages.append({"role": "assistant", "content": response})

        return response
