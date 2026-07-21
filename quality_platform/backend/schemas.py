from pydantic import BaseModel, HttpUrl, EmailStr
from typing import Optional, List
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    role: str = "viewer"

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int

# Auth schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Usage schemas
class UserUsageResponse(BaseModel):
    id: int
    report_type: str
    month: str
    count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UsageLimitsResponse(BaseModel):
    daily_limit: int
    weekly_limit: int
    monthly_limit: int
    magazine_limit: int
    current_month: str
    usage: dict  # {"daily": count, "weekly": count, "monthly": count, "magazine": count}

class UserUsageStatsResponse(BaseModel):
    user_id: int
    username: str
    full_name: str
    role: str
    current_month: str
    limits: dict  # {"daily": limit, "weekly": limit, "monthly": limit, "magazine": limit}
    current_month_usage: dict  # {"daily": count, "weekly": count, "monthly": count, "magazine": count}
    all_time_usage: dict  # {"daily": count, "weekly": count, "monthly": count, "magazine": count}
    usage_records: list  # List of UserUsageResponse

class ResetUsageResponse(BaseModel):
    message: str
    reset_type: str
    user_id: int
    username: str

# Existing schemas
class SourceSchema(BaseModel):
    name: Optional[str] = None

class ArticleBase(BaseModel):
    title: str
    description: Optional[str] = None
    url: str
    publishedAt: Optional[datetime] = None
    source_name: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None  # Family & Society category (e.g. الأسرة والطفولة، الصحة والرفاهية، ...)

class ArticleResponse(ArticleBase):
    id: int
    created_at: datetime
    source: Optional[SourceSchema] = None

    class Config:
        from_attributes = True

class NewsListResponse(BaseModel):
    date: str
    count: int
    articles: List[ArticleResponse]

class SettingBase(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class SettingResponse(SettingBase):
    id: int

    class Config:
        from_attributes = True

# Report schemas
class ReportBase(BaseModel):
    title: str
    report_type: str
    file_path: str
    file_size: Optional[int] = None
    status: str = "pending"
    error_message: Optional[str] = None

class ReportCreate(ReportBase):
    pass

class ReportResponse(ReportBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ReportListResponse(BaseModel):
    reports: List[ReportResponse]
    total: int

class NotificationResponse(BaseModel):
    id: int
    type: str  # "report_generated", "report_failed"
    title: str
    message: str
    report_id: Optional[int] = None
    created_at: datetime
    is_read: bool = False

    class Config:
        from_attributes = True

class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    unread_count: int
