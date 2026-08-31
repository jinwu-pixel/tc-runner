"""Public entrypoint for the BUG27084 AppWidget stale-provider harness."""

from __future__ import annotations

from appwidget_stale_provider_cli import main, render_plan
from appwidget_stale_provider_orchestrator import (
    arm,
    bind,
    capture,
    restore,
    trigger,
    verify,
)
from appwidget_stale_provider_parsers import (
    parse_adb_devices,
    parse_appwidget_state,
    parse_crash_signature,
    parse_home_role,
    parse_package_state,
)


if __name__ == "__main__":
    raise SystemExit(main())
