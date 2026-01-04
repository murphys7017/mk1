class tools:
    @staticmethod
    def normalize_block(text: str) -> str:
        return text.replace("\t", " ").strip()