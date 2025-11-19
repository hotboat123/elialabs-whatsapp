"""
FastAPI-based MCP server that delegates tool executions to Anthropic Claude
using the official Anthropic SDK and construye contexto directamente desde la base de
datos PostgreSQL usando los mismos módulos de la app principal.

El servidor expone un único endpoint (`/tools/<tool_name>`, por defecto `openai_chat`)
que el bot llama mediante `MCPHandler`. Así todo el acceso a Claude (y ahora a Postgres)
ocurre dentro del servidor MCP.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from anthropic import Anthropic, NotFoundError
from pydantic import BaseModel, Field

from app.bot.context_builder import build_business_context

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


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MCP_MODEL", "claude-3-haiku-20240307")
_fallback_models = os.getenv(
    "ANTHROPIC_MCP_FALLBACK_MODELS",
    "claude-3-5-sonnet-20241022,claude-3-5-sonnet-20240620,claude-3-sonnet-20240229",
)
ANTHROPIC_MODEL_FALLBACKS: List[str] = [
    model.strip()
    for model in _fallback_models.split(",")
    if model.strip()
]
ANTHROPIC_TEMPERATURE = _env_float("ANTHROPIC_MCP_TEMPERATURE", 0.7)
ANTHROPIC_MAX_TOKENS = _env_int("ANTHROPIC_MCP_MAX_TOKENS", 1024)
TOOL_NAME = os.getenv("OPENAI_MCP_TOOL_NAME", "openai_chat")
SERVER_SECRET = os.getenv("OPENAI_MCP_SERVER_KEY")
SERVER_HOST = os.getenv("OPENAI_MCP_HOST", "0.0.0.0")
SERVER_PORT = _env_int("OPENAI_MCP_PORT", 9000)
SERVER_RELOAD = os.getenv("OPENAI_MCP_RELOAD", "false").lower() == "true"

def _build_client_kwargs() -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {"api_key": ANTHROPIC_API_KEY}
    if ANTHROPIC_BASE_URL:
        normalized = ANTHROPIC_BASE_URL.rstrip("/")
        if normalized.endswith("/v1"):
            normalized = normalized[: -len("/v1")]
        kwargs["base_url"] = normalized
    return kwargs


# Initialize Anthropic client
_client: Optional[Anthropic] = None
if ANTHROPIC_API_KEY:
    _client = Anthropic(**_build_client_kwargs())


def _candidate_models() -> List[str]:
    seen = set()
    ordered: List[str] = []
    for model in [ANTHROPIC_MODEL, *ANTHROPIC_MODEL_FALLBACKS]:
        if model and model not in seen:
            seen.add(model)
            ordered.append(model)
    return ordered

class ConversationMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(..., min_length=1)


class ToolArguments(BaseModel):
    conversation: List[ConversationMessage] = Field(
        default_factory=list,
        description="Ordered conversation history without the system prompt.",
    )
    message_text: Optional[str] = Field(
        default=None,
        description="Último mensaje del usuario para inferir contexto.",
    )
    phone_number: Optional[str] = Field(
        default=None,
        description="Teléfono del contacto para personalizar reportes.",
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


def _ensure_client() -> Anthropic:
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ANTHROPIC_API_KEY is not configured.",
            )
        _client = Anthropic(**_build_client_kwargs())
    return _client


async def _resolve_business_context(args: ToolArguments) -> Optional[str]:
    if args.business_context:
        return args.business_context
    
    if not args.message_text:
        return None
    
    try:
        context = await build_business_context(args.message_text, args.phone_number)
        if context:
            logger.info("Business context built directly from database via MCP.")
        return context
    except Exception as exc:
        logger.error("Failed to build business context inside MCP: %s", exc)
        return None


def _build_messages_for_claude(
    args: ToolArguments, context_data: Optional[str]
) -> tuple[Optional[str], List[Dict[str, str]]]:
    """
    Build payload for Anthropic Claude:
    - Returns system prompt (string or None)
    - Returns list of user/assistant messages (Claude API does not accept system role there)
    """
    if not args.conversation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="conversation cannot be empty.",
        )

    system_parts: List[str] = []

    system_prompt = args.system_prompt.strip()
    if system_prompt:
        system_parts.append(system_prompt)

    if context_data:
        context = context_data.strip()
        system_parts.append(f"[INFORMACIÓN DE LA BASE DE DATOS]\n{context}")

    final_system_prompt = "\n\n".join(system_parts) if system_parts else None

    claude_messages: List[Dict[str, str]] = []
    for item in args.conversation:
        content = item.content.strip()
        if not content:
            continue
        if item.role not in ("user", "assistant"):
            # Claude only accepts user/assistant roles in the messages list
            continue
        claude_messages.append({"role": item.role, "content": content})

    return final_system_prompt, claude_messages


def create_router(prefix: str = "") -> APIRouter:
    router = APIRouter(prefix=prefix, tags=["mcp"])

    @router.get("/health")
    async def healthcheck() -> Dict[str, Any]:
        return {
            "status": "ok",
            "model": ANTHROPIC_MODEL,
            "tool": TOOL_NAME,
            "time": datetime.now(timezone.utc).isoformat(),
        }

    @router.post(f"/tools/{TOOL_NAME}", response_model=ToolResponse)
    async def invoke_openai_tool(
        payload: ToolInvocation, _: None = Depends(verify_authorization)
    ) -> ToolResponse:
        args = payload.arguments
        context_data = await _resolve_business_context(args)
        system_prompt, messages = _build_messages_for_claude(args, context_data)
        client = _ensure_client()

        logger.info(
            "Forwarding MCP conversation to Claude (messages=%s metadata=%s)",
            len(messages),
            args.metadata or {},
        )

        temperature = (
            args.temperature if args.temperature is not None else ANTHROPIC_TEMPERATURE
        )
        max_tokens = args.max_tokens if args.max_tokens is not None else ANTHROPIC_MAX_TOKENS

        response = None
        used_model: Optional[str] = None
        last_error: Optional[Exception] = None

        for model_name in _candidate_models():
            try:
                response = client.messages.create(
                    model=model_name,
                    system=system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                used_model = model_name
                break
            except NotFoundError as exc:
                last_error = exc
                logger.warning(
                    "Claude model '%s' not available (404). Trying next fallback...",
                    model_name,
                )
                continue
            except Exception as exc:  # pragma: no cover
                logger.exception("Claude API call failed with model '%s'", model_name)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Claude error: {exc}",
                ) from exc

        if response is None or used_model is None:
            detail = (
                f"All Claude models unavailable ({last_error})"
                if last_error
                else "All Claude models unavailable"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=detail,
            )

        content_parts: List[str] = []
        for block in response.content or []:
            text = getattr(block, "text", None)
            if text is not None:
                content_parts.append(text)

        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }

        return ToolResponse(
            content="".join(content_parts).strip(),
            model=used_model or response.model,
            finish_reason=response.stop_reason or "stop",
            usage=usage,
            created_at=datetime.now(timezone.utc),
        )

    return router


def create_mcp_router() -> APIRouter:
    """Alias for create_router to match the expected import name."""
    return create_router()


def create_app() -> FastAPI:
    fastapi_app = FastAPI(
        title="OpenAI MCP Server",
        version="0.1.0",
        description="Bridge between MCP tool calls and OpenAI Chat Completions.",
    )
    fastapi_app.include_router(create_router())
    return fastapi_app


app = create_app()


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


