import subprocess
import sys
import os
import pytest


@pytest.mark.skipif(os.getenv("RUN_INTEGRATION_TESTS") != "1", reason="Integration tests disabled by default; set RUN_INTEGRATION_TESTS=1 to enable")
def test_get_search_autocomplete_suggestions_integration():
    """
    Run the integration runner in a fresh Python process to avoid SQLAlchemy
    MetaData duplication that occurs when reloading ORM modules in the
    same interpreter process.
    """
    runner = os.path.join("tests", "integration", "run_job_post_integration.py")
    # Use the same Python interpreter
    result = subprocess.run([sys.executable, runner], capture_output=True, text=True)
    if result.returncode != 0:
        print("Runner stdout:\n", result.stdout)
        print("Runner stderr:\n", result.stderr)
    assert result.returncode == 0, "Integration runner failed; see stdout/stderr above"
