"""
数据库连接与会话管理模块

使用 SQLAlchemy 异步引擎创建数据库连接池，
提供异步会话工厂和 FastAPI 依赖注入用的 get_db 生成器。
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# 异步数据库引擎，配置连接池大小
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
)

# 异步会话工厂，expire_on_commit=False 避免提交后属性过期
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """ORM 模型基类，所有模型类均继承此类"""
    pass


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取异步数据库会话

    请求正常完成时自动 commit，异常时自动 rollback，
    最终关闭会话。
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
