"""Invoke collection for local Python quality audits.

Not CI: no build, publish, sonar, pip-audit, pytest, or venv bootstrap.
"""

from __future__ import annotations

from invoke import Collection  # type: ignore[attr-defined]

from tasks.quality import format, lint
from tasks.security import security_code, security_secrets

ns = Collection()
ns.add_task(lint)
ns.add_task(format)

sec_coll = Collection("sec")
sec_coll.add_task(security_code, name="code")
sec_coll.add_task(security_secrets, name="secrets")
ns.add_collection(sec_coll)
