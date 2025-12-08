import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock


@pytest.mark.asyncio
async def test_to_dict_variants():
    import app.controllers.job_post_controller as jpc

    # None
    assert jpc._to_dict(None) is None

    # Pydantic-like model_dump
    class PD:
        def model_dump(self):
            return {"a": 1}

    assert jpc._to_dict(PD()) == {"a": 1}

    # dict
    d = {"b": 2}
    assert jpc._to_dict(d) == d

    # fallback object
    class X:
        pass

    x = X()
    assert jpc._to_dict(x) is x


@pytest.mark.asyncio
async def test_get_job_by_id_owner_and_populates_flags(monkeypatch):
    import app.controllers.job_post_controller as jpc

    async def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id):
            return {"user_id": "u1", "job_id": job_id, "job_title": "T"}

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    # request with current user
    req = SimpleNamespace()
    req.state = SimpleNamespace(user={"user_id": "u1", "sub": "u1"})

    res = await jpc.get_job_by_id_controller('00000000-0000-0000-0000-000000000001', request=req)
    assert res.get('success') is True
    job = res.get('data').get('job')
    assert job.get('is_own_job') is True
    assert 'user_id' not in job


@pytest.mark.asyncio
async def test_get_active_jobs_logger_exception(monkeypatch):
    import app.controllers.job_post_controller as jpc

    async def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass

        def list_active(self):
            # return list with invalid element to trigger logger.info exception
            return [1, 2]

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    res = await jpc.get_active_jobs_controller()
    assert res.get('success') is True


@pytest.mark.asyncio
async def test_delete_job_post_controller_model_dump(monkeypatch):
    import app.controllers.job_post_controller as jpc

    async def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id):
            return {"user_id": "auth-user-id", "job_id": job_id}

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    class RespObj:
        def model_dump(self):
            return {"success": True, "data": {"job_id": "abc"}}

    class FakeUpdate:
        def __init__(self, db):
            pass

        def delete_job_post(self, job_id):
            return RespObj()

    monkeypatch.setattr(jpc, 'UpdateJobPost', FakeUpdate)

    fake_request = SimpleNamespace()
    fake_request.state = SimpleNamespace(user={"user_id": "auth-user-id", "sub": "auth-user-id"})

    res = await jpc.delete_job_post_controller('abc', request=fake_request)
    assert isinstance(res, dict)
    assert res.get('success') is True


@pytest.mark.asyncio
async def test_delete_job_posts_batch_hard_delete_success_and_none(monkeypatch):
    import app.controllers.job_post_controller as jpc

    async def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    # Non-super user, valid ids owned by same user
    class FakeReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id):
            return {"job_id": job_id, "created_by_user_id": "u1"}

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    fake_request = SimpleNamespace()
    fake_request.state = SimpleNamespace(user={"user_id": "u1", "sub": "u1"})

    # UpdateJobPost.delete_jobs_batch returns None-> fallback to hard_delete
    class FakeUpdate:
        def __init__(self, db):
            pass

        def delete_jobs_batch(self, job_ids):
            return None

    monkeypatch.setattr(jpc, 'UpdateJobPost', FakeUpdate)

    async def fake_hard_delete(db, job_ids):
        return 2

    monkeypatch.setattr(jpc, 'hard_delete_jobs_batch', fake_hard_delete)

    res = await jpc.delete_job_posts_batch_controller(['x', 'y'], request=fake_request)
    assert res.get('success') is True
    assert res.get('data').get('rows_affected') == 2

    # Case when affected == 0 -> return error
    async def fake_hard_delete_zero(db, job_ids):
        return 0

    monkeypatch.setattr(jpc, 'hard_delete_jobs_batch', fake_hard_delete_zero)
    res2 = await jpc.delete_job_posts_batch_controller(['x', 'y'], request=fake_request)
    assert res2.get('success') is False
    assert res2.get('status_code') == 400


@pytest.mark.asyncio
async def test_candidate_stats_success(monkeypatch):
    import app.controllers.job_post_controller as jpc

    class FakeRepo:
        def __init__(self, db):
            pass

        async def count_by_status(self, job_id, status=None):
            return {"applied": 1}.get(status, 0) or 2

    async def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(jpc, 'get_db', fake_get_db)
    # monkeypatch the repo import target used within function
    monkeypatch.setattr('app.db.repository.profile_repository.ProfileRepository', FakeRepo)

    res = await jpc.candidate_stats_controller('00000000-0000-0000-0000-000000000002')
    assert res.get('success') is True
    assert 'profile_counts' in res.get('data')


@pytest.mark.asyncio
async def test_search_suggestions_failure(monkeypatch):
    import app.controllers.job_post_controller as jpc

    class BadSearch:
        async def get_suggestions(self):
            raise RuntimeError('err')

    bad = BadSearch()
    res = await jpc.get_search_suggestions_controller(search_service=bad)
    assert res.get('success') is False
    assert res.get('status_code') == 500


