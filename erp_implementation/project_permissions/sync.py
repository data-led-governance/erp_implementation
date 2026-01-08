import frappe

MANAGED_PREFIX = "erp_implementation: managed"
logger = frappe.logger("erp_implementation")

def _get_project_team_users(project_name: str) -> set[str]:
    rows = frappe.get_all(
        "Project Team",
        filters={"parent": project_name, "parenttype": "Project"},
        fields=["user"],
    )
    return {r.get("user") for r in rows if r.get("user")}

def _get_managed_user_permissions_for_project(project_name: str) -> dict[str, str]:
    perms = frappe.get_all(
        "User Permission",
        filters={"allow": "Project", "for_value": project_name},
        fields=["name", "user", "description"],
    )
    out = {}
    for p in perms:
        if (p.get("description") or "").startswith(MANAGED_PREFIX) and p.get("user"):
            out[p["user"]] = p["name"]
    return out

def sync_project_user_permissions(project_name: str, dry_run: bool = False) -> dict:
    team_users = _get_project_team_users(project_name)
    managed = _get_managed_user_permissions_for_project(project_name)

    to_create = sorted(team_users - set(managed.keys()))
    to_remove = sorted(set(managed.keys()) - team_users)

    created, removed = [], []

    for user in to_create:
        if dry_run:
            created.append({"user": user, "project": project_name, "dry_run": True})
            continue
        doc = frappe.get_doc({
            "doctype": "User Permission",
            "user": user,
            "allow": "Project",
            "for_value": project_name,
            "description": f"{MANAGED_PREFIX} (source=Project Team)",
        })
        doc.insert(ignore_permissions=True)
        created.append(doc.name)

    for user in to_remove:
        perm_name = managed[user]
        if dry_run:
            removed.append({"user": user, "user_permission": perm_name, "dry_run": True})
            continue
        frappe.delete_doc("User Permission", perm_name, ignore_permissions=True, force=True)
        removed.append(perm_name)

    if not dry_run:
        frappe.db.commit()

    summary = {
        "project": project_name,
        "team_users": len(team_users),
        "managed_permissions": len(managed),
        "created": created,
        "removed": removed,
    }
    logger.info(summary)
    return summary

def reconcile_all_projects(dry_run: bool = False, limit: int | None = None) -> dict:
    projects = frappe.get_all("Project", fields=["name"], limit=limit)
    results = []
    for p in projects:
        try:
            results.append(sync_project_user_permissions(p["name"], dry_run=dry_run))
        except Exception:
            logger.exception(f"Failed reconcile for Project {p[name]}")
            results.append({"project": p["name"], "error": True})
    return {"count": len(projects), "results": results}
