import time


class PerceptionSystem:
    def __init__(self):
        pass
    def text_analysis(self, text: str) -> dict:
        return {
            "time_stamp": int(round(time.time() * 1000)),
            "time_date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "media_type": "text",
            "analysis_results": text
        }
    
    def analyze(self, input_data: str) -> dict:
        return self.text_analysis(input_data)