@pytest.mark.asyncio
async def test_getjobpost_imported_impl_and_fallback(monkeypatch):
    import importlib
    import sys
    import types

    # Backup original modules
    orig_controller = sys.modules.get('app.controllers.job_post_controller')
    orig_getjob_mod = sys.modules.get('app.services.job_post.get_job_post')

    try:
        # Provide a fake module with GetJobDetails that has fetch_full_job_details
        fake_mod = types.ModuleType('app.services.job_post.get_job_post')
        class ImplGood:
            def __init__(self, db):
                self.db = db
            def fetch_full_job_details(self, job_id):
                return {'job_id': job_id, 'ok': True}
        fake_mod.GetJobDetails = ImplGood
        sys.modules['app.services.job_post.get_job_post'] = fake_mod

        # Force re-import of controller to pick up fake module
        if 'app.controllers.job_post_controller' in sys.modules:
            del sys.modules['app.controllers.job_post_controller']
        mod = importlib.import_module('app.controllers.job_post_controller')
        # should delegate to impl
        gp = mod.GetJobPost(None)
        res = gp.fetch_full_job_details('jid')
        assert res.get('ok') is True

        # Now fake module with GetJobDetails but no fetch_full_job_details -> fallback reader
        fake_mod2 = types.ModuleType('app.services.job_post.get_job_post')
        class ImplBad:
            def __init__(self, db):
                self.db = db
        fake_mod2.GetJobDetails = ImplBad
        sys.modules['app.services.job_post.get_job_post'] = fake_mod2

        # reload controller
        if 'app.controllers.job_post_controller' in sys.modules:
            del sys.modules['app.controllers.job_post_controller']
        mod2 = importlib.import_module('app.controllers.job_post_controller')
        # monkeypatch reader to return known payload
        class FakeReader:
            def __init__(self, db):
                pass
            def get_job(self, job_id):
                return {'job_id': job_id, 'ok': 'reader'}
        monkeypatch.setattr(mod2, 'JobPostReader', FakeReader)
        gp2 = mod2.GetJobPost(None)
        # fetch_full_job_details is sync -> returns reader dict
        res2 = gp2.fetch_full_job_details('j2')
        assert res2.get('ok') == 'reader'

    finally:
        # Restore module state
        if orig_getjob_mod is not None:
            sys.modules['app.services.job_post.get_job_post'] = orig_getjob_mod
        else:
            sys.modules.pop('app.services.job_post.get_job_post', None)
        if orig_controller is not None:
            sys.modules['app.controllers.job_post_controller'] = orig_controller


@pytest.mark.asyncio
async def test_update_job_post_debug_model_dump_raises(monkeypatch):
    import app.controllers.job_post_controller as jpc
    from datetime import datetime
    from app.schemas.update_jd_request import UpdateJdRequest, SkillSchema

    async def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    # job_details.model_dump raises
    class BadJob:
        def model_dump(self):
            raise RuntimeError('boom')
    bad = BadJob()

    # reader returns None and Update service returns success
    class FakeReader:
        def __init__(self, db):
            pass
        def get_job(self, job_id):
            return None
    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    class FakeUpdate:
        def __init__(self, db):
            pass
        def update_job_post(self, job_details=None, job_id=None, creator_id=None):
            return {"success": True, "data": {"job_details": {"id": "1"}}}
    monkeypatch.setattr(jpc, 'UpdateJobPost', FakeUpdate)

    fake_request2 = SimpleNamespace()
    fake_request2.state = SimpleNamespace(user={"user_id": "creator", "sub": "creator"})
    res = await jpc.update_job_post_controller(job_details=bad, job_id=None, request=fake_request2)
    assert res.get('success') is True


@pytest.mark.asyncio
async def test_analyze_job_details_controller_http_exc(monkeypatch):
    import app.controllers.job_post_controller as jpc
    from fastapi import HTTPException
    from app.schemas.analyze_jd_request import AnalyzeJdRequest

    class BadAnalyzer:
        async def analyze_job_details(self, job_details=None):
            raise HTTPException(status_code=422, detail='bad')

    monkeypatch.setattr(jpc, 'get_analyze_jd_service', lambda: BadAnalyzer())
    req = AnalyzeJdRequest(job_title='x', job_description='y')
    res = await jpc.analyze_job_details_controller(req)
    assert res.get('success') is False
    assert res.get('status_code') == 422


