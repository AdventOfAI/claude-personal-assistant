from typing import Literal

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    display_name: str = ""
    tone: Literal["brief", "balanced", "friendly", "formal"] = "balanced"
    about_me: str = ""
    extra_instructions: str = Field(
        default="",
        description="How you want the assistant to behave (style, topics to avoid, etc.)",
    )


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ProfilePutRequest(BaseModel):
    profile: UserProfile


class ChatResponse(BaseModel):
    message: ChatMessage


class ConversationResponse(BaseModel):
    messages: list[ChatMessage]
