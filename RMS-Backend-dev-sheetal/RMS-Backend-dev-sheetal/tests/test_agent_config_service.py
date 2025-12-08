import pytest
import uuid
from types import SimpleNamespace
from fastapi import HTTPException, status

from app.services.config_service.agent_config_service import AgentConfigService


def make_fake_db(get_result=None, execute_result=None):
    class FakeDB:
        def __init__(self):
            self._get = get_result
            self._exec = execute_result

        async def get(self, model, pk):
            return self._get

        async def execute(self, stmt):
            return self._exec

        async def commit(self):
            return None

    return FakeDB()


def test_invalid_uuid_raises():
    svc = AgentConfigService(db=object())
    with pytest.raises(HTTPException) as ei:
        # invalid job id
        pytest.run = None
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            svc.update_job_agent_config(job_id="not-a-uuid", user_id="also-bad", rounds_data=[])
        )
    assert ei.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_job_not_found_raises_404():
    fake_db = make_fake_db(get_result=None)
    svc = AgentConfigService(db=fake_db)
    with pytest.raises(HTTPException) as ei:
        await svc.update_job_agent_config(job_id=str(uuid.uuid4()), user_id=str(uuid.uuid4()), rounds_data=[])
    assert ei.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_forbidden_when_user_mismatch():
    # Create a fake job object with a different user_id
    class JobObj:
        def __init__(self, user_id):
            self.user_id = user_id

    other_user = uuid.uuid4()
    job = JobObj(user_id=other_user)
    fake_db = make_fake_db(get_result=job)
    svc = AgentConfigService(db=fake_db)
    # Call with a different user id (not matching job.user_id)
    with pytest.raises(HTTPException) as ei:
        await svc.update_job_agent_config(job_id=str(uuid.uuid4()), user_id=str(uuid.uuid4()), rounds_data=[])
    assert ei.value.status_code == status.HTTP_403_FORBIDDEN
import uuid
import pytest
from unittest.mock import AsyncMock
from app.services.config_service.agent_config_service import AgentConfigService
from app.schemas.config_request import AgentRoundConfigUpdate
from fastapi import HTTPException
from datetime import datetime


class FakeJob:
    def __init__(self, user_id):
        self.user_id = user_id


class FakeResultForExecute:
    def __init__(self, scalars_list=None, scalar_one_obj=None):
        self._scalars_list = scalars_list
        self._scalar_one_obj = scalar_one_obj

    def scalars(self):
        class _S:
            def __init__(self, xs):
                self._xs = xs
            def all(self):
                return self._xs
        return _S(self._scalars_list)

    def scalar_one(self):
        return self._scalar_one_obj


class FakeConfig:
    def __init__(self, id, job_id, round_list_id, round_name):
        self.id = id
        self.job_id = job_id
        self.round_list_id = round_list_id
        self.round_name = round_name
        self.round_focus = 'focus'
        self.persona = 'alex'
        self.key_skills = ['python']
        self.custom_questions = []
        self.forbidden_topics = []
        self.score_distribution = {}


@pytest.mark.asyncio
async def test_update_job_agent_config_inserts_new_config():
    # Arrange: create fake DB and job
    job_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    job_uuid = uuid.UUID(job_id)
    user_uuid = uuid.UUID(user_id)

    round_list_id = str(uuid.uuid4())
    round_data = AgentRoundConfigUpdate(jobId=job_id, roundListId=round_list_id, roundName='Round 1', roundFocus='focus', persona='alex')

    # Fake DB
    class FakeDB:
        async def get(self, model, uuid_val):
            return FakeJob(user_uuid)

        async def execute(self, stmt):
            # First call is for existing configs: return empty
            # Second call will be for the insert and return object that scalar_one returns FakeConfig
            if not hasattr(self, 'called'):
                self.called = 1
                return FakeResultForExecute(scalars_list=[])
            else:
                cfg = FakeConfig(id=uuid.uuid4(), job_id=job_uuid, round_list_id=uuid.UUID(round_list_id), round_name='Round 1')
                return FakeResultForExecute(scalar_one_obj=cfg)

        async def commit(self):
            return None

    svc = AgentConfigService(FakeDB())
    # Act
    result = await svc.update_job_agent_config(job_id, user_id, [round_data])
    # Assert
    assert isinstance(result, list)
    assert result[0]['jobId'] == job_id
    assert result[0]['roundName'] == 'Round 1'


