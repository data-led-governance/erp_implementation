"""Synchronize Project users with User Permissions."""

from __future__ import annotations

import frappe

MANAGED_FLAG_FIELD = "managed_by_erp_implementation"
MANAGED_SOURCE_FIELD = "erp_implementation_source"
MANAGED_SOURCE_VALUE = "Project.users"


def _get_project_users(project_name: str) -> set[str]:
    project_users = frappe.get_all(
        "Project User",
        filters={"parent": project_name, "parenttype": "Project"},
        pluck="user",
    )
    return {user for user in project_users if user}


def _get_project_user_permissions(project_name: str) -> list[dict]:
    return frappe.get_all(
        "User Permission",
        filters={"allow": "Project", "for_value": project_name},
        fields=["name", "user"],
    )


def _get_managed_project_user_permissions(project_name: str) -> list[dict]:
    return frappe.get_all(
        "User Permission",
        filters={
            "allow": "Project",
            "for_value": project_name,
            MANAGED_FLAG_FIELD: 1,
        },
        fields=["name", "user", MANAGED_SOURCE_FIELD],
    )


def _create_user_permission(project_name: str, user: str, dry_run: bool) -> None:
    if dry_run:
        return

    permission = frappe.get_doc(
        {
            "doctype": "User Permission",
            "user": user,
            "allow": "Project",
            "for_value": project_name,
            MANAGED_FLAG_FIELD: 1,
            MANAGED_SOURCE_FIELD: MANAGED_SOURCE_VALUE,
        }
    )
    permission.insert(ignore_permissions=True)


def _delete_user_permission(permission_name: str, dry_run: bool) -> None:
    if dry_run:
        return

    frappe.delete_doc(
        "User Permission", permission_name, ignore_permissions=True, force=True
    )


def sync_project_user_permissions(project_name: str, dry_run: bool = False) -> dict:
    """Sync Project users to User Permissions for a single project."""
    logger = frappe.logger("erp_implementation")
    project_users = _get_project_users(project_name)
    permissions = _get_project_user_permissions(project_name)
    managed_permissions = _get_managed_project_user_permissions(project_name)

    permissions_by_user: dict[str, list[dict]] = {}
    for permission in permissions:
        user = permission.get("user")
        if not user:
            continue
        permissions_by_user.setdefault(user, []).append(permission)

    created: list[str] = []
    removed: list[str] = []

    for user in sorted(project_users):
        if user in permissions_by_user:
            continue
        _create_user_permission(project_name, user, dry_run=dry_run)
        created.append(user)

    managed_by_user: dict[str, list[dict]] = {}
    for permission in managed_permissions:
        user = permission.get("user")
        if not user:
            continue
        managed_by_user.setdefault(user, []).append(permission)

    for user, user_permissions in managed_by_user.items():
        if user in project_users:
            continue
        for permission in user_permissions:
            _delete_user_permission(permission["name"], dry_run=dry_run)
            removed.append(permission["name"])

    summary = {
        "project": project_name,
        "project_users": sorted(project_users),
        "created": created,
        "removed": removed,
        "dry_run": dry_run,
    }
    logger.info(summary)
    return summary


def reconcile_all_projects(dry_run: bool = False, limit: int | None = None) -> dict:
    """Reconcile User Permissions for all projects."""
    logger = frappe.logger("erp_implementation")
    project_names = frappe.get_all("Project", pluck="name", limit=limit)

    aggregate = {
        "projects": [],
        "created_count": 0,
        "removed_count": 0,
        "errors": [],
        "dry_run": dry_run,
    }

    for project_name in project_names:
        try:
            result = sync_project_user_permissions(project_name, dry_run=dry_run)
        except Exception:
            error = {
                "project": project_name,
                "message": frappe.get_traceback(),
            }
            aggregate["errors"].append(error)
            logger.error(error)
            continue

        aggregate["projects"].append(result)
        aggregate["created_count"] += len(result.get("created", []))
        aggregate["removed_count"] += len(result.get("removed", []))

    logger.info(aggregate)
    return aggregate


def reconcile_all_projects_dry_run(limit: int | None = None) -> dict:
    """Reconcile all projects without writing changes."""
    return reconcile_all_projects(dry_run=True, limit=limit)


def on_project_update(doc, method: str | None = None) -> None:
    """Doc event handler for Project updates."""
    if not doc or not doc.name:
        return

    sync_project_user_permissions(doc.name)
