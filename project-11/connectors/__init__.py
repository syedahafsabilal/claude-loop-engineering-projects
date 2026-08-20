"""Connector registry for project-11.

A connector is the mechanism a routine uses to reach the outside world.
The registry below is the *final, pruned* set. Unused connectors (github,
email) were removed because this implementation is fully local.
"""

REQUIRED_CONNECTORS = ["local_http"]


def list_connector_modules(base_dir):
    """Return connector module file names present on disk (for inspection)."""
    import os
    conn_dir = os.path.join(base_dir, "connectors")
    if not os.path.isdir(conn_dir):
        return []
    return sorted(
        f for f in os.listdir(conn_dir)
        if f.endswith(".py") and not f.startswith("__")
    )
