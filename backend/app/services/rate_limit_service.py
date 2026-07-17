"""
提问次数限制服务模块

提供提问频率限制的业务逻辑，支持两级限制：
1. 用户级限制：每个用户每天最多提问 USER_DAILY_QUESTION_LIMIT 次
2. 全局限制：所有用户每天最多提问 GLOBAL_DAILY_QUESTION_LIMIT 次

使用 PostgreSQL 的 INSERT ... ON CONFLICT 实现原子性递增，避免并发竞争问题。
"""

import uuid
from datetime import date

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.rate_limit import QuestionRateLimit

settings = get_settings()


async def check_rate_limit(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """检查用户是否超过提问频率限制

    返回字典包含：
    - allowed: 是否允许提问
    - user_remaining: 该用户今日剩余次数
    - global_remaining: 全局今日剩余次数
    """
    today = date.today()

    # 查询用户今日提问次数
    user_result = await db.execute(
        select(QuestionRateLimit.count).where(
            QuestionRateLimit.user_id == user_id,
            QuestionRateLimit.date == today,
        )
    )
    user_count = user_result.scalar_one_or_none() or 0

    # 查询全局今日提问总次数
    global_result = await db.execute(
        select(func.coalesce(func.sum(QuestionRateLimit.count), 0)).where(
            QuestionRateLimit.date == today,
        )
    )
    global_count = global_result.scalar_one() or 0

    user_remaining = max(0, settings.USER_DAILY_QUESTION_LIMIT - user_count)
    global_remaining = max(0, settings.GLOBAL_DAILY_QUESTION_LIMIT - global_count)

    # 取两者中较小的剩余次数作为实际可用次数
    allowed = user_remaining > 0 and global_remaining > 0

    return {
        "allowed": allowed,
        "user_remaining": user_remaining,
        "global_remaining": global_remaining,
    }


async def increment_user_count(db: AsyncSession, user_id: uuid.UUID) -> None:
    """递增用户今日提问计数

    使用 INSERT ... ON CONFLICT 实现原子性操作：
    - 若记录不存在则插入，count 设为 1
    - 若记录已存在则将 count 加 1
    """
    today = date.today()
    # 使用原生 SQL 的 INSERT ... ON CONFLICT 实现原子性 upsert
    stmt = text("""
        INSERT INTO question_rate_limits (id, user_id, date, count, created_at)
        VALUES (gen_random_uuid(), :user_id, :today, 1, NOW())
        ON CONFLICT (user_id, date)
        DO UPDATE SET count = question_rate_limits.count + 1
    """)
    await db.execute(stmt, {"user_id": str(user_id), "today": today})
    await db.flush()
