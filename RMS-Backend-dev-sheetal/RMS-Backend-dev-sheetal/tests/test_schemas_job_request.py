import uuid
import pytest
from pydantic import ValidationError

from app.schemas.job_request import BatchDeleteJobsRequest


def test_batch_delete_jobs_request_valid_uuid_list():
    ids = [str(uuid.uuid4()), uuid.uuid4()]
    req = BatchDeleteJobsRequest(job_ids=ids)
    assert len(req.job_ids) == 2
    # all elements should be UUID instances
    assert all(isinstance(i, uuid.UUID) for i in req.job_ids)


def test_batch_delete_jobs_request_empty_list_raises():
    with pytest.raises(ValidationError):
        BatchDeleteJobsRequest(job_ids=[])
