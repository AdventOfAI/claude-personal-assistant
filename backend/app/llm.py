from anthropic import Anthropic

from app.config import settings
from app.schemas import ChatMessage, UserProfile


def build_system_prompt(profile: UserProfile) -> str:
    tone_lines = {
        "brief": "Prefer short, direct answers unless the user asks for depth.",
        "balanced": "Balance clarity with enough detail to be useful.",
        "friendly": "Use a warm, conversational tone.",
        "formal": "Use a clear, professional tone.",
    }
    parts = [
        "You are a helpful personal assistant.",
        tone_lines.get(profile.tone, tone_lines["balanced"]),
    ]
    if profile.display_name.strip():
        parts.append(f"The user's preferred name is: {profile.display_name.strip()}.")
    if profile.about_me.strip():
        parts.append(f"Context about the user:\n{profile.about_me.strip()}")
    if profile.extra_instructions.strip():
        parts.append(f"Additional preferences from the user:\n{profile.extra_instructions.strip()}")
    parts.append(
        "Use this context to personalize replies naturally. Do not recite this block back unless asked."
    )
    return "\n\n".join(parts)


def _with_file_context(system: str, filename: str, file_text: str) -> str:
    return (
        f"{system}\n\n---\nThe user attached a file named «{filename}». "
        "Use the following content as reference when answering their message.\n\n"
        f"{file_text}\n---"
    )


def complete_chat(
    profile: UserProfile,
    messages: list[ChatMessage],
    file_text: str | None = None,
    file_filename: str | None = None,
) -> str:
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    client = Anthropic(api_key=settings.anthropic_api_key)
    system = build_system_prompt(profile)
    if file_text and file_filename:
        system = _with_file_context(system, file_filename, file_text)
    api_messages = [{"role": m.role, "content": m.content} for m in messages]

    response = client.messages.create(
        model=settings.claude_model,
        max_tokens=4096,
        system=system,
        messages=api_messages,
    )

    text_blocks = [b.text for b in response.content if b.type == "text"]
    return "".join(text_blocks).strip()