@pytest.mark.asyncio
async def test_update_job_agent_config_invalid_job_id():
    svc = AgentConfigService(AsyncMock())
    with pytest.raises(HTTPException) as exc:
        await svc.update_job_agent_config('not-uuid', 'u1', [])
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_job_agent_config_job_not_found():
    class FakeDB:
        async def get(self, model, uuid_val):
            return None

    svc = AgentConfigService(FakeDB())
    with pytest.raises(HTTPException) as exc:
        await svc.update_job_agent_config(str(uuid.uuid4()), str(uuid.uuid4()), [])
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_job_agent_config_permission_denied():
    job_id = str(uuid.uuid4())
    owner_id = uuid.uuid4()
    other_id = str(uuid.uuid4())

    class FakeDB:
        async def get(self, model, uuid_val):
            return FakeJob(owner_id)

    svc = AgentConfigService(FakeDB())
    with pytest.raises(HTTPException) as exc:
        await svc.update_job_agent_config(job_id, other_id, [])
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_update_job_agent_config_invalid_round_list_id():
    job_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    class FakeDB:
        async def get(self, model, uuid_val):
            return FakeJob(uuid.UUID(user_id))
        async def execute(self, stmt):
            return FakeResultForExecute(scalars_list=[])

    svc = AgentConfigService(FakeDB())
    bad_round = AgentRoundConfigUpdate(jobId=job_id, roundListId='not-uuid', roundName='1', roundFocus='f', persona='alex')
    with pytest.raises(HTTPException) as exc:
        await svc.update_job_agent_config(job_id, user_id, [bad_round])
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_job_agent_config_round_jobid_mismatch():
    job_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    bad_round = AgentRoundConfigUpdate(jobId=str(uuid.uuid4()), roundListId=str(uuid.uuid4()), roundName='1', roundFocus='f', persona='alex')
    class FakeDB:
        async def get(self, model, uuid_val):
            return FakeJob(uuid.UUID(user_id))
        async def execute(self, stmt):
            return FakeResultForExecute(scalars_list=[])
        async def commit(self):
            return None

    svc = AgentConfigService(FakeDB())
    with pytest.raises(HTTPException) as exc:
        await svc.update_job_agent_config(job_id, user_id, [bad_round])
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_job_agent_config_updates_existing_config_and_legacy_scores():
    job_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    job_uuid = uuid.UUID(job_id)
    user_uuid = uuid.UUID(user_id)
    round_list_id = str(uuid.uuid4())

    # Create round_data with legacy fields and thresholds
    from types import SimpleNamespace
    round_data = SimpleNamespace(
        jobId=job_id,
        roundListId=round_list_id,
        roundName='Round 1',
        roundFocus='focus',
        persona='alex',
        keySkills=[],
        customQuestions=[],
        forbiddenTopics=[],
        roleFit=0.7,
        shortlistingThreshold=0.5,
        rejectingThreshold=0.1
    )

    existing_config_id = uuid.uuid4()
    existing_cfg = FakeConfig(id=existing_config_id, job_id=job_uuid, round_list_id=uuid.UUID(round_list_id), round_name='Round 1')
    existing_cfg.score_distribution = {'role_fit': 0.2}

    class FakeDB:
        def __init__(self):
            self.calls = 0
        async def get(self, model, uuid_val):
            return FakeJob(user_uuid)
        async def execute(self, stmt):
            # First execute: select existing configs
            if self.calls == 0:
                self.calls += 1
                return FakeResultForExecute(scalars_list=[existing_cfg])
            else:
                # Second execute is update; return updated config in scalar_one
                updated = FakeConfig(id=existing_config_id, job_id=job_uuid, round_list_id=uuid.UUID(round_list_id), round_name='Round 1')
                updated.score_distribution = {'role_fit': 0.7, 'shortlisting': 0.5, 'rejecting': 0.1}
                return FakeResultForExecute(scalar_one_obj=updated)
        async def commit(self):
            return None

    svc = AgentConfigService(FakeDB())
    res = await svc.update_job_agent_config(job_id, user_id, [round_data])
    assert isinstance(res, list)
    out = res[0]
    assert out['roundListId'] == round_list_id
    assert out['scoreDistribution']['role_fit'] == 0.7
    assert out['shortlistingThreshold'] == 0.5
    assert out['rejectingThreshold'] == 0.1
