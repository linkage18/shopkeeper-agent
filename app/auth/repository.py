from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.jwt import hash_password


class AuthRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, username: str, password: str, role: str = "user") -> User | str:
        existing = await self.session.execute(select(User).where(User.username == username))
        if existing.scalar_one_or_none():
            return "用户名已存在"
        user = User(username=username, password_hash=hash_password(password), role=role)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def login(self, username: str, password: str) -> User | None:
        result = await self.session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user and user.password_hash == hash_password(password):
            return user
        return None

    async def get_by_id(self, user_id: str) -> User | None:
        return await self.session.get(User, user_id)
