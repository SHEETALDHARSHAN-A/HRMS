import pytest
from types import SimpleNamespace
from datetime import datetime
from app.services.job_post.job_post_serializer import (
    _to_iso,
    _collect_locations,
    _serialize_description_sections,
    _serialize_skills,
    _serialize_rounds,
    serialize_job_details,
    serialize_admin_job,
    serialize_public_job,
    JobPostSerializer,
)


def test_to_iso_none_and_datetime_and_string():
    assert _to_iso(None) is None
    dt = datetime(2020, 1, 1, 0, 0, 0)
    assert _to_iso(dt) == dt.isoformat()
    assert _to_iso(dt.isoformat()) == dt.isoformat()


def test_collect_locations_remote_and_work_mode():
    # location nested model
    loc_model = SimpleNamespace(location="Remote", state=None, country=None)
    loc_wrapper = SimpleNamespace(location=loc_model)
    job = SimpleNamespace(locations=[loc_wrapper], work_mode="wfh")
    info = _collect_locations(job)
    assert info["work_from_home"] is True
    assert info["primary_location"] == "Remote"


def test_serialize_description_sections_and_skills():
    desc = SimpleNamespace(title="Desc", content="Body")
    job_skill1 = SimpleNamespace(skill=SimpleNamespace(skill_name="Python"), weightage=10)
    job_skill2 = SimpleNamespace(skill="Linux", weightage=None)
    job = SimpleNamespace(descriptions=[desc], job_skills=[job_skill1, job_skill2])
    sections = _serialize_description_sections(job)
    skills = _serialize_skills(job)
    assert sections[0]["title"] == "Desc"
    assert any(s["skill"] == "Python" for s in skills)
    assert any(s["skill"] == "Linux" for s in skills)


def test_serialize_rounds_and_sorting():
    crit1 = SimpleNamespace(shortlisting_criteria=70, rejecting_criteria=50)
    round1 = SimpleNamespace(round_name="Level1", round_description=None, round_order=2, evaluation_criteria=[crit1])
    crit2 = SimpleNamespace(shortlisting_criteria=60, rejecting_criteria=40)
    round2 = SimpleNamespace(round_name="Level0", round_description="R2", round_order=1, evaluation_criteria=[crit2])
    job = SimpleNamespace(rounds=[round1, round2])
    rounds = _serialize_rounds(job)
    assert rounds[0]["round_order"] == 1
    assert rounds[1]["round_order"] == 2


def test_serialize_job_details_and_admin_public():
    # Build a detailed job with nested fields
    creator = SimpleNamespace(first_name="A", last_name="B", email="a@b.com")
    loc_model = SimpleNamespace(location="Bengaluru", state="KA", country="IN")
    loc_wrapper = SimpleNamespace(location=loc_model)
    job_skill = SimpleNamespace(skill=SimpleNamespace(skill_name="FastAPI"), weightage=5)
    round_item = SimpleNamespace(round_name="Screening", round_description="R1", round_order=1, evaluation_criteria=[SimpleNamespace(shortlisting_criteria=60, rejecting_criteria=40)])
    agent_config = SimpleNamespace(id=1, round_list_id="r1", round_name="R1", round_focus="focus", persona="persona", key_skills=[], custom_questions=[], forbidden_topics=[], interview_mode="agent", interview_time_min=10, interview_time_max=20, interviewer_id=None)
    job = SimpleNamespace(
        id="j1",
        job_title="Test Job",
        descriptions=[SimpleNamespace(title="Desc", content="Body")],
        job_skills=[job_skill],
        locations=[loc_wrapper],
        work_mode="office",
        minimum_experience=1,
        maximum_experience=3,
        no_of_openings=1,
        rounds_count=1,
        is_active=True,
        active_till=datetime(2025,1,1),
        posted_date=datetime(2025,1,1),
        created_at=datetime(2025,1,1),
        updated_at=datetime(2025,1,1),
        rounds=[round_item],
        agent_configs=[agent_config],
        total_candidates=10,
        shortlisted_count=2,
        under_review_count=1,
        rejected_count=7,
        user_id="u1",
        creator=creator
    )

    details = serialize_job_details(job)
    assert details["job_title"] == "Test Job"
    assert details["job_location"] == "Bengaluru"
    assert details["work_from_home"] is False
    assert details["shortlisted_count"] == 2

    admin = serialize_admin_job(job)
    assert admin["jobId"] == "j1"
    public = serialize_public_job(job)
    assert public["job_title"] == "Test Job"


