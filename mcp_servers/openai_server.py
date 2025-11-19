"""
FastAPI-based MCP server that delegates tool executions to OpenAI Chat Completions.

The server exposes a single tool endpoint (`/tools/<tool_name>`, default `openai_chat`)
that the WhatsApp bot can call through `MCPHandler`. This keeps all OpenAI usage inside
the MCP server, while the bot just performs HTTP tool invocations.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from openai import OpenAI
from pydantic import BaseModel, Field


logger = logging.getLogger("openai_mcp_server")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MCP_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE = _env_float("OPENAI_MCP_TEMPERATURE", 0.4)
OPENAI_MAX_TOKENS = _env_int("OPENAI_MCP_MAX_TOKENS", 700)
TOOL_NAME = os.getenv("OPENAI_MCP_TOOL_NAME", "openai_chat")
SERVER_SECRET = os.getenv("OPENAI_MCP_SERVER_KEY")
SERVER_HOST = os.getenv("OPENAI_MCP_HOST", "0.0.0.0")
SERVER_PORT = _env_int("OPENAI_MCP_PORT", 9000)
SERVER_RELOAD = os.getenv("OPENAI_MCP_RELOAD", "false").lower() == "true"

_client: Optional[OpenAI] = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

app = FastAPI(
    title="OpenAI MCP Server",
    version="0.1.0",
    description="Bridge between MCP tool calls and OpenAI Chat Completions.",
)


class ConversationMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(..., min_length=1)


class ToolArguments(BaseModel):
    conversation: List[ConversationMessage] = Field(
        default_factory=list,
        description="Ordered conversation history without the system prompt.",
    )
    system_prompt: str = Field(..., description="System instructions for the assistant.")
    business_context: Optional[str] = Field(
        default=None,
        description="Optional analytics context fetched from the database.",
    )
    temperature: Optional[float] = Field(
        default=None, ge=0.0, le=2.0, description="Override temperature if provided."
    )
    max_tokens: Optional[int] = Field(
        default=None, gt=0, description="Override max tokens if provided."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata (contact name, phone, etc.) forwarded for logging.",
    )


class ToolInvocation(BaseModel):
    arguments: ToolArguments


class ToolResponse(BaseModel):
    content: str
    model: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    created_at: datetime


async def verify_authorization(request: Request) -> None:
    """
    Simple bearer-token auth to keep the MCP endpoint private.
    """
    if not SERVER_SECRET:
        return

    header = request.headers.get("Authorization")
    if not header or not header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    token = header.split(" ", 1)[1].strip()
    if token != SERVER_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )


def _ensure_client() -> OpenAI:
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OPENAI_API_KEY is not configured.",
            )
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def _build_messages(args: ToolArguments) -> List[Dict[str, str]]:
    if not args.conversation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="conversation cannot be empty.",
        )

    messages: List[Dict[str, str]] = []
    system_prompt = args.system_prompt.strip()
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if args.business_context:
        context = args.business_context.strip()
        if context:
            messages.append(
                {
                    "role": "system",
                    "content": f"[INFORMACIÓN DE LA BASE DE DATOS]\n{context}",
                }
            )

    for item in args.conversation:
        if not item.content.strip():
            continue
        messages.append({"role": item.role, "content": item.content})

    return messages


@app.get("/health")
async def healthcheck() -> Dict[str, Any]:
    return {
        "status": "ok",
        "model": OPENAI_MODEL,
        "tool": TOOL_NAME,
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.post(f"/tools/{TOOL_NAME}", response_model=ToolResponse)
async def invoke_openai_tool(
    payload: ToolInvocation, _: None = Depends(verify_authorization)
) -> ToolResponse:
    args = payload.arguments
    messages = _build_messages(args)
    client = _ensure_client()

    logger.info(
        "Forwarding MCP conversation to OpenAI (messages=%s metadata=%s)",
        len(messages),
        args.metadata or {},
    )

    temperature = args.temperature if args.temperature is not None else OPENAI_TEMPERATURE
    max_tokens = args.max_tokens if args.max_tokens is not None else OPENAI_MAX_TOKENS

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:  # pragma: no cover - surfacing errors to client is enough
        logger.exception("OpenAI chat completion failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI error: {exc}",
        ) from exc

    choice = response.choices[0]
    content = choice.message.content or ""
    usage = (
        response.usage.model_dump()
        if hasattr(response.usage, "model_dump")
        else getattr(response.usage, "__dict__", None)
    )

    return ToolResponse(
        content=content.strip(),
        model=response.model,
        finish_reason=choice.finish_reason,
        usage=usage,
        created_at=datetime.fromtimestamp(response.created, tz=timezone.utc),
    )


def run() -> None:
    """Convenience entrypoint for `python -m mcp_servers.openai_server`."""
    import uvicorn

    uvicorn.run(
        "mcp_servers.openai_server:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=SERVER_RELOAD,
    )


if __name__ == "__main__":
    run()


