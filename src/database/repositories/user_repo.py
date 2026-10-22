from typing import Optional
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import History, User

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_identifier(self, identifier: str | int) -> User | None:
        identifier_str = str(identifier).strip()
        if identifier_str.isdigit():
            query = select(User).where(User.user_id == int(identifier_str))
        else:
            clean_username = identifier_str.lstrip("@")
            query = select(User).where(func.lower(User.username) == clean_username.lower())
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def set_ban_status(self, user_id: int, is_banned: bool):
        await self.session.execute(
            update(User).where(User.user_id == user_id).values(is_banned=is_banned)
        )
        await self.session.commit()

    async def set_mute_status(self, user_id: int, is_muted: bool):
        await self.session.execute(
            update(User).where(User.user_id == user_id).values(is_muted=is_muted)
        )
        await self.session.commit()

    async def set_role(self, user_id: int, role: str, is_admin: bool):
        await self.session.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(role=role, is_admin=is_admin)
        )
        await self.session.commit()

    async def get_route_count(self, user_id: int) -> int:
        count = await self.session.scalar(
            select(func.count(History.id)).where(History.user_id == user_id)
        )
        return count or 0

    async def list_users_paginated(
        self,
        offset: int = 0,
        limit: int = 15,
        role_filter: Optional[str] = None,
    ) -> tuple[list[User], int]:
        stmt = select(User)
        count_stmt = select(func.count(User.user_id))

        if role_filter:
            rf = role_filter.upper()
            if rf == "ADMIN":
                condition = (User.role == "ADMIN") | (User.is_admin == True)
                stmt = stmt.where(condition)
                count_stmt = count_stmt.where(condition)
            elif rf == "USER":
                condition = (User.role == "USER") & (User.is_admin == False)
                stmt = stmt.where(condition)
                count_stmt = count_stmt.where(condition)
            elif rf == "SUPERADMIN":
                condition = User.role == "SUPERADMIN"
                stmt = stmt.where(condition)
                count_stmt = count_stmt.where(condition)

        total = await self.session.scalar(count_stmt) or 0
        result = await self.session.execute(
            stmt.order_by(User.user_id.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_all_active_user_ids(self) -> list[int]:
        """Fetch all user IDs that are not banned, for broadcast dispatch."""
        result = await self.session.execute(
            select(User.user_id).where(User.is_banned == False)
        )
        return [row[0] for row in result.all()]
