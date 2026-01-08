### Erp Implementation

In8.pro ERP Default Configuration Package

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app erp_implementation
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/erp_implementation
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### Project permissions sync

This app enforces Project visibility by syncing Project Users (Project.users → Project User.user)
to User Permissions (`Allow=Project`). The Project users table is the source of truth.
User Permissions created by this sync are marked via Custom Fields on User Permission:
`managed_by_erp_implementation=1` and `erp_implementation_source="Project.users"` so they can be
safely cleaned up without touching manually-created permissions.

**How it works**

- Project `on_update` triggers a sync for that project.
- A daily scheduler job reconciles all projects to ensure drift is corrected.

**Run reconciliation manually**

```bash
bench --site <site> execute erp_implementation.project_permissions.sync.reconcile_all_projects
```

To simulate changes without writing:

```bash
bench --site <site> execute erp_implementation.project_permissions.sync.reconcile_all_projects_dry_run
```

**Rollback notes**

- Disable the hooks by removing the Project doc_events and scheduler entry in `hooks.py`.
- Managed User Permissions can be deleted by filtering on `managed_by_erp_implementation=1`
  and `erp_implementation_source="Project.users"`. Manually-created User Permissions are not touched by this app.

### License

mit
