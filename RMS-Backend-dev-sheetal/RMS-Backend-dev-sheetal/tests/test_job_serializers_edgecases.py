from types import SimpleNamespace
import datetime

from app.services.job_post.job_post_serializer import serialize_job_details


def make_job_with_simple_locations():
    # locations where job_location.location is a plain string (no nested model)
    jl = SimpleNamespace(location="Work from Home")
    job_loc = SimpleNamespace(location=jl)
    desc = SimpleNamespace(type_description=None, title=None, context=None, content=None)
    job_skill = SimpleNamespace(skill=None, weightage=None)
    job_skill.skill = None
    job_skill.skill_name = None
    job_skill.skill = "Python"

    round_item = SimpleNamespace(round_name=None, round_description=None, round_order=None, evaluation_criteria=None)

    return SimpleNamespace(
        id=None,
        job_title=None,
        descriptions=[desc],
        job_skills=[job_skill],
        rounds=[round_item],
        locations=[job_loc],
        work_mode="wfh",
        minimum_experience=None,
        maximum_experience=None,
        no_of_openings=None,
        rounds_count=None,
        is_active=False,
        active_till=None,
        posted_date=None,
        created_at=None,
        updated_at=None,
        interview_type=None,
        is_agent_interview=None,
        role_fit=None,
        potential_fit=None,
        location_fit=None,
        career_activation_mode=None,
        career_activation_days=None,
        career_shortlist_threshold=None,
        total_candidates=None,
        shortlisted_count=None,
        under_review_count=None,
        rejected_count=None,
        user_id=None,
    )


def test_serialize_locations_and_skills_and_rounds():
    job = make_job_with_simple_locations()
    details = serialize_job_details(job)

    # primary location should detect 'Work from Home' and set work_from_home True
    assert details["work_from_home"] is True
    # location names should include the string
    assert "Work from Home" in details["job_locations"]

    # skills required should include the fallback skill name
    assert any(s.get("skill") == "Python" for s in details["skills_required"])

    # interview_rounds should be a list (even if criteria missing)
    assert isinstance(details["interview_rounds"], list)
