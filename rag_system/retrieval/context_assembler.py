"""Token预算上下文组装器"""


def estimate_tokens(text: str) -> int:
    """粗略估计token数（1中文≈1.5token，1英文单词≈1token）"""
    zh = sum(1 for c in text if '一' <= c <= '鿿')
    en_words = len([w for w in text.split() if any(c.isascii() and c.isalpha() for c in w)])
    return int(zh * 1.5 + en_words)


class ContextAssembler:
    """
    将检索到的文档块组装为上下文字符串
    按相关性排序，控制总token预算
    """

    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens

    def assemble(self, chunks_with_scores: list, chunk_text_map: dict = None) -> str:
        """
        组装上下文

        Parameters
        ----------
        chunks_with_scores : list of (chunk_id, score)
        chunk_text_map : dict, {chunk_id: text}

        Returns
        -------
        str, 组装后的上下文
        """
        if not chunks_with_scores:
            return ""

        parts = []
        used_tokens = 0

        for chunk_id, score in chunks_with_scores:
            text = chunk_text_map.get(chunk_id, "") if chunk_text_map else ""
            if not text:
                continue

            chunk_tokens = estimate_tokens(text)
            if used_tokens + chunk_tokens > self.max_tokens:
                # 尝试截断
                remaining = self.max_tokens - used_tokens
                if remaining < 100:
                    break
                # 粗略截断
                char_limit = int(remaining / 1.5)
                text = text[:char_limit] + "..."

            header = f"[Score: {score:.3f}]"
            if chunk_text_map and isinstance(chunk_text_map, dict):
                meta = chunk_text_map.get(f"{chunk_id}_meta", {})
                if meta:
                    parts_str = []
                    if meta.get("title"):
                        parts_str.append(f"Title: {meta['title']}")
                    if meta.get("authors"):
                        parts_str.append(f"Authors: {', '.join(meta['authors'][:3])}")
                    if meta.get("year"):
                        parts_str.append(f"Year: {meta['year']}")
                    if parts_str:
                        header = f"[{' | '.join(parts_str)}] (Score: {score:.3f})"

            parts.append(f"{header}\n{text}")
            used_tokens += chunk_tokens

        return "\n\n---\n\n".join(parts)
