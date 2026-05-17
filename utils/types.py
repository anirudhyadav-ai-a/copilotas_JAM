"""Pydantic models for the copilotas_JAM phase."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Message(BaseModel):
    """A single chat message."""

    role: str = Field(description="One of: system, user, assistant, tool")
    content: str = Field(description="Text content of the message")


class ToolCall(BaseModel):
    """Represents a tool/function call requested by the LLM."""

    name: str = Field(description="Name of the tool to invoke")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )


class ToolResult(BaseModel):
    """Result returned after executing a tool."""

    name: str = Field(description="Name of the tool that was executed")
    result: str = Field(description="Stringified result of the tool execution")


class RuleMatch(BaseModel):
    """Outcome of evaluating an input against a static rule."""

    rule_name: str = Field(description="Name of the rule that matched")
    matched: bool = Field(description="Whether the rule fired")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score"
    )
