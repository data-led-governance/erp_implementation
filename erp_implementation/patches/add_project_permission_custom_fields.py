"""Create Custom Fields for managed Project User Permissions."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


CUSTOM_FIELDS = {
    "User Permission": [
        {
            "fieldname": "managed_by_erp_implementation",
            "label": "Managed By ERP Implementation",
            "fieldtype": "Check",
            "insert_after": "allow",
            "default": 0,
        },
        {
            "fieldname": "erp_implementation_source",
            "label": "ERP Implementation Source",
            "fieldtype": "Data",
            "insert_after": "managed_by_erp_implementation",
        },
    ]
}


def execute() -> None:
    if not frappe.db.exists("DocType", "User Permission"):
        return

    create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
