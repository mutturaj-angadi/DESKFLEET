"""
tests.conftest
===============
Sets required environment variables *before* any `app.*` module is
imported, since `app.config.settings` is instantiated once at import
time. Also points the database at a temp file so tests never touch
a real deskfleet.db.
"""

import os
import tempfile

os.environ.setdefault("LLM_API_KEY", "test-key-not-real")
os.environ.setdefault("MOCK_API_BASE_URL", "http://localhost:9000")
# Tests must not send telemetry because a developer's local .env can enable
# LangSmith tracing.  This is set before app.config loads that file.
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")

_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_PATH"] = _tmp_db.name
