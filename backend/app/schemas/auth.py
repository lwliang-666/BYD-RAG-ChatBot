"""
认证相关请求/响应 Schema 模块

定义注册、登录、Token 刷新的请求体和响应体数据结构，
包含字段校验规则（用户名格式、密码长度等）。
"""

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """用户注册请求体"""
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_一-龥]+$")
    password: str = Field(..., min_length=6, max_length=72)


class LoginRequest(BaseModel):
    """用户登录请求体"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=72)


class TokenResponse(BaseModel):
    """JWT 令牌响应体，包含访问令牌和刷新令牌"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Token 刷新请求体"""
    refresh_token: str
