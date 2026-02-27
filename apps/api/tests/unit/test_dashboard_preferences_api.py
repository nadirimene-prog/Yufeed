import pytest


def _sample_filters(**overrides):
    payload = {
        "page": 1,
        "pageSize": 50,
        "queue": "all",
        "severity": "all",
        "jurisdiction": "",
        "sla": "all",
        "search": "",
        "savedView": "all",
    }
    payload.update(overrides)
    return payload


@pytest.mark.unit
def test_dashboard_saved_views_crud_and_preferences_roundtrip(client, auth_headers, admin_headers):
    private_create = client.post(
        "/api/dashboard/views",
        json={
            "name": "My Escalations",
            "scope": "private",
            "filters": _sample_filters(queue="cases", savedView="escalations"),
            "layout_prefs": {"queueDensity": "compact", "insightsOpen": True},
        },
        headers=auth_headers,
    )
    assert private_create.status_code == 201, private_create.text
    private_view = private_create.json()

    team_create = client.post(
        "/api/dashboard/views",
        json={
            "name": "Team Backlog",
            "scope": "team",
            "filters": _sample_filters(queue="alerts", severity="high"),
            "layout_prefs": {"queueDensity": "comfortable"},
        },
        headers=admin_headers,
    )
    assert team_create.status_code == 201, team_create.text
    team_view = team_create.json()
    assert team_view["team_id"] == "default"

    listed = client.get("/api/dashboard/views", headers=auth_headers)
    assert listed.status_code == 200, listed.text
    body = listed.json()
    ids = {item["id"] for item in body["items"]}
    assert private_view["id"] in ids
    assert team_view["id"] in ids

    patch_resp = client.patch(
        f"/api/dashboard/views/{private_view['id']}",
        json={
            "name": "My Escalations (Updated)",
            "filters": _sample_filters(queue="reg_tasks", savedView="escalations"),
        },
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200, patch_resp.text
    patched = patch_resp.json()
    assert patched["name"] == "My Escalations (Updated)"
    assert patched["filters"]["queue"] == "reg_tasks"

    pref_patch = client.patch(
        "/api/dashboard/preferences",
        json={
            "layout_prefs": {
                "queueDensity": "compact",
                "insightsOpen": True,
                "defaultWorkspaceTab": "actions",
            },
            "default_saved_view_id": private_view["id"],
        },
        headers=auth_headers,
    )
    assert pref_patch.status_code == 200, pref_patch.text
    prefs = pref_patch.json()
    assert prefs["layout_prefs"]["queueDensity"] == "compact"
    assert prefs["layout_prefs"]["defaultWorkspaceTab"] == "actions"
    assert prefs["default_saved_view_id"] == private_view["id"]

    pref_get = client.get("/api/dashboard/preferences", headers=auth_headers)
    assert pref_get.status_code == 200, pref_get.text
    pref_body = pref_get.json()
    assert pref_body["layout_prefs"]["insightsOpen"] is True
    assert pref_body["default_saved_view_id"] == private_view["id"]

    invalid_pref = client.patch(
        "/api/dashboard/preferences",
        json={"default_saved_view_id": "dsv_missing"},
        headers=auth_headers,
    )
    assert invalid_pref.status_code == 400

    delete_resp = client.delete(
        f"/api/dashboard/views/{private_view['id']}",
        headers=auth_headers,
    )
    assert delete_resp.status_code == 204, delete_resp.text

    listed_after_delete = client.get("/api/dashboard/views", headers=auth_headers)
    assert listed_after_delete.status_code == 200
    ids_after = {item["id"] for item in listed_after_delete.json()["items"]}
    assert private_view["id"] not in ids_after
    assert team_view["id"] in ids_after


@pytest.mark.unit
def test_dashboard_saved_views_resolves_role_default_for_manager(
    client,
    ensure_tenant_membership,
):
    manager_password = "ManagerPassword123!"  # pragma: allowlist secret

    register = client.post(
        "/api/auth/register",
        json={
            "email": "manager@example.com",
            "password": manager_password,
            "full_name": "Manager User",
        },
    )
    assert register.status_code in {200, 201}, register.text
    ensure_tenant_membership("manager@example.com", role="manager", tenant_id="default")

    login = client.post(
        "/api/auth/login",
        json={
            "email": "manager@example.com",
            "password": manager_password,
            "tenant_id": "default",
        },
    )
    assert login.status_code == 200, login.text
    manager_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}",
        "X-Tenant-ID": "default",
    }

    create_team_default = client.post(
        "/api/dashboard/views",
        json={
            "name": "Manager Review Backlog",
            "scope": "team",
            "is_default_for_role": True,
            "role": "manager",
            "filters": _sample_filters(queue="approvals", severity="high"),
            "layout_prefs": {"insightsOpen": True},
        },
        headers=manager_headers,
    )
    assert create_team_default.status_code == 201, create_team_default.text
    record = create_team_default.json()

    listed = client.get("/api/dashboard/views", headers=manager_headers)
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["resolved_default_view_id"] == record["id"]
