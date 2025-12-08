from datetime import datetime, timezone, time
import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from unittest.mock import AsyncMock
import asyncio
from app.services.scheduling_service.scheduling_service import Scheduling
from app.schemas.scheduling_interview_request import SchedulingInterviewRequest

class FakeDB:
    pass

async def run():
    svc = Scheduling(FakeDB())
    today = datetime.now(timezone.utc)
    req = SchedulingInterviewRequest(job_id='j1', profile_id=['p1'], round_id='r1', interview_date=today.date(), interview_time=time(14,0))
    # patch repo functions used in schedule
    from app.services.scheduling_service import scheduling_service as sched_mod
    sched_mod.check_existing_schedules = AsyncMock(return_value=[])
    sched_mod.get_candidate_details_for_scheduling = AsyncMock(return_value=[{"user_id":"p1","email":"a@b.com"}])
    sched_mod.get_job_title_by_id = AsyncMock(return_value='Job')
    sched_mod.send_interview_invite_email_async = AsyncMock(return_value=False)
    try:
        r = await svc.schedule_candidate(req)
        print('Returned:', r)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(run())
