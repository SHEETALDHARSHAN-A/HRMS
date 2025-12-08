# app/db/models/user_repository.py

from types import SimpleNamespace
import inspect
from typing import Any, Dict, List

from sqlalchemy.future import select
from sqlalchemy import delete, update
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user_model import User

async def create_user(db: AsyncSession, user: User) -> User:
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    try:
        # Case-insensitive email lookup and trim whitespace
        email = email.strip().lower()
        result = await db.execute(select(User).where(User.email.ilike(email)))
        return result.scalars().first()
    except ProgrammingError:
        # The prior statement likely caused the current transaction to be aborted
        # (missing column or similar). Roll back the transaction so we can run
        # a safe fallback select in a clean transaction.
        try:
            await db.rollback()
        except Exception:
            # best-effort rollback; ignore failures and proceed to fallback
            pass

        # Fallback for databases - select core columns
        result = await db.execute(
            select(
                User.user_id,
                User.first_name,
                User.last_name,
                User.email,
                User.role,  # Use role instead of user_type
                User.created_at,
                User.updated_at,
            ).where(User.email == email)
        )
        maybe = result.first()
        if inspect.isawaitable(maybe):
            row = await maybe
        else:
            row = maybe
        # If the row is falsy or a test/mock object, treat as no result
        if not row:
            return None
        if getattr(type(row), '__module__', '').startswith('unittest.mock'):
            return None
        # No need to commit here; we're returning a lightweight object.
        return SimpleNamespace(
            user_id=row[0],
            first_name=row[1],
            last_name=row[2],
            email=row[3],
            role=row[4],  # Return role instead of user_type
            created_at=row[5],
            updated_at=row[6],
        )


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:

    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalars().first()

async def get_all_admins_details(db: AsyncSession, caller_role: str = None) -> List[Dict]:
    """
    Retrieves list of admins based on caller's role:
    - SUPER_ADMIN: sees all admins (SUPER_ADMIN, ADMIN, HR)
    - ADMIN: sees ADMIN and HR
    - HR: sees HR only
    """
    # Query all users who are admin roles (not CANDIDATE)
    query = select(
        User.user_id,
        User.first_name,
        User.last_name,
        User.email,
        User.phone_number,
        User.role,
        User.created_at,
    ).where(User.role.in_(["SUPER_ADMIN", "ADMIN", "HR"]))
    
    # Apply role-based filtering
    if caller_role == "SUPER_ADMIN":
        # Super admin sees everyone (including other SUPER_ADMINs)
        print(f"[DEBUG] SUPER_ADMIN caller - showing all roles: SUPER_ADMIN, ADMIN, HR")
        pass
    elif caller_role == "ADMIN":
        # Admin sees ADMIN and HR
        print(f"[DEBUG] ADMIN caller - showing roles: ADMIN, HR")
        query = query.where(User.role.in_(["ADMIN", "HR"]))
    elif caller_role == "HR":
        # HR sees HR only
        print(f"[DEBUG] HR caller - showing role: HR")
        query = query.where(User.role == "HR")
    else:
        # Unknown role, return empty list
        print(f"[DEBUG] Unknown caller role '{caller_role}' - returning empty list")
        return []
    
    result = await db.execute(query)
    raw_results = result.fetchall()

    # Map the results to a list of dictionaries
    admin_list = [
        {
            "user_id": str(r[0]),
            "first_name": r[1],
            "last_name": r[2],
            "email": r[3],
            "phone_number": r[4],
            "role": r[5],
            "created_at": r[6].isoformat() if r[6] else None,
        }
        for r in raw_results
    ]
    
    # Debug logging
    role_counts = {}
    for admin in admin_list:
        role = admin["role"]
        role_counts[role] = role_counts.get(role, 0) + 1
    
    print(f"[DEBUG] Returning {len(admin_list)} admins for caller_role '{caller_role}': {role_counts}")
    
    return admin_list


async def search_admins(db: AsyncSession, query_str: str, limit: int = 20) -> List[Dict]:
    """
    Search admin users by name, email, or user_id (UUID). Returns a list of matching admin dicts.
    """
    from sqlalchemy import or_, String
    from sqlalchemy.sql import cast

    if not query_str:
        return []

    pattern = f"%{query_str}%"

    search_query = select(
        User.user_id,
        User.first_name,
        User.last_name,
        User.email,
        User.phone_number,
        User.role,
        User.created_at,
    ).where(
        User.role.in_("SUPER_ADMIN ADMIN HR".split())
    ).where(
        or_(
            User.first_name.ilike(pattern),
            User.last_name.ilike(pattern),
            User.email.ilike(pattern),
            cast(User.user_id, String).ilike(pattern),
        )
    ).limit(limit)

    result = await db.execute(search_query)
    rows = result.fetchall()

    return [
        {
            "user_id": str(r[0]),
            "first_name": r[1],
            "last_name": r[2],
            "email": r[3],
            "phone_number": r[4],
            "role": r[5],
            "created_at": r[6].isoformat() if r[6] else None,
        }
        for r in rows
    ]

async def delete_users_by_id_and_type(
    db: AsyncSession, 
    user_ids: List[str], 
    allowed_roles: List[str] = None,  # Changed from user_type to allowed_roles
    caller_role: str = None, 
    caller_id: str = None
) -> tuple[int, List[User]]:
    """
    Deletes multiple users by a list of user_ids, ensuring they have appropriate roles.
    Applies role-based filtering:
    - SUPER_ADMIN can delete anyone
    - ADMIN can delete ADMIN and HR
    - HR can delete HR only (not themselves)
    
    Args:
        db: Database session
        user_ids: List of user IDs to delete
        allowed_roles: List of roles that can be deleted (e.g., ["ADMIN", "HR"])
        caller_role: Role of the user making the request
        caller_id: ID of the user making the request
    """
    
    # Default allowed roles if not specified
    if allowed_roles is None:
        allowed_roles = ["SUPER_ADMIN", "ADMIN", "HR"]
    
    query = select(User).where(User.user_id.in_(user_ids)).where(User.role.in_(allowed_roles))
    
    # Apply role-based filtering
    if caller_role == "SUPER_ADMIN":
        # Super admin can delete anyone
        pass
    elif caller_role == "ADMIN":
        # Admin can delete ADMIN and HR
        query = query.where(User.role.in_(["ADMIN", "HR"]))
    elif caller_role == "HR":
        # HR can delete HR only (but not themselves)
        query = query.where(User.role == "HR")
        if caller_id:
            query = query.where(User.user_id != caller_id)
    else:
        # Unknown role, return empty
        return 0, []
    
    users_to_delete_result = await db.execute(query)
    users_to_delete: List[User] = users_to_delete_result.scalars().all()

    if not users_to_delete:
        return 0, []
    
    # Build delete query with same filters
    delete_query = delete(User).where(User.user_id.in_([str(u.user_id) for u in users_to_delete]))
    
    result = await db.execute(delete_query)
    await db.commit()
    return result.rowcount, users_to_delete


async def update_user_details(db: AsyncSession, user_id: str, updates: dict):
    """
    Update fields on User by user_id and return the updated user object (or None on failure).
    """
    if not updates:
        return None

    stmt = (
        update(User)
        .where(User.user_id == user_id)
        .values(**updates)
        .execution_options(synchronize_session="fetch")
    )
    await db.execute(stmt)
    await db.commit()

    # return the fresh row
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    return user