@pytest.mark.asyncio
async def test_delete_job_post_controller_fallback_success(monkeypatch):
    import app.controllers.job_post_controller as jpc

    async def fake_get_db():
        yield SimpleNamespace()
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass
        def get_job(self, job_id):
            return {"user_id": "auth-user-id", "job_id": job_id}
    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    class FakeUpdateNone:
        def __init__(self, db):
            pass
        def delete_job_post(self, job_id):
            return None
    monkeypatch.setattr(jpc, 'UpdateJobPost', FakeUpdateNone)

    fake_request = SimpleNamespace()
    fake_request.state = SimpleNamespace(user={"user_id": "auth-user-id", "sub": "auth-user-id"})

    res = await jpc.delete_job_post_controller('abc', request=fake_request)
    assert res.get('success') is True
    assert res.get('data').get('job_id') == 'abc'


@pytest.mark.asyncio
async def test_get_all_jobs_controller_reader_raises(monkeypatch):
    import app.controllers.job_post_controller as jpc

    async def fake_get_db():
        yield SimpleNamespace()
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class BadReader:
        def __init__(self, db):
            pass
        def list_all(self):
            raise RuntimeError('boom')
    monkeypatch.setattr(jpc, 'JobPostReader', BadReader)

    res = await jpc.get_all_jobs_controller()
    # can be JSONResponse or dict
    if hasattr(res, 'status_code'):
        assert res.status_code == 500
    else:
        assert res.get('status_code') == 500 or res.get('success') is False


@pytest.mark.asyncio
async def test_update_job_post_controller_faulty_service_dict(monkeypatch):
    import app.controllers.job_post_controller as jpc
    from datetime import datetime
    from app.schemas.update_jd_request import UpdateJdRequest, SkillSchema

    async def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    # Faulty dict subclass that raises on get
    class FaultyDict(dict):
        def get(self, key, default=None):
            raise RuntimeError('faulty get')

    class ServiceObj:
        def dict(self):
            return FaultyDict({'job_details': {'id': '1'}})

    class FakeUpdate:
        def __init__(self, db):
            pass
        def update_job_post(self, job_details=None, job_id=None, creator_id=None):
            return ServiceObj()

    monkeypatch.setattr(jpc, 'UpdateJobPost', FakeUpdate)
    monkeypatch.setattr(jpc, 'JobPostReader', lambda db: SimpleNamespace(get_job=lambda job_id: None))

    fake_request = SimpleNamespace()
    fake_request.state = SimpleNamespace(user={"user_id": "creator", "sub": "creator"})
    job = UpdateJdRequest(job_title='t', job_description='d', description_sections=[], active_till=datetime.now(), job_location='loc', skills_required=[SkillSchema(skill='s', weightage=1)])

    res = await jpc.update_job_post_controller(job_details=job, job_id=None, request=fake_request)
    # Faulty dict get() raising should cause controller to return server error
    assert res.get('success') is False
    assert res.get('status_code') == 500


@pytest.mark.asyncio
async def test_get_public_job_by_id_skills_and_wfh(monkeypatch):
    import app.controllers.job_post_controller as jpc

    async def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass
        def get_job(self, job_id):
            return {
                'job_id': job_id,
                'is_active': True,
                'job_title': 'T',
                'job_location': 'L',
                'work_from_home': True,
                'skills_required': [{'skill': 'Python'}, {'skill': 'Django'}],
            }

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)
    res = await jpc.get_public_job_by_id_controller('abc')
    assert res.get('success') is True
    data = res.get('data').get('job')
    assert data.get('skills') == ['Python', 'Django']
    assert data.get('wfh') is True


@pytest.mark.asyncio
async def test_search_public_jobs_controller_search_service_raises(monkeypatch):
    import app.controllers.job_post_controller as jpc

    class BadSearch2:
        async def search_jobs(self, **kwargs):
            raise RuntimeError('search fail')

    res = await jpc.search_public_jobs_controller(search_service=BadSearch2(), role='dev', skills=None, locations=None)
    assert res.get('success') is False
    assert res.get('status_code') == 500


@pytest.mark.asyncio
async def test_analyze_job_details_controller_generic_exc(monkeypatch):
    import app.controllers.job_post_controller as jpc
    from app.schemas.analyze_jd_request import AnalyzeJdRequest

    class BadAnalyzer2:
        async def analyze_job_details(self, job_details=None):
            raise RuntimeError('boom')

    monkeypatch.setattr(jpc, 'get_analyze_jd_service', lambda: BadAnalyzer2())
    req = AnalyzeJdRequest(job_title='x', job_description='y')
    res = await jpc.analyze_job_details_controller(req)
    assert res.get('success') is False
    assert res.get('status_code') == 500