def test_jobpost_serializer_class_methods():
    job = SimpleNamespace(id="x", job_title="T")
    assert JobPostSerializer.format_job_details_orm(job)["job_title"] == "T"
    assert JobPostSerializer.format_admin_job_orm(job)["jobId"] == "x"
    assert JobPostSerializer.format_full_job_orm(job)["job_id"] == "x"
import pytest
from types import SimpleNamespace
from app.services.job_post.job_post_serializer import (
    _to_iso,
    _collect_locations,
    _serialize_description_sections,
    _serialize_skills,
    _serialize_rounds,
    serialize_job_details,
    serialize_admin_job,
    serialize_public_job,
    JobPostSerializer,
)
from datetime import datetime


def test_to_iso_with_datetime():
    dt = datetime(2020, 1, 1, 12, 0, 0)
    assert _to_iso(dt) == dt.isoformat()


def test_collect_locations_remote_and_work_mode():
    # location with nested model
    loc_model = SimpleNamespace(location="Remote", state="KA", country="IN")
    job_loc = SimpleNamespace(location=loc_model)
    job = SimpleNamespace(locations=[job_loc], work_mode="remote")

    info = _collect_locations(job)
    assert info["primary_location"] == "Remote"
    assert info["work_from_home"] is True
    assert isinstance(info["locations_detail"], list)


def test_serialize_description_sections_and_skills_and_rounds():
    desc = SimpleNamespace(type_description=None, title="T", context="C", content=None)
    skill_model = SimpleNamespace(skill_name="Python")
    job_skill = SimpleNamespace(skill=skill_model, weightage=5)
    criteria = SimpleNamespace(shortlisting_criteria=60, rejecting_criteria=40)
    round_item = SimpleNamespace(round_name="Screen", round_description="desc", round_order=1, evaluation_criteria=[criteria])

    job = SimpleNamespace(descriptions=[desc], job_skills=[job_skill], rounds=[round_item])

    sections = _serialize_description_sections(job)
    skills = _serialize_skills(job)
    rounds = _serialize_rounds(job)

    assert sections[0]["title"] == "T"
    assert skills[0]["skill"] == "Python"
    assert rounds[0]["level_name"] == "Screen"


def test_serialize_job_details_and_variants():
    creator = SimpleNamespace(first_name="Alice", last_name="Smith", email="a@b.com")
    job = SimpleNamespace(
        id="jid",
        job_title="J",
        descriptions=[SimpleNamespace(title="T", content="C")],
        job_skills=[SimpleNamespace(skill="Py", weightage=10)],
        locations=[SimpleNamespace(location="Remote")],
        work_mode=None,
        minimum_experience=1,
        maximum_experience=3,
        no_of_openings=2,
        rounds_count=1,
        is_active=True,
        active_till=datetime(2025,1,1,0,0,0),
        posted_date=datetime(2025,1,1,0,0,0),
        created_at=None,
        updated_at=None,
        rounds=[],
        interview_type=None,
        is_agent_interview=False,
        role_fit=None,
        potential_fit=None,
        location_fit=None,
        career_activation_mode=None,
        career_activation_days=None,
        career_shortlist_threshold=None,
        total_candidates=0,
        shortlisted_count=0,
        under_review_count=0,
        rejected_count=0,
        user_id="u1",
        creator=creator,
    )

    details = serialize_job_details(job)
    assert details["job_title"] == "J"
    admin = serialize_admin_job(job)
    public = serialize_public_job(job)
    assert admin["job_id"] == public["job_id"]
    # test class wrapper
    assert JobPostSerializer.format_full_job_orm(job)["job_title"] == "J"