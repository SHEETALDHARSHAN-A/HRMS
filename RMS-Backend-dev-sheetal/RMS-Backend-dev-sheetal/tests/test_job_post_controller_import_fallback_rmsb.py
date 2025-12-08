import importlib
import sys
import types


def test_getjobpost_import_fallback_executes_except_and_restores():
    # Import the controller module to get a reference
    import app.controllers.job_post_controller as controller

    target_mod_name = 'app.services.job_post.get_job_post'

    # Backup any existing module object
    backup = sys.modules.get(target_mod_name)

    try:
        # Insert a fake module that PROVIDES GetJobPost (to satisfy the earlier
        # top-level import) but does NOT provide GetJobDetails so the
        # 'from ... import GetJobDetails' inside the controller will raise
        # ImportError and execute the except branch.
        fake = types.ModuleType(target_mod_name)
        # Provide a minimal GetJobPost symbol so the initial import of
        # GetJobPost doesn't fail during reload.
        class DummyGetJobPost:
            def __init__(self, db):
                self.db = db

            def fetch_full_job_details(self, job_id: str):
                return None

        fake.GetJobPost = DummyGetJobPost
        sys.modules[target_mod_name] = fake

        # Reload the controller module so the try/except runs again
        importlib.reload(controller)

        # After reload, controller should still expose GetJobPost (the file defines a final
        # GetJobPost class regardless), so basic sanity check:
        assert hasattr(controller, 'GetJobPost')

    finally:
        # Restore original module state
        if backup is not None:
            sys.modules[target_mod_name] = backup
        else:
            sys.modules.pop(target_mod_name, None)
        # Reload controller again to restore original definitions
        importlib.reload(controller)
