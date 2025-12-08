from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification_model import Notification
from app.db.models.user_model import User


async def fetch_notifications(db: AsyncSession, user_id: str, unread_only: bool = False, limit: int = 50) -> List[Notification]:
    query = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        query = query.where(Notification.is_read == False)
    query = query.order_by(Notification.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def fetch_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    query = select(User).where(User.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def mark_notification_read_db(db: AsyncSession, notification_id: str, user_id: str) -> bool:
    query = select(Notification).where(
        Notification.notification_id == notification_id,
        Notification.user_id == user_id
    )
    result = await db.execute(query)
    notification = result.scalar_one_or_none()
    if not notification:
        return False
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    await db.commit()
    return True


async def mark_all_notifications_read_db(db: AsyncSession, user_id: str) -> int:
    update_query = (
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)
        .values(is_read=True, read_at=datetime.utcnow())
    )
    result = await db.execute(update_query)
    await db.commit()
    try:
        return int(result.rowcount)
    except Exception:
        return 0


async def get_unread_count_db(db: AsyncSession, user_id: str) -> int:
    query = select(Notification).where(Notification.user_id == user_id, Notification.is_read == False)
    result = await db.execute(query)
    return len(result.scalars().all())


async def delete_notification_db(db: AsyncSession, notification_id: str, user_id: str) -> bool:
    query = select(Notification).where(
        Notification.notification_id == notification_id,
        Notification.user_id == user_id
    )
    result = await db.execute(query)
    notification = result.scalar_one_or_none()
    if not notification:
        return False
    await db.delete(notification)
    await db.commit()
    return True


# Invitation-related repository helpers (shared with notification services)
from app.db.models.invitation_model import Invitation, InvitationStatus
from sqlalchemy import and_, or_


async def fetch_invitations_by_inviter(db: AsyncSession, inviter_id: str, status_filter: Optional[str] = None) -> List[Invitation]:
    query = select(Invitation).where(Invitation.invited_by == inviter_id)
    if status_filter:
        query = query.where(Invitation.status == status_filter)
    query = query.order_by(Invitation.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def get_invitation_stats_db(db: AsyncSession, inviter_id: str) -> dict:
    # pending: PENDING and not expired
    pending_q = select(Invitation).where(
        and_(
            Invitation.invited_by == inviter_id,
            Invitation.status == InvitationStatus.PENDING.value,
            Invitation.expires_at > datetime.utcnow()
        )
    )
    accepted_q = select(Invitation).where(
        and_(
            Invitation.invited_by == inviter_id,
            Invitation.status == InvitationStatus.ACCEPTED.value
        )
    )
    expired_q = select(Invitation).where(
        and_(
            Invitation.invited_by == inviter_id,
            or_(
                Invitation.status == InvitationStatus.EXPIRED.value,
                and_(
                    Invitation.status == InvitationStatus.PENDING.value,
                    Invitation.expires_at <= datetime.utcnow()
                )
            )
        )
    )

    pending_res = await db.execute(pending_q)
    accepted_res = await db.execute(accepted_q)
    expired_res = await db.execute(expired_q)

    return {
        "pending": len(pending_res.scalars().all()),
        "accepted": len(accepted_res.scalars().all()),
        "expired": len(expired_res.scalars().all()),
    }
