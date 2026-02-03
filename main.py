from dotenv import load_dotenv
# load environment variables before configuring logging
load_dotenv()

# ensure centralized logging is configured early (after env vars loaded)
from src import logging_config  # noqa: F401

from dataclasses import dataclass
from functools import lru_cache
import os
import asyncio
from Transport.ws_server import start_ws_server, stop_ws_server
from ltp import LTP
from src.Alice import Alice

api_key = os.environ.get("OPENAI_API_KEY") 
ltp_path = os.environ.get("LTP_PATH", r"src\PerceptionSystem\ltp\base")
stop_words_path = os.environ.get("STOPWORDS_PATH", r"src\PerceptionSystem\ltp\base\stopwords_full.txt")

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
@dataclass
class Config:
     db_path = "chat_history.db"
     db_echo = False
     history_window = 20
     dialogue_window = 4
     min_raw_for_summary = 4
     ltp_path = ltp_path
     stop_words_path = stop_words_path
     min_raw_for_summary = 4
     analysis_window = 3


async def main():

    if api_key is None:
        raise ValueError("请设置环境变量 OPENAI_API_KEY")


    ltp = LTP(Config.ltp_path)
    STOPWORDS = load_stopwords(stop_words_path)




    alice = Alice(
        ltp=ltp, 
        ltp_stopwords=STOPWORDS,
        db_path = Config.db_path,
        db_echo= Config.db_echo,
        history_window = Config.history_window,
        dialogue_window = Config.dialogue_window,
        min_raw_for_summary = Config.min_raw_for_summary,
        anaylsis_window = Config.analysis_window
        )

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
        response = await alice.respond({
			"text": user_input,
			"sender_name": "aki",
			"sender_id": 1,
		})
        print("爱丽丝: " + response)



if __name__ == "__main__":
    import asyncio
    asyncio.run(main())