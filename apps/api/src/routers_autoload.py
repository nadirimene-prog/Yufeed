# AUTO-GENERATED: routers autoload
from typing import List
from fastapi import APIRouter, FastAPI

def register_routers(app: FastAPI) -> None:
    def include_with_api_prefix(router: APIRouter):
        if not router.prefix.startswith("/api"):
            app.include_router(router, prefix="/api")
        else:
            app.include_router(router)

    from .api.ai_agents import router as r1
    include_with_api_prefix(r1)
    from .api.alerts import router as r2
    include_with_api_prefix(r2)
    from .api.aml_officer import router as r3
    include_with_api_prefix(r3)
    from .api.audit import router as r4
    include_with_api_prefix(r4)
    from .api.auth import router as r5
    include_with_api_prefix(r5)
    from .api.cases import router as r6
    include_with_api_prefix(r6)
    from .api.celex import router as r7
    include_with_api_prefix(r7)
    from .api.compliance import router as r8
    include_with_api_prefix(r8)
    from .api.compliance_workflow import router as r9
    include_with_api_prefix(r9)
    from .api.decisioning import router as r10
    include_with_api_prefix(r10)
    from .api.endpoints import router as r11
    include_with_api_prefix(r11)
    from .api.features import router as r12
    include_with_api_prefix(r12)
    from .api.impact import router as r13
    include_with_api_prefix(r13)
    from .api.model_registry import router as r14
    include_with_api_prefix(r14)
    from .api.monitoring_dashboard import router as r15
    include_with_api_prefix(r15)
    from .api.monitoring_rules import router as r16
    include_with_api_prefix(r16)
    from .api.network_analysis import router as r17
    include_with_api_prefix(r17)
    from .api.obligations import router as r18
    include_with_api_prefix(r18)
    from .api.policies import router as r28
    include_with_api_prefix(r28)
    from .api.risk import router as r29
    include_with_api_prefix(r29)
    from .api.onchain_risk import router as r19
    include_with_api_prefix(r19)
    from .api.query import router as r20
    include_with_api_prefix(r20)
    from .api.reporting import router as r21
    include_with_api_prefix(r21)
    from .api.risk_profiles import router as r22
    include_with_api_prefix(r22)
    from .api.tenants import router as r23
    include_with_api_prefix(r23)
    from .api.transactions import router as r24
    include_with_api_prefix(r24)
    from .api.travel_rule import router as r25
    include_with_api_prefix(r25)
    from .api.websocket import router as r26
    include_with_api_prefix(r26)
    from .api.ingestion import router as r30
    include_with_api_prefix(r30)
    from .monitoring.metrics import router as r27
    app.include_router(r27) # Metrics usually aren't prefixed with /api
