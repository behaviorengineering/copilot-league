"""detect-secrets exclude regex — anchored path segments only."""

from __future__ import annotations

# Do not use bare ``build`` / ``dist`` — those match rebuild.py and distribute.py.
DETECT_SECRETS_EXCLUDE = (
    r"(^|/)\.venv($|/)|(^|/)build($|/)|(^|/)dist($|/)|(^|/)\.git($|/)|\.egg-info"
)
