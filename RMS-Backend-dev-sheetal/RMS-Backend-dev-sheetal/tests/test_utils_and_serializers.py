import datetime
from types import SimpleNamespace

from app.utils.standard_response_utils import ResponseBuilder
from app.services.job_post.job_post_permissions import JobPostPermissions
from app.services.job_post.job_post_serializer import (
    serialize_job_details,
    serialize_admin_job,
    serialize_public_job,
    JobPostSerializer,
)


def make_mock_job():
    # Create a lightweight object that mimics the ORM JobDetails used by serializers
    loc = SimpleNamespace(location="Remote Office", state="KA", country="IN")
    job_loc = SimpleNamespace(location=loc)

    desc = SimpleNamespace(type_description=None, title="Desc", context="Full description text.")

    skill_model = SimpleNamespace(skill_name="Python")
    job_skill1 = SimpleNamespace(skill=skill_model, weightage=8)
    job_skill2 = SimpleNamespace(skill=None, skill_name=None, weightage=None, skill_name_alt=None)
    job_skill2.skill = None
    job_skill2.skill = None
    job_skill2 = SimpleNamespace(skill=None, weightage=0, skill_name=None)

    criteria = SimpleNamespace(shortlisting_criteria=60, rejecting_criteria=40)
    round_item = SimpleNamespace(round_name="Screening", round_description=None, round_order=1, evaluation_criteria=[criteria])

    return SimpleNamespace(
        id="job-123",
        job_title="Senior Dev",
        descriptions=[desc],
        job_skills=[job_skill1, job_skill2],
        rounds=[round_item],
        locations=[job_loc],
        work_mode="remote",
        minimum_experience=2,
        maximum_experience=5,
        no_of_openings=3,
        rounds_count=1,
        is_active=True,
        active_till=datetime.datetime(2026, 1, 1),
        posted_date=datetime.datetime(2025, 11, 6),
        created_at=None,
        updated_at=None,
        interview_type="onsite",
        is_agent_interview=False,
        role_fit=30,
        potential_fit=60,
        location_fit=10,
        career_activation_mode="manual",
        career_activation_days=30,
        career_shortlist_threshold=5,
        total_candidates=12,
        shortlisted_count=3,
        under_review_count=1,
        rejected_count=0,
        user_id="user-xyz",
    )


def test_response_builder_variants():
    s = ResponseBuilder.success("ok", data={"a": 1}, status_code=200)
    assert s["success"] is True
    assert s["message"] == "ok"

    c = ResponseBuilder.created("created", data=None)
    assert c["status_code"] == 201

    e = ResponseBuilder.error("bad", errors=["err1"], status_code=400)
    assert e["success"] is False
    assert e["errors"] == ["err1"]

    nf = ResponseBuilder.not_found()
    assert nf["status_code"] == 404

    cf = ResponseBuilder.conflict()
    assert cf["status_code"] == 409

    se = ResponseBuilder.server_error()
    assert se["status_code"] == 500


def test_job_post_permissions_and_filtering():
    job = SimpleNamespace(user_id="user-xyz")
    # No user -> cannot edit
    assert JobPostPermissions.can_edit_job(job, None) is False

    # Same user -> can edit
    current_user = {"user_id": "user-xyz", "role": "USER"}
    assert JobPostPermissions.can_edit_job(job, current_user) is True

    # Super admin -> can edit
    current_user_sa = {"user_id": "other", "role": "SUPER_ADMIN"}
    assert JobPostPermissions.can_edit_job(job, current_user_sa) is True

    # filter_jobs_by_ownership
    jobs = [
        {"user_id": "user-xyz", "job_id": "a"},
        {"user_id": "other", "job_id": "b"},
    ]
    filtered = JobPostPermissions.filter_jobs_by_ownership(jobs.copy(), current_user)
    assert any(j.get("is_own_job") for j in filtered)

    # show_own_only should filter others out
    filtered2 = JobPostPermissions.filter_jobs_by_ownership(jobs.copy(), current_user, show_own_only=True)
    assert len(filtered2) == 1


def test_job_serializers_basic():
    job = make_mock_job()
    details = serialize_job_details(job)
    assert details["job_id"] == "job-123"
    assert isinstance(details["skills_required"], list)
    assert isinstance(details["description_sections"], list)

    admin = serialize_admin_job(job)
    assert admin["job_id"] == "job-123"

    public = serialize_public_job(job)
    assert public["job_id"] == "job-123"

    # Test class wrapper
    assert JobPostSerializer.format_full_job_orm(job)["job_id"] == "job-123"
