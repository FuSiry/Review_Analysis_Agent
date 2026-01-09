from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from src.config.loader import get_config_section
from src.models.provider import ChatModel

_MCP_TOOLS: list[Any] | None = None
_MCP_TOOLS_LOCK: asyncio.Lock | None = None


def _get_mcp_tools_lock() -> asyncio.Lock:
    global _MCP_TOOLS_LOCK
    if _MCP_TOOLS_LOCK is None:
        _MCP_TOOLS_LOCK = asyncio.Lock()
    return _MCP_TOOLS_LOCK


async def load_mcp_tools() -> list[Any]:
    global _MCP_TOOLS
    if _MCP_TOOLS is not None:
        return _MCP_TOOLS

    async with _get_mcp_tools_lock():
        if _MCP_TOOLS is not None:
            return _MCP_TOOLS

        servers_cfg = get_config_section(["tools", "mcp_servers"])
        if not servers_cfg:
            _MCP_TOOLS = []
            return _MCP_TOOLS

        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore
        except Exception:
            _MCP_TOOLS = []
            return _MCP_TOOLS

        servers: dict[str, dict[str, Any]] = {}
        for name, cfg in servers_cfg.items():
            if not isinstance(cfg, dict):
                continue
            transport = cfg.get("transport")
            url = cfg.get("url")
            if isinstance(transport, str) and isinstance(url, str):
                servers[name] = {"transport": transport, "url": url}

        if not servers:
            _MCP_TOOLS = []
            return _MCP_TOOLS

        client = MultiServerMCPClient(servers)
        tools: Any
        try:
            tools = await client.get_tools()
        except Exception:
            tools = []

        if isinstance(tools, list):
            _MCP_TOOLS = tools
        else:
            _MCP_TOOLS = []
        return _MCP_TOOLS


def _extract_tool_calls(msg: Any) -> list[dict[str, Any]]:
    tool_calls = getattr(msg, "tool_calls", None)
    if isinstance(tool_calls, list):
        return [x for x in tool_calls if isinstance(x, dict)]

    additional_kwargs = getattr(msg, "additional_kwargs", None)
    if isinstance(additional_kwargs, dict):
        tool_calls2 = additional_kwargs.get("tool_calls")
        if isinstance(tool_calls2, list):
            out: list[dict[str, Any]] = []
            for x in tool_calls2:
                if isinstance(x, dict):
                    out.append(x)
            return out

    return []


def _normalize_tool_args(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {"input": raw}
    return {"input": raw}


class ToolCallingChatModel:
    def __init__(
        self,
        base_model: ChatModel,
        *,
        max_tool_iterations: int = 8,
    ) -> None:
        self._base_model = base_model
        self._max_tool_iterations = max_tool_iterations
        self._tools_loaded = False
        self._tools: list[Any] = []
        self._bound_model: Any = base_model

    async def _ensure_tools_loaded(self) -> None:
        if self._tools_loaded:
            return

        tools = await load_mcp_tools()
        self._tools = tools
        self._tools_loaded = True

        if not tools:
            self._bound_model = self._base_model
            return

        bind_tools = getattr(self._base_model, "bind_tools", None)
        if callable(bind_tools):
            try:
                self._bound_model = bind_tools(tools)
            except Exception:
                self._bound_model = self._base_model
        else:
            self._bound_model = self._base_model

    async def ainvoke(
        self,
        input: Any,
        config: Any | None = None,
        **kwargs: Any,
    ) -> Any:
        await self._ensure_tools_loaded()
        if not self._tools:
            return await self._base_model.ainvoke(input, config=config, **kwargs)

        if not isinstance(input, list):
            return await self._bound_model.ainvoke(input, config=config, **kwargs)

        tool_by_name: dict[str, Any] = {}
        for tool in self._tools:
            name = getattr(tool, "name", None)
            if isinstance(name, str) and name:
                tool_by_name[name] = tool

        messages: list[Any] = list(input)
        last: Any | None = None
        for _ in range(self._max_tool_iterations):
            last = await self._bound_model.ainvoke(messages, config=config, **kwargs)
            tool_calls = _extract_tool_calls(last)
            if not tool_calls:
                return last

            messages.append(last)
            for call in tool_calls:
                name = call.get("name")
                if not isinstance(name, str) or not name:
                    continue
                tool = tool_by_name.get(name)
                call_id = call.get("id") or call.get("tool_call_id") or name
                args = _normalize_tool_args(call.get("args") or call.get("arguments"))

                if tool is None:
                    messages.append(
                        ToolMessage(
                            content=f"tool not found: {name}",
                            tool_call_id=str(call_id),
                        )
                    )
                    continue

                try:
                    try:
                        ainvoke = tool.ainvoke
                    except AttributeError:
                        ainvoke = None
                    if callable(ainvoke):
                        result = await ainvoke(args)
                    else:
                        try:
                            invoke = tool.invoke
                        except AttributeError:
                            invoke = None
                        if callable(invoke):
                            result = invoke(args)
                        else:
                            result = f"tool not invokable: {name}"
                except Exception as e:
                    result = f"tool error: {name}: {e}"

                if isinstance(result, str):
                    content = result
                else:
                    try:
                        content = json.dumps(result, ensure_ascii=False)
                    except Exception:
                        content = str(result)

                messages.append(ToolMessage(content=content, tool_call_id=str(call_id)))

        if last is None:
            return await self._bound_model.ainvoke(messages, config=config, **kwargs)
        return last


def _resolve_api_key(settings: dict[str, Any]) -> SecretStr | None:
    api_key = settings.get("api_key")
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    elif isinstance(api_key, str) and api_key.startswith("$"):
        api_key = os.getenv(api_key[1:])
    if not api_key or not isinstance(api_key, str):
        return None
    return SecretStr(api_key)


def init_chat_model() -> ChatModel:
    settings = get_config_section(["models", "chat_model"])
    if not settings:
        raise ValueError("The `models/chat_model` section in `config.yaml` is not found")
    model = settings.get("model")
    if not model:
        raise ValueError("The `model` in `config.yaml` is not found")
    api_key = _resolve_api_key(settings)
    if api_key is None:
        raise ValueError("OpenAI API key is not configured")
    rest_settings: dict[str, Any] = dict(settings)
    rest_settings.pop("model", None)
    rest_settings.pop("api_key", None)
    rest_settings.pop("type", None)
    base = ChatOpenAI(model=model, api_key=api_key, **rest_settings)
    return ToolCallingChatModel(base)
