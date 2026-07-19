from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import User

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_identifier(self, identifier: str | int) -> User | None:
        identifier_str = str(identifier)
        if identifier_str.isdigit():
            query = select(User).where(User.user_id == int(identifier_str))
        else:
            clean_username = identifier_str.lstrip('@')
            query = select(User).where(User.username == clean_username)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def set_ban_status(self, user_id: int, is_banned: bool):
        await self.session.execute(
            update(User).where(User.user_id == user_id).values(is_banned=is_banned)
        )
        await self.session.commit()