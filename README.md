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

This app enforces Project visibility by syncing Project Team membership to User Permissions
(`Allow=Project`). The Project Team table is the source of truth. User Permissions created
by this sync are marked with the description prefix `erp_implementation: managed` so they can
be safely cleaned up without touching manually-created permissions.

**How it works**

- Project `on_update` (and `after_insert`) triggers a sync for that project.
- A daily scheduler job reconciles all projects to ensure drift is corrected.

**Run reconciliation manually**

```bash
bench --site <site> execute erp_implementation.project_permissions.sync.reconcile_all_projects
```

To simulate changes without writing:

```bash
bench --site <site> execute erp_implementation.project_permissions.sync.reconcile_all_projects --kwargs \"{\\\"dry_run\\\": true}\"
```

**Rollback notes**

- Disable the hooks by removing the Project doc_events and scheduler entry in `hooks.py`.
- Managed User Permissions can be deleted by filtering on descriptions that begin with
  `erp_implementation: managed`. Manually-created User Permissions are not touched by this app.

### License

mit
