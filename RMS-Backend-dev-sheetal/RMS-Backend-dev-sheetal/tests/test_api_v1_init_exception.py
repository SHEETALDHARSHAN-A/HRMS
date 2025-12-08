import importlib
import pkgutil
import sys


def test_v1_init_import_exception(monkeypatch, capsys):
    """Force an import failure for a submodule so the except block
    in `app.api.v1.__init__` executes (traceback.print_exc()).
    """
    # fake iter_modules to yield one module name
    def fake_iter_modules(path):
        yield (None, "fake_bad_mod", False)

    orig_import = importlib.import_module

    def fake_import(name, package=None):
        # Raise only for the specific target module name
        if name == "app.api.v1.fake_bad_mod":
            raise Exception("simulated import failure")
        return orig_import(name, package)

    monkeypatch.setattr(pkgutil, "iter_modules", fake_iter_modules)
    monkeypatch.setattr(importlib, "import_module", fake_import)

    # Ensure a fresh import to execute the top-level code in the module
    sys.modules.pop("app.api.v1", None)

    # Import should succeed overall; the inner import will raise and be caught
    mod = importlib.import_module("app.api.v1")

    captured = capsys.readouterr()
    # The except block calls traceback.print_exc(), which writes to stderr.
    assert "simulated import failure" in captured.err or "Traceback" in captured.err
