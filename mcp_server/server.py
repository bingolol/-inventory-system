"""MCP server 入口 — stdio 传输

启动方式:
    python -m mcp_server.server

也由 Electron 主进程 spawn (随系统启动)。

职责:
1. 初始化账本上下文
2. 注册 tools / resources / prompts
3. 跑 MCP stdio main loop
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# 把 backend 目录加入 sys.path, 让 mcp_server 能 import commands/policy/reports
_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool, ResourcesCapability, ResourceTemplate, PromptsCapability,
    Prompt, PromptArgument, GetPromptResult, PromptMessage,
    TextContent, ImageContent, EmbeddedResource,
    CallToolResult, ReadResourceResult,
    ServerCapabilities, LoggingLevel,
    ToolsCapability,
)

from . import account_context
from . import tools
from . import tool_dispatcher
from . import resources as resources_mod
from . import prompts as prompts_mod
from errors import BusinessError
from database import init_db

logger = logging.getLogger("mcp_server")

# 初始化数据库 (WAL 模式 + 自动迁移 + 触发器, 幂等)
def _init_database():
    """确保数据库 schema 最新、WAL 模式已开启、写保护触发器已就绪。"""
    try:
        init_db()
        logger.info("MCP server 数据库初始化完成 (WAL + 迁移 + 触发器)")
    except Exception as e:
        logger.warning(f"数据库初始化失败: {e}")

# 初始化账本上下文
def _init_context():
    """初始化账本上下文 (启动时取默认账本)。"""
    try:
        aid = account_context.init_default_account()
        logger.info(f"MCP server 默认账本: account_id={aid}")
    except Exception as e:
        logger.warning(f"初始化默认账本失败: {e}")


server = Server("inventory-mcp")


# ──────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name=t["name"],
            description=t["description"],
            inputSchema=t["inputSchema"],
        )
        for t in tools.TOOL_TEMPLATES
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """执行 tool 调用。

    返回类型:
        成功: list[TextContent]  (默认 isError=False)
        失败: CallToolResult(isError=True, content=[TextContent(...)])
              必须显式设置 isError=True, 否则 client 端 is_error=False,
              导致 period 格式校验等 BusinessError 被误判为成功。
    """
    handler = tools.TOOL_HANDLERS.get(name)
    if not handler:
        return CallToolResult(
            isError=True,
            content=[TextContent(
                type="text",
                text=f'{{"ok": false, "error": "未知 tool: {name}"}}',
            )],
        )

    try:
        result = handler(arguments)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]
    except BusinessError as e:
        err = tool_dispatcher.format_business_error(e)
        return CallToolResult(
            isError=True,
            content=[TextContent(
                type="text",
                text=json.dumps({"ok": False, "error": err}, ensure_ascii=False, default=str),
            )],
        )
    except Exception as e:
        logger.exception(f"tool {name} 执行失败")
        return CallToolResult(
            isError=True,
            content=[TextContent(
                type="text",
                text=f'{{"ok": false, "error": "{type(e).__name__}: {str(e)}"}}',
            )],
        )


# ──────────────────────────────────────────────────────────────
# Resources
# ──────────────────────────────────────────────────────────────
@server.list_resources()
async def list_resources() -> list:
    # 静态资源列表 (URI 模板需要 agent 自行填充)
    return []


@server.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    return [
        ResourceTemplate(
            uriTemplate=t["uriTemplate"],
            name=t["name"],
            description=t["description"],
            mimeType=t["mimeType"],
        )
        for t in resources_mod.RESOURCE_TEMPLATES
    ]


@server.read_resource()
async def read_resource(uri) -> str:
    # MCP 把 uri 作为 AnyUrl 对象传入, 转成字符串
    uri_str = str(uri)
    try:
        result = resources_mod.read_resource(uri_str)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception(f"read_resource {uri_str} 失败")
        return f'{{"error": "{type(e).__name__}: {str(e)}"}}'


# ──────────────────────────────────────────────────────────────
# Prompts
# ──────────────────────────────────────────────────────────────
@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    return [
        Prompt(
            name=p["name"],
            description=p["description"],
            arguments=[
                PromptArgument(name=a["name"], description=a["description"], required=a.get("required", False))
                for a in p.get("arguments", [])
            ],
        )
        for p in prompts_mod.PROMPT_TEMPLATES
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict) -> GetPromptResult:
    try:
        result = prompts_mod.get_prompt(name, arguments)
        messages = []
        for m in result["messages"]:
            content = m["content"]
            if content["type"] == "text":
                messages.append(PromptMessage(
                    role=m["role"],
                    content=TextContent(type="text", text=content["text"]),
                ))
            else:
                # 其他类型暂时按 text 处理
                messages.append(PromptMessage(
                    role=m["role"],
                    content=TextContent(type="text", text=str(content)),
                ))
        return GetPromptResult(messages=messages)
    except Exception as e:
        logger.exception(f"get_prompt {name} 失败")
        return GetPromptResult(
            messages=[PromptMessage(
                role="assistant",
                content=TextContent(type="text", text=f"prompt 渲染失败: {type(e).__name__}: {str(e)}"),
            )]
        )


# ──────────────────────────────────────────────────────────────
# main 入口
# ──────────────────────────────────────────────────────────────
async def main():
    # 配置日志 (写 stderr, 不污染 stdout stdio 通信)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        stream=sys.stderr,
    )

    _init_database()
    _init_context()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="inventory-mcp",
                server_version="0.1.0",
                capabilities=ServerCapabilities(
                    tools=ToolsCapability(),
                    resources=ResourcesCapability(),
                    prompts=PromptsCapability(),
                    logging=None,
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
