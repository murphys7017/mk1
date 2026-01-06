import os
from Alice import Alice
from dotenv import load_dotenv
load_dotenv()
api_key = os.environ.get("OPENAI_API_KEY") 

async def main():
    from Agent.QwenClient import QwenClient
    if api_key is None:
        raise ValueError("请设置环境变量 OPENAI_API_KEY")

    client = QwenClient(api_key)

    alice = Alice(client=client)

    while True:
        user_input = input("你: ")
        if user_input.lower() == "退出":
            print("再见！")
            break
        response = await alice.respond({"text": user_input})
        print("爱丽丝: " + response)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())