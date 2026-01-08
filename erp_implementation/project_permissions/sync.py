import frappe

MANAGED_PREFIX = "erp_implementation: managed (source=Project.users)"
logger = frappe.logger("erp_implementation")

def _get_project_users(project_name: str) -> set[str]:
    # Confirmed schema:
    # Project has table field `users` -> child doctype `Project User`
    # Child field that stores user is `user` (Link -> User)
    rows = frappe.get_all(
        "Project User",
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
    out: dict[str, str] = {}
    for p in perms:
        if (p.get("description") or "").startswith(MANAGED_PREFIX) and p.get("user"):
            out[p["user"]] = p["name"]
    return out

def sync_project_user_permissions(project_name: str, dry_run: bool = False) -> dict:
    users = _get_project_users(project_name)
    managed = _get_managed_user_permissions_for_project(project_name)

    to_create = sorted(users - set(managed.keys()))
    to_remove = sorted(set(managed.keys()) - users)

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
            "description": MANAGED_PREFIX,
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
        "source_users": len(users),
        "managed_permissions": len(managed),
        "created": created,
        "removed": removed,
        "dry_run": dry_run,
    }
    logger.info(summary)
    return summary

def reconcile_all_projects(dry_run: bool = False, limit: int | None = None) -> dict:
    projects = frappe.get_all("Project", fields=["name"], limit=limit)
    results = []
    errors = []

    for p in projects:
        name = p["name"]
        try:
            results.append(sync_project_user_permissions(name, dry_run=dry_run))
        except Exception as e:
            logger.exception(f"Failed reconcile for Project {name}")
            errors.append({"project": name, "error": str(e)})

    return {"count": len(projects), "errors": errors, "results": results}
