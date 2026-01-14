from functools import lru_cache
import os
import asyncio
from Transport.ws_server import start_ws_server, stop_ws_server
from ltp import LTP
from src.Alice import Alice
from dotenv import load_dotenv
load_dotenv()
api_key = os.environ.get("OPENAI_API_KEY") 

@lru_cache(maxsize=1)
def load_stopwords(file_path: str) -> set[str]:
        """
        加载停用词文件，自动缓存（只读一次）
        """
        stopwords = set()

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip()
                if w:
                    stopwords.add(w)

        return stopwords
async def main():

    if api_key is None:
        raise ValueError("请设置环境变量 OPENAI_API_KEY")


    ltp = LTP(r"src\PerceptionSystem\ltp\base")
    STOPWORDS = load_stopwords(r"src\PerceptionSystem\ltp\base\stopwords_full.txt")




    alice = Alice(ltp=ltp, ltp_stopwords=STOPWORDS)

    # server = await start_ws_server(alice, host='0.0.0.0', port=8765)
    # try:
    #     await asyncio.Future()  # 或者其它你的主循环
    # finally:
    #     await stop_ws_server(server)


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