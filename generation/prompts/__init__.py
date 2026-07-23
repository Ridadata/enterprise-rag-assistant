from pathlib import Path


_PROMPTS_DIR = Path(__file__).resolve().parent


def load_system_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()
