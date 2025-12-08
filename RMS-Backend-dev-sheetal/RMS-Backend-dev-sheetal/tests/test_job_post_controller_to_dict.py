import pytest

from app.controllers.job_post_controller import _to_dict


def test_model_dump_works_returns_dict():
    class Obj:
        def model_dump(self):
            return {"a": 1}

    o = Obj()
    assert _to_dict(o) == {"a": 1}


def test_model_dump_raises_but_dict_works():
    class Obj:
        def model_dump(self):
            raise RuntimeError("nope")

        def dict(self):
            return {"b": 2}

    o = Obj()
    # model_dump raises (covered), dict succeeds -> returns dict
    assert _to_dict(o) == {"b": 2}


def test_dict_raises_returns_original_object():
    class Obj:
        def dict(self):
            raise RuntimeError("bad dict")

    o = Obj()
    res = _to_dict(o)
    # since dict raised and it's not a dict instance, _to_dict should return the original object
    assert res is o


def test_both_methods_raise_returns_original_object():
    class Obj:
        def model_dump(self):
            raise RuntimeError("bad dump")

        def dict(self):
            raise RuntimeError("bad dict")

    o = Obj()
    res = _to_dict(o)
    assert res is o


def test_input_is_dict_returned_directly():
    d = {"x": 1}
    assert _to_dict(d) is d
