from fastapi import APIRouter, FastAPI


def register_routers(app: FastAPI) -> None:
    """
    Register all API routers with versioning support.

    Versioning Strategy:
    - /api/*         -> Current version (backward compatibility)
    - /api/v1/*      -> Version 1 (explicit alias)

    All routers are registered twice: once at /api/* and once at /api/v1/*
    This allows gradual migration to versioned endpoints without breaking existing clients.
    """

    def include_with_api_prefix(router: APIRouter):
        """Include router at both unversioned and v1 paths."""
        if not router.prefix.startswith("/api"):
            app.include_router(router, prefix="/api", tags=router.tags or [])
            app.include_router(router, prefix="/api/v1", tags=(router.tags or []) + ["v1"])
        else:
            app.include_router(router)

    from .api.ai_agents import router as ai_agents_router

    include_with_api_prefix(ai_agents_router)
    from .api.alerts import router as alerts_router

    include_with_api_prefix(alerts_router)
    from .api.aml_officer import router as aml_officer_router

    include_with_api_prefix(aml_officer_router)
    from .api.audit import router as audit_router

    include_with_api_prefix(audit_router)
    from .api.auth import router as auth_router

    include_with_api_prefix(auth_router)
    from .api.cases import router as cases_router

    include_with_api_prefix(cases_router)
    from .api.celex import router as celex_router

    include_with_api_prefix(celex_router)
    from .api.compliance import router as compliance_router

    include_with_api_prefix(compliance_router)
    from .api.compliance_workflow import router as compliance_workflow_router

    include_with_api_prefix(compliance_workflow_router)
    from .api.decisioning import router as decisioning_router

    include_with_api_prefix(decisioning_router)
    from .api.endpoints import router as endpoints_router

    include_with_api_prefix(endpoints_router)
    from .api.features import router as features_router

    include_with_api_prefix(features_router)

    from .api.findings import router as findings_router

    include_with_api_prefix(findings_router)
    from .api.impact import router as impact_router

    include_with_api_prefix(impact_router)
    from .api.ingestion import router as ingestion_router

    include_with_api_prefix(ingestion_router)
    from .api.model_registry import router as model_registry_router

    include_with_api_prefix(model_registry_router)
    from .api.monitoring_dashboard import router as monitoring_dashboard_router

    include_with_api_prefix(monitoring_dashboard_router)
    from .api.monitoring_rules import router as monitoring_rules_router

    include_with_api_prefix(monitoring_rules_router)
    from .api.network_analysis import router as network_analysis_router

    include_with_api_prefix(network_analysis_router)
    from .api.obligations import router as obligations_router

    include_with_api_prefix(obligations_router)
    from .api.onchain_risk import router as onchain_risk_router

    include_with_api_prefix(onchain_risk_router)
    from .api.policies import router as policies_router

    include_with_api_prefix(policies_router)
    from .api.query import router as query_router

    include_with_api_prefix(query_router)
    from .api.reporting import router as reporting_router

    include_with_api_prefix(reporting_router)
    from .api.risk import router as risk_router

    include_with_api_prefix(risk_router)
    from .api.risk_profiles import router as risk_profiles_router

    include_with_api_prefix(risk_profiles_router)
    from .api.tenants import router as tenants_router

    include_with_api_prefix(tenants_router)
    from .api.transactions import router as transactions_router

    include_with_api_prefix(transactions_router)
    from .api.travel_rule import router as travel_rule_router

    include_with_api_prefix(travel_rule_router)
    from .api.websocket import router as websocket_router

    include_with_api_prefix(websocket_router)

    # Metrics aren't prefixed with /api
    from .monitoring.metrics import router as metrics_router

    app.include_router(metrics_router)
