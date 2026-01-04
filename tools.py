import re


class tools:
    @staticmethod
    def normalize_block(text: str) -> str:
        """
        将各种复杂空白（换行、tab、多空格）统一为：
        - 行内：单个空格
        - 行首行尾：去除
        """
        if not text:
            return ""

        # 把 \t 统一成空格
        text = text.replace("\t", " ")

        # 把多个空白字符（包括换行）压缩成一个空格
        text = re.sub(r"\s+", " ", text)

        return text.replace("\t", " ").strip()