import json
import logging
import re

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.app_config import AppConfig
from app.db.models.agent_config_model import AgentRoundConfig
from app.db.models.coding_submission_model import CodingSubmission
from app.db.models.job_post_model import EvaluationCriteria, RoundList
from app.db.models.resume_model import InterviewRounds, Profile
from app.db.models.scheduling_model import Scheduling
from app.db.models.shortlist_model import Shortlist
from app.db.models.transcript_model import Transcript

try:
	from groq import AsyncGroq
except Exception:  # pragma: no cover - dependency may be absent in some test environments
	AsyncGroq = None


logger = logging.getLogger(__name__)
settings = AppConfig()


class InterviewCompletionService:
	"""Finalize interview session, evaluate candidate, and progress next round."""

	def __init__(self, db: AsyncSession):
		self.db = db

	async def complete_and_evaluate(
		self,
		token: str,
		email: str,
		session_id: Optional[str] = None,
		final_notes: Optional[str] = None,
	) -> Dict[str, Any]:
		try:
			schedule = await self._resolve_candidate_schedule(token=token, email=email)
			interview_round, current_round = await self._resolve_current_round(schedule)

			if current_round is None:
				raise HTTPException(
					status_code=status.HTTP_404_NOT_FOUND,
					detail="Unable to resolve current interview round for this schedule",
				)

			transcript = await self._fetch_latest_transcript(
				token=token,
				profile_id=schedule.profile_id,
				session_id=session_id,
			)

			coding_submission = await self._fetch_latest_coding_submission(
				profile_id=schedule.profile_id,
				token=token,
				round_list_id=current_round.id,
			)

			evaluation = await self._evaluate_candidate(
				transcript=transcript,
				coding_submission=coding_submission,
			)

			thresholds = await self._get_round_thresholds(
				job_id=schedule.job_id,
				round_list_id=current_round.id,
			)

			decision = self._decide_result(
				score=evaluation["overall_score"],
				shortlisting_threshold=thresholds["shortlisting_threshold"],
				rejecting_threshold=thresholds["rejecting_threshold"],
			)
			round_status = self._map_result_to_round_status(decision)

			await self._mark_current_round_status(
				schedule=schedule,
				interview_round=interview_round,
				current_round=current_round,
				round_status=round_status,
			)

			await self._update_shortlist_record(
				job_id=schedule.job_id,
				profile_id=schedule.profile_id,
				evaluation=evaluation,
				decision=decision,
			)

			next_round = await self._progress_to_next_round(
				schedule=schedule,
				current_round=current_round,
				decision=decision,
			)

			auto_schedule = {
				"triggered": False,
				"reason": "not_shortlisted",
			}
			if decision == "shortlist" and bool(next_round.get("triggered")):
				try:
					from app.services.scheduling_service.next_round_auto_scheduler import NextRoundAutoScheduler

					auto_schedule = await NextRoundAutoScheduler(self.db).auto_schedule_next_round(
						profile_id=schedule.profile_id,
						current_round_id=current_round.id,
						source="interview_completion",
					)
				except Exception as auto_exc:
					logger.warning("Auto scheduling failed during interview completion: %s", auto_exc, exc_info=True)
					auto_schedule = {
						"triggered": False,
						"reason": "auto_schedule_failed",
						"error": str(auto_exc),
					}

			await self._mark_schedule_completed(schedule)

			await self._attach_evaluation_to_transcript(
				transcript=transcript,
				evaluation=evaluation,
				decision=decision,
				thresholds=thresholds,
				next_round=next_round,
				final_notes=final_notes,
			)

			await self.db.commit()

			return {
				"token": str(token),
				"email": email,
				"decision": decision,
				"roundStatus": round_status,
				"evaluation": evaluation,
				"thresholds": thresholds,
				"currentRound": {
					"id": str(current_round.id),
					"name": current_round.round_name,
					"order": current_round.round_order,
				},
				"nextRound": next_round,
				"autoSchedule": auto_schedule,
				"transcriptId": str(transcript.id) if transcript else None,
				"codingSubmissionId": str(coding_submission.id) if coding_submission else None,
			}

		except HTTPException:
			await self.db.rollback()
			raise
		except Exception as exc:
			await self.db.rollback()
			logger.error("Failed to complete interview lifecycle: %s", exc, exc_info=True)
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail="Failed to complete interview lifecycle",
			)

	async def _resolve_candidate_schedule(self, token: str, email: str) -> Scheduling:
		stmt = (
			select(Scheduling)
			.join(Profile, Scheduling.profile_id == Profile.id)
			.where(cast(Scheduling.interview_token, String) == str(token))
			.where(func.lower(Profile.email) == email.lower())
		)
		result = await self.db.execute(stmt)
		schedule = result.scalar_one_or_none()

		if schedule is None:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="Interview schedule not found for provided token/email",
			)

		return schedule

	async def _resolve_current_round(
		self,
		schedule: Scheduling,
	) -> Tuple[Optional[InterviewRounds], Optional[RoundList]]:
		schedule_round_uuid = self._to_uuid(getattr(schedule, "round_id", None))

		if schedule_round_uuid is None:
			return None, None

		interview_round: Optional[InterviewRounds] = await self._get_interview_round_by_id(schedule_round_uuid)

		current_round: Optional[RoundList] = None
		if interview_round is not None:
			current_round = await self._get_round_list_by_id(interview_round.round_id)

		# Some deployments store round_list.id in scheduling.round_id instead of interview_rounds.id.
		if current_round is None:
			current_round = await self._get_round_list_by_id(schedule_round_uuid)

		if interview_round is None and current_round is not None:
			interview_round = await self._get_interview_round_by_profile_round(
				job_id=schedule.job_id,
				profile_id=schedule.profile_id,
				round_list_id=current_round.id,
			)

		return interview_round, current_round

	async def _get_interview_round_by_id(self, interview_round_id: UUID) -> Optional[InterviewRounds]:
		stmt = select(InterviewRounds).where(InterviewRounds.id == interview_round_id)
		result = await self.db.execute(stmt)
		return result.scalar_one_or_none()

	async def _get_round_list_by_id(self, round_list_id: UUID) -> Optional[RoundList]:
		stmt = select(RoundList).where(RoundList.id == round_list_id)
		result = await self.db.execute(stmt)
		return result.scalar_one_or_none()

	async def _get_interview_round_by_profile_round(
		self,
		job_id: Any,
		profile_id: Any,
		round_list_id: UUID,
	) -> Optional[InterviewRounds]:
		stmt = (
			select(InterviewRounds)
			.where(InterviewRounds.job_id == job_id)
			.where(InterviewRounds.profile_id == profile_id)
			.where(InterviewRounds.round_id == round_list_id)
			.order_by(InterviewRounds.id.desc())
		)
		result = await self.db.execute(stmt)
		return result.scalars().first()

	async def _fetch_latest_transcript(
		self,
		token: str,
		profile_id: Any,
		session_id: Optional[str],
	) -> Optional[Transcript]:
		stmt = (
			select(Transcript)
			.where(Transcript.room_id == str(token))
			.where(Transcript.profile_id == profile_id)
		)

		session_uuid = self._to_uuid(session_id)
		if session_id and session_uuid is None:
			logger.warning("Invalid session_id received for completion: %s", session_id)

		if session_uuid is not None:
			stmt = stmt.where(Transcript.id == session_uuid)

		stmt = stmt.order_by(Transcript.start_time.desc())
		result = await self.db.execute(stmt)
		return result.scalars().first()

	async def _fetch_latest_coding_submission(
		self,
		profile_id: Any,
		token: str,
		round_list_id: UUID,
	) -> Optional[CodingSubmission]:
		stmt = (
			select(CodingSubmission)
			.where(CodingSubmission.profile_id == profile_id)
			.where(CodingSubmission.interview_token == str(token))
			.where(CodingSubmission.round_list_id == round_list_id)
			.order_by(CodingSubmission.created_at.desc())
		)
		result = await self.db.execute(stmt)
		submission = result.scalars().first()
		if submission is not None:
			return submission

		# Fallback without round filter for deployments where round mapping differs.
		fallback_stmt = (
			select(CodingSubmission)
			.where(CodingSubmission.profile_id == profile_id)
			.where(CodingSubmission.interview_token == str(token))
			.order_by(CodingSubmission.created_at.desc())
		)
		fallback_res = await self.db.execute(fallback_stmt)
		return fallback_res.scalars().first()

	async def _evaluate_candidate(
		self,
		transcript: Optional[Transcript],
		coding_submission: Optional[CodingSubmission],
	) -> Dict[str, Any]:
		conversation_text = self._flatten_transcript(transcript)
		fallback = self._heuristic_evaluation(
			conversation_text=conversation_text,
			coding_submission=coding_submission,
		)

		if not self._can_call_groq():
			return fallback

		client = AsyncGroq(api_key=settings.effective_groq_api_key)
		transcript_excerpt = conversation_text[-14000:] if conversation_text else "No transcript captured."

		if coding_submission is not None:
			coding_context = {
				"score": coding_submission.ai_score,
				"feedback": coding_submission.ai_feedback,
				"language": coding_submission.language,
			}
			coding_text = json.dumps(coding_context, ensure_ascii=True)
		else:
			coding_text = "No coding submission available."

		prompt = f"""
You are evaluating an interview outcome for hiring progression.
Return strict JSON with keys:
- overall_score (integer 0-100)
- communication_score (integer 0-100)
- technical_score (integer 0-100)
- coding_score (integer 0-100 or null)
- summary (string, max 300 chars)
- strengths (array of short strings)
- concerns (array of short strings)
- recommendation (one of: shortlist, under_review, reject)

Transcript:
{transcript_excerpt}

Coding Evaluation:
{coding_text}

Return only valid JSON.
"""

		try:
			completion = await client.chat.completions.create(
				model=settings.effective_groq_model,
				temperature=0.1,
				response_format={"type": "json_object"},
				messages=[
					{"role": "system", "content": "You are a strict and fair technical interviewer."},
					{"role": "user", "content": prompt},
				],
			)
			content = completion.choices[0].message.content or ""
			parsed = self._extract_json(content)
			if not parsed:
				return fallback

			overall_score = self._coerce_score(parsed.get("overall_score"), default=fallback["overall_score"])
			communication_score = self._coerce_score(
				parsed.get("communication_score"),
				default=fallback["communication_score"],
			)
			technical_score = self._coerce_score(
				parsed.get("technical_score"),
				default=fallback["technical_score"],
			)

			raw_coding_score = parsed.get("coding_score")
			coding_score: Optional[int]
			if raw_coding_score is None:
				coding_score = fallback.get("coding_score")
			else:
				coding_score = self._coerce_score(raw_coding_score, default=fallback.get("coding_score") or 0)

			summary = parsed.get("summary") if isinstance(parsed.get("summary"), str) else fallback["summary"]
			strengths = parsed.get("strengths") if isinstance(parsed.get("strengths"), list) else fallback["strengths"]
			concerns = parsed.get("concerns") if isinstance(parsed.get("concerns"), list) else fallback["concerns"]
			recommendation = (
				parsed.get("recommendation")
				if parsed.get("recommendation") in {"shortlist", "under_review", "reject"}
				else fallback["recommendation"]
			)

			return {
				"overall_score": overall_score,
				"communication_score": communication_score,
				"technical_score": technical_score,
				"coding_score": coding_score,
				"summary": summary,
				"strengths": strengths,
				"concerns": concerns,
				"recommendation": recommendation,
			}
		except Exception as exc:
			logger.warning("Groq interview evaluation failed, using fallback: %s", exc)
			return fallback

	def _heuristic_evaluation(
		self,
		conversation_text: str,
		coding_submission: Optional[CodingSubmission],
	) -> Dict[str, Any]:
		words = re.findall(r"\w+", conversation_text or "")
		word_count = len(words)

		communication_score = max(25, min(92, int(32 + (word_count * 0.15))))

		lower_text = (conversation_text or "").lower()
		technical_keywords = [
			"algorithm",
			"complexity",
			"database",
			"scalable",
			"api",
			"debug",
			"optimization",
			"architecture",
			"testing",
			"security",
		]
		keyword_hits = sum(1 for kw in technical_keywords if kw in lower_text)
		technical_score = max(28, min(95, 35 + (keyword_hits * 6) + (8 if word_count >= 120 else 0)))

		coding_score: Optional[int] = None
		if coding_submission is not None and coding_submission.ai_score is not None:
			coding_score = self._coerce_score(coding_submission.ai_score, default=55)

		if coding_score is not None:
			overall_score = round((technical_score * 0.45) + (communication_score * 0.25) + (coding_score * 0.30))
		else:
			overall_score = round((technical_score * 0.60) + (communication_score * 0.40))

		if overall_score >= 70:
			recommendation = "shortlist"
		elif overall_score <= 40:
			recommendation = "reject"
		else:
			recommendation = "under_review"

		strengths = []
		concerns = []

		if communication_score >= 65:
			strengths.append("Communicated responses clearly during the interview.")
		else:
			concerns.append("Communication was limited; responses need more clarity.")

		if technical_score >= 65:
			strengths.append("Demonstrated acceptable technical depth for this round.")
		else:
			concerns.append("Technical depth appeared below threshold for this round.")

		if coding_score is not None:
			if coding_score >= 65:
				strengths.append("Coding submission quality was solid.")
			else:
				concerns.append("Coding submission quality needs improvement.")
		else:
			concerns.append("No coding submission was available for this evaluation.")

		summary = (
			f"Automated interview evaluation produced {overall_score}/100 "
			f"(communication {communication_score}, technical {technical_score}"
			+ (f", coding {coding_score}" if coding_score is not None else "")
			+ ")."
		)

		return {
			"overall_score": overall_score,
			"communication_score": communication_score,
			"technical_score": technical_score,
			"coding_score": coding_score,
			"summary": summary,
			"strengths": strengths,
			"concerns": concerns,
			"recommendation": recommendation,
		}

	async def _get_round_thresholds(self, job_id: Any, round_list_id: UUID) -> Dict[str, int]:
		shortlisting_threshold = None
		rejecting_threshold = None

		stmt = (
			select(EvaluationCriteria)
			.where(EvaluationCriteria.job_id == job_id)
			.where(EvaluationCriteria.round_id == round_list_id)
		)
		result = await self.db.execute(stmt)
		criteria = result.scalar_one_or_none()

		if criteria is not None:
			shortlisting_threshold = criteria.shortlisting_criteria
			rejecting_threshold = criteria.rejecting_criteria

		if shortlisting_threshold is None or rejecting_threshold is None:
			cfg_stmt = (
				select(AgentRoundConfig)
				.where(AgentRoundConfig.job_id == job_id)
				.where(AgentRoundConfig.round_list_id == round_list_id)
			)
			cfg_res = await self.db.execute(cfg_stmt)
			config = cfg_res.scalar_one_or_none()
			if config is not None:
				score_distribution = getattr(config, "score_distribution", None) or {}
				if shortlisting_threshold is None:
					shortlisting_threshold = score_distribution.get("shortlisting")
				if rejecting_threshold is None:
					rejecting_threshold = score_distribution.get("rejecting")

		shortlisting_threshold = self._coerce_score(shortlisting_threshold, default=70)
		rejecting_threshold = self._coerce_score(rejecting_threshold, default=40)

		if rejecting_threshold >= shortlisting_threshold:
			rejecting_threshold = max(0, shortlisting_threshold - 10)

		return {
			"shortlisting_threshold": shortlisting_threshold,
			"rejecting_threshold": rejecting_threshold,
		}

	async def _mark_current_round_status(
		self,
		schedule: Scheduling,
		interview_round: Optional[InterviewRounds],
		current_round: RoundList,
		round_status: str,
	) -> None:
		if interview_round is None:
			interview_round = await self._get_interview_round_by_profile_round(
				job_id=schedule.job_id,
				profile_id=schedule.profile_id,
				round_list_id=current_round.id,
			)

		if interview_round is None:
			interview_round = InterviewRounds(
				job_id=schedule.job_id,
				profile_id=schedule.profile_id,
				round_id=current_round.id,
				status=round_status,
			)
			self.db.add(interview_round)
			return

		interview_round.status = round_status

	async def _update_shortlist_record(
		self,
		job_id: Any,
		profile_id: Any,
		evaluation: Dict[str, Any],
		decision: str,
	) -> None:
		stmt = (
			select(Shortlist)
			.where(Shortlist.job_id == job_id)
			.where(Shortlist.profile_id == profile_id)
		)
		result = await self.db.execute(stmt)
		shortlist = result.scalar_one_or_none()
		if shortlist is None:
			logger.info("No shortlist row found for profile %s and job %s", profile_id, job_id)
			return

		shortlist.result = decision
		shortlist.reason = evaluation.get("summary")
		shortlist.overall_score = evaluation.get("overall_score")
		shortlist.score_explanation = json.dumps(
			{
				"communication_score": evaluation.get("communication_score"),
				"technical_score": evaluation.get("technical_score"),
				"coding_score": evaluation.get("coding_score"),
				"strengths": evaluation.get("strengths") or [],
				"concerns": evaluation.get("concerns") or [],
			},
			ensure_ascii=True,
		)
		shortlist.updated_at = datetime.utcnow()

	async def _progress_to_next_round(
		self,
		schedule: Scheduling,
		current_round: RoundList,
		decision: str,
	) -> Dict[str, Any]:
		if decision != "shortlist":
			return {
				"triggered": False,
				"is_final_round": False,
				"reason": "candidate_not_shortlisted",
			}

		if current_round.round_order is None:
			return {
				"triggered": False,
				"is_final_round": False,
				"reason": "missing_round_order",
			}

		next_round_order = int(current_round.round_order) + 1
		stmt = (
			select(RoundList)
			.where(RoundList.job_id == schedule.job_id)
			.where(RoundList.round_order == next_round_order)
		)
		result = await self.db.execute(stmt)
		next_round = result.scalar_one_or_none()

		if next_round is None:
			return {
				"triggered": False,
				"is_final_round": True,
				"reason": "no_next_round",
			}

		next_interview_round = await self._get_interview_round_by_profile_round(
			job_id=schedule.job_id,
			profile_id=schedule.profile_id,
			round_list_id=next_round.id,
		)

		if next_interview_round is None:
			next_interview_round = InterviewRounds(
				job_id=schedule.job_id,
				profile_id=schedule.profile_id,
				round_id=next_round.id,
				status="under_review",
			)
			self.db.add(next_interview_round)
		elif not next_interview_round.status or str(next_interview_round.status).lower() in {"pending", "scheduled"}:
			next_interview_round.status = "under_review"

		return {
			"triggered": True,
			"is_final_round": False,
			"next_round_id": str(next_round.id),
			"next_round_name": next_round.round_name,
			"next_round_order": next_round.round_order,
			"next_interview_round_id": str(next_interview_round.id) if getattr(next_interview_round, "id", None) else None,
		}

	async def _mark_schedule_completed(self, schedule: Scheduling) -> None:
		schedule.status = "completed"

	async def _attach_evaluation_to_transcript(
		self,
		transcript: Optional[Transcript],
		evaluation: Dict[str, Any],
		decision: str,
		thresholds: Dict[str, int],
		next_round: Dict[str, Any],
		final_notes: Optional[str],
	) -> None:
		if transcript is None:
			return

		existing_meta = transcript.round_meta if isinstance(transcript.round_meta, dict) else {}
		existing_meta["evaluation"] = {
			"decision": decision,
			"overall_score": evaluation.get("overall_score"),
			"communication_score": evaluation.get("communication_score"),
			"technical_score": evaluation.get("technical_score"),
			"coding_score": evaluation.get("coding_score"),
			"summary": evaluation.get("summary"),
			"strengths": evaluation.get("strengths") or [],
			"concerns": evaluation.get("concerns") or [],
			"thresholds": thresholds,
			"next_round": next_round,
			"final_notes": final_notes,
			"evaluated_at": datetime.now(timezone.utc).isoformat(),
		}

		transcript.round_meta = existing_meta
		if not transcript.end_time:
			transcript.end_time = datetime.now(timezone.utc)

	@staticmethod
	def _flatten_transcript(transcript: Optional[Transcript]) -> str:
		if transcript is None or not isinstance(transcript.conversation, list):
			return ""

		lines = []
		for item in transcript.conversation:
			if not isinstance(item, dict):
				continue
			speaker = str(item.get("speaker") or "participant").strip()
			content = str(item.get("content") or item.get("speech") or "").strip()
			if content:
				lines.append(f"{speaker}: {content}")
		return "\n".join(lines)

	@staticmethod
	def _decide_result(score: int, shortlisting_threshold: int, rejecting_threshold: int) -> str:
		if score >= shortlisting_threshold:
			return "shortlist"
		if score <= rejecting_threshold:
			return "reject"
		return "under_review"

	@staticmethod
	def _map_result_to_round_status(result: str) -> str:
		mapping = {
			"shortlist": "shortlisted",
			"under_review": "under_review",
			"reject": "rejected",
		}
		return mapping.get(result, "under_review")

	@staticmethod
	def _extract_json(text: str) -> Optional[Dict[str, Any]]:
		if not text:
			return None

		try:
			parsed = json.loads(text)
			return parsed if isinstance(parsed, dict) else None
		except Exception:
			pass

		match = re.search(r"\{.*\}", text, re.DOTALL)
		if not match:
			return None

		try:
			parsed = json.loads(match.group(0))
			return parsed if isinstance(parsed, dict) else None
		except Exception:
			return None

	@staticmethod
	def _coerce_score(raw_score: Any, default: int) -> int:
		try:
			value = int(raw_score)
		except Exception:
			value = default
		return max(0, min(100, value))

	@staticmethod
	def _to_uuid(value: Any) -> Optional[UUID]:
		if value is None:
			return None
		if isinstance(value, UUID):
			return value
		try:
			return UUID(str(value))
		except Exception:
			return None

	@staticmethod
	def _can_call_groq() -> bool:
		if AsyncGroq is None:
			return False
		api_key = (getattr(settings, "effective_groq_api_key", "") or "").strip()
		return api_key.startswith("gsk_")
