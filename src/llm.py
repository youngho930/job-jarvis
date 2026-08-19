import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv(override=True)

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-5"


def ask(prompt: str, system: str = "", max_tokens: int = 2000) -> str:
    """Claude에게 한 번 물어보고 텍스트를 돌려받는다."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    # content는 블록 배열이다. thinking/tool_use 등이 섞일 수 있으므로
    # text 블록만 골라서 이어붙인다.
    parts = [block.text for block in response.content if block.type == "text"]

    if not parts:
        raise ValueError(f"텍스트 응답이 없습니다. 블록 종류: {[b.type for b in response.content]}")

    return "\n".join(parts)