@pytest.mark.asyncio
async def test_getjobpost_imported_impl_init_raises(monkeypatch):
    import importlib
    import sys
    import types

    orig_controller = sys.modules.get('app.controllers.job_post_controller')
    orig_getjob_mod = sys.modules.get('app.services.job_post.get_job_post')
    try:
        # Module where class __init__ raises
        fake_mod = types.ModuleType('app.services.job_post.get_job_post')
        class ImplRaise:
            def __init__(self, db):
                raise RuntimeError('init fail')
        fake_mod.GetJobDetails = ImplRaise
        sys.modules['app.services.job_post.get_job_post'] = fake_mod

        if 'app.controllers.job_post_controller' in sys.modules:
            del sys.modules['app.controllers.job_post_controller']
        mod = importlib.import_module('app.controllers.job_post_controller')
        # instantiate GetJobPost, which should set _impl to None due to exception
        gp = mod.GetJobPost(None)
        assert getattr(gp, '_impl', 'NOIMPL') is None
    finally:
        if orig_getjob_mod is not None:
            sys.modules['app.services.job_post.get_job_post'] = orig_getjob_mod
        else:
            sys.modules.pop('app.services.job_post.get_job_post', None)
        if orig_controller is not None:
            sys.modules['app.controllers.job_post_controller'] = orig_controller

@pytest.mark.asyncio
async def test_get_my_jobs_controller_success(monkeypatch):
    import app.controllers.job_post_controller as jpc

    async def fake_get_db():
        yield SimpleNamespace()
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass
        async def list_by_user(self, user_id):
            return [{'job_id': 'x', 'user_id': user_id}]
        async def list_all(self):
            return []
    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    fake_request = SimpleNamespace()
    fake_request.state = SimpleNamespace(user={"user_id": "u1", "sub": "u1"})
    res = await jpc.get_my_jobs_controller(fake_request)
    assert res.get('success') is True

@pytest.mark.asyncio
async def test_get_my_agent_jobs_controller_interview_attrs(monkeypatch):
    import app.controllers.job_post_controller as jpc

    async def fake_get_db():
        yield SimpleNamespace()
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class Conf:
        def __init__(self, id):
            self.id = id
            self.job_id = 'jid'
            self.round_list_id = 'r'
            self.round_name = 'rname'
            self.round_focus = 'focus'
            self.persona = 'p'
            self.key_skills = []
            self.custom_questions = []
            self.forbidden_topics = []
            self.interviewMode = 'video'
            self.interviewTime = 30

    class JobOrm:
        def __init__(self):
            self.agent_configs = [Conf(1)]

    def fake_serialize(job):
        return {'job_id': 'jid'}

    monkeypatch.setattr(jpc, 'serialize_admin_job', fake_serialize)
    async def fake_get_agent(db, user_id):
        return [JobOrm()]
    monkeypatch.setattr(jpc, 'get_agent_jobs_by_user_id', fake_get_agent)

    fake_request = SimpleNamespace()
    fake_request.state = SimpleNamespace(user={"user_id": "u1", "sub": "u1"})
    res = await jpc.get_my_agent_jobs_controller(fake_request)
    assert res.get('success') is True
    jobs = res.get('data').get('jobs')
    assert jobs and 'agentRounds' in jobs[0]

@pytest.mark.asyncio
async def test_toggle_job_status_controller_service_model_dump(monkeypatch):
    import app.controllers.job_post_controller as jpc

    async def fake_get_db():
        yield SimpleNamespace()
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass
        def get_job(self, job_id):
            return {'job_id': job_id, 'created_by_user_id': 'u1', 'is_active': True}
    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    class RespObj:
        def model_dump(self):
            return {'success': True, 'data': {'job_id': 'jid'}}
    class FakeUpdate:
        def __init__(self, db):
            pass
        def toggle_status(self, job_id, is_active):
            return RespObj()
    monkeypatch.setattr(jpc, 'UpdateJobPost', FakeUpdate)
    fake_request = SimpleNamespace()
    fake_request.state = SimpleNamespace(user={"user_id": "u1", "sub": "u1"})
    res = await jpc.toggle_job_status_controller('jid', True, request=fake_request)
    assert res.get('success') is True

@pytest.mark.asyncio
async def test_delete_job_posts_batch_service_returns_dict_non_super(monkeypatch):
    import app.controllers.job_post_controller as jpc

    async def fake_get_db():
        yield SimpleNamespace()
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass
        def get_job(self, job_id):
            return {"job_id": job_id, "created_by_user_id": "u1"}
    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    class FakeUpdate:
        def __init__(self, db):
            pass
        def delete_jobs_batch(self, job_ids):
            return {"success": True, "rows_affected": len(job_ids)}
    monkeypatch.setattr(jpc, 'UpdateJobPost', FakeUpdate)

    fake_request = SimpleNamespace()
    fake_request.state = SimpleNamespace(user={"user_id": "u1", "sub": "u1"})
    res = await jpc.delete_job_posts_batch_controller(['a','b'], request=fake_request)
    assert res.get('success') is True
