"""Synchronize Project Team members with User Permissions."""

from __future__ import annotations

import frappe

MANAGED_DESCRIPTION_PREFIX = "erp_implementation: managed"


def _get_project_team_users(project_name: str) -> set[str]:
    team_users = frappe.get_all(
        "Project Team",
        filters={"parent": project_name, "parenttype": "Project"},
        pluck="user",
    )
    return {user for user in team_users if user}


def _get_project_user_permissions(project_name: str) -> list[dict]:
    return frappe.get_all(
        "User Permission",
        filters={"allow": "Project", "for_value": project_name},
        fields=["name", "user", "description"],
    )


def _is_managed_permission(permission: dict) -> bool:
    description = (permission.get("description") or "").strip()
    return description.startswith(MANAGED_DESCRIPTION_PREFIX)


def _create_user_permission(project_name: str, user: str, dry_run: bool) -> None:
    if dry_run:
        return

    permission = frappe.get_doc(
        {
            "doctype": "User Permission",
            "user": user,
            "allow": "Project",
            "for_value": project_name,
            "apply_to_all_doctypes": 1,
            "description": MANAGED_DESCRIPTION_PREFIX,
        }
    )
    permission.insert(ignore_permissions=True)


def _delete_user_permission(permission_name: str, dry_run: bool) -> None:
    if dry_run:
        return

    frappe.delete_doc("User Permission", permission_name, ignore_permissions=True)


def sync_project_user_permissions(project_name: str, dry_run: bool = False) -> dict:
    """Sync Project Team users to User Permissions for a single project."""
    logger = frappe.logger("erp_implementation")
    team_users = _get_project_team_users(project_name)
    permissions = _get_project_user_permissions(project_name)

    permissions_by_user: dict[str, list[dict]] = {}
    for permission in permissions:
        user = permission.get("user")
        if not user:
            continue
        permissions_by_user.setdefault(user, []).append(permission)

    created: list[str] = []
    removed: list[str] = []

    for user in sorted(team_users):
        if user in permissions_by_user:
            continue
        _create_user_permission(project_name, user, dry_run=dry_run)
        created.append(user)

    for user, user_permissions in permissions_by_user.items():
        if user in team_users:
            continue
        for permission in user_permissions:
            if not _is_managed_permission(permission):
                continue
            _delete_user_permission(permission["name"], dry_run=dry_run)
            removed.append(permission["name"])

    summary = {
        "project": project_name,
        "team_users": sorted(team_users),
        "created": created,
        "removed": removed,
        "dry_run": dry_run,
    }
    logger.info("Project permission sync completed", summary)
    return summary


def reconcile_all_projects(dry_run: bool = False, limit: int | None = None) -> dict:
    """Reconcile User Permissions for all projects."""
    logger = frappe.logger("erp_implementation")
    project_names = frappe.get_all("Project", pluck="name", limit=limit)

    aggregate = {
        "projects": [],
        "created_count": 0,
        "removed_count": 0,
        "dry_run": dry_run,
    }

    for project_name in project_names:
        result = sync_project_user_permissions(project_name, dry_run=dry_run)
        aggregate["projects"].append(result)
        aggregate["created_count"] += len(result.get("created", []))
        aggregate["removed_count"] += len(result.get("removed", []))

    logger.info("Project permission reconciliation completed", aggregate)
    return aggregate


def on_project_update(doc, method: str | None = None) -> None:
    """Doc event handler for Project updates."""
    if not doc or not doc.name:
        return

    sync_project_user_permissions(doc.name)
