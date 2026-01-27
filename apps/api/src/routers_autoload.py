# AUTO-GENERATED: routers autoload
from typing import List
from fastapi import APIRouter, FastAPI

def register_routers(app: FastAPI) -> None:
    from .api.ai_agents import router as r1
    app.include_router(r1)
    from .api.alerts import router as r2
    app.include_router(r2)
    from .api.aml_officer import router as r3
    app.include_router(r3)
    from .api.audit import router as r4
    app.include_router(r4)
    from .api.auth import router as r5
    app.include_router(r5)
    from .api.cases import router as r6
    app.include_router(r6)
    from .api.celex import router as r7
    app.include_router(r7)
    from .api.compliance import router as r8
    app.include_router(r8)
    from .api.compliance_workflow import router as r9
    app.include_router(r9)
    from .api.decisioning import router as r10
    app.include_router(r10)
    from .api.endpoints import router as r11
    app.include_router(r11)
    from .api.features import router as r12
    app.include_router(r12)
    from .api.impact import router as r13
    app.include_router(r13)
    from .api.model_registry import router as r14
    app.include_router(r14)
    from .api.monitoring_dashboard import router as r15
    app.include_router(r15)
    from .api.monitoring_rules import router as r16
    app.include_router(r16)
    from .api.network_analysis import router as r17
    app.include_router(r17)
    from .api.obligations import router as r18
    app.include_router(r18)
    from .api.onchain_risk import router as r19
    app.include_router(r19)
    from .api.query import router as r20
    app.include_router(r20)
    from .api.reporting import router as r21
    app.include_router(r21)
    from .api.risk_profiles import router as r22
    app.include_router(r22)
    from .api.tenants import router as r23
    app.include_router(r23)
    from .api.transactions import router as r24
    app.include_router(r24)
    from .api.travel_rule import router as r25
    app.include_router(r25)
    from .api.websocket import router as r26
    app.include_router(r26)
    from .monitoring.metrics import router as r27
    app.include_router(r27)

