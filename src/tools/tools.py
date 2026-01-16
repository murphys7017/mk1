import re


class tools:
    @staticmethod
    def normalizeBlock(text: str) -> str:
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

    @staticmethod
    def formatBlock(title: str, *lines: str, width: int = 120) -> str:
        """
        Format multiple lines into a readable block with automatic wrapping.
        - `title`: short title to appear on the first line
        - `lines`: arbitrary number of text lines to include
        - `width`: wrap width (default 120)

        Returns a single string with newlines that is safe to pass to logger.
        """
        import textwrap

        out_lines = []
        if title:
            out_lines.append(str(title))
            out_lines.append("-")

        for ln in lines:
            if ln is None:
                continue
            # normalize whitespace then wrap
            # normalized = tools.normalizeBlock(str(ln))
            wrapped = textwrap.fill(str(ln), width=width)
            out_lines.append(wrapped)

        return "\n".join(out_lines)