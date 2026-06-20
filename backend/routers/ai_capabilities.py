"""AI 能力发现接口 — 返回 AI 可调用的规范写接口清单

让 AI Agent 以本接口为唯一真相源，避免猜测端点。调用非清单内写接口会被
AIGatewayMiddleware 拦截（403 + ai_instruction 指明规范替代）。

  GET /api/_ai/capabilities → { "write_endpoints": [...], "note": "..." }
"""

from fastapi import APIRouter

from ai_gateway import AI_CAPABILITIES

router = APIRouter()


@router.get("/capabilities")
def list_ai_capabilities():
    """返回 AI 可调用的规范写接口清单（GET 查询类全部开放，无需列举）"""
    return {
        "note": (
            "GET 查询类接口对 AI 全部开放。写接口（POST/PUT/DELETE/PATCH）仅下表所列为规范入口，"
            "调用其他写接口将返回 403。新能力应作为现有规范端点的可选字段，而非新增并行端点。"
        ),
        "write_endpoints": [
            {
                "method": cap.method,
                "path": cap.path,
                "desc": cap.desc,
                "params_hint": cap.params_hint,
                "replaces": cap.replaces,
            }
            for cap in AI_CAPABILITIES
            if cap.canonical
        ],
    }
