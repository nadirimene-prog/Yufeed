import pytest

from src.ai.orchestrator import AMLOfficer, get_aml_officer
from src.ai.agents.sar import SARWorkflowManager


@pytest.mark.unit
def test_get_aml_officer_returns_fresh_instance():
    first = get_aml_officer(db_session="db1")
    second = get_aml_officer(db_session="db2")
    assert isinstance(first, AMLOfficer)
    assert isinstance(second, AMLOfficer)
    assert first is not second
    assert first.db == "db1"
    assert second.db == "db2"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sar_workflow_manager_uses_session_id_context():
    manager = SARWorkflowManager()

    async def fake_process(context):
        assert context.session_id == "sar-CASE-123"
        raise RuntimeError("stop-after-context-check")

    manager.agent.process = fake_process

    with pytest.raises(RuntimeError, match="stop-after-context-check"):
        await manager.generate_draft(
            case_id="CASE-123",
            case_data={"id": "CASE-123"},
            transactions=[],
        )
