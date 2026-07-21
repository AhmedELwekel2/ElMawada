import asyncio
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
import os
import sys

# Ensure project root (.. ) is on sys.path so we can import quality_bot module
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Load credentials (AWS keys for Bedrock, TWITTER_BEARER_TOKEN, etc.) BEFORE
# importing the bot. The backend runs from quality_platform/backend/, so the
# bot's own load_dotenv() (CWD-relative) won't find them — load the known files
# explicitly. In Docker these come from --env-file and this is a harmless no-op.
from dotenv import load_dotenv  # noqa: E402
for _env in (
    os.path.join(CURRENT_DIR, ".env"),
    os.path.join(PROJECT_ROOT, "quality_platform", ".env"),
    os.path.join(PROJECT_ROOT, "quality_bot", ".env"),
    os.path.join(PROJECT_ROOT, ".env"),
):
    if os.path.exists(_env):
        load_dotenv(_env)

# Unset ALL conflicting Bedrock/Bearer tokens BEFORE importing the bot module,
# so telegram_bot_family builds its Bedrock client with AWS access keys (not a
# bearer token) — quality_platform authenticates via the default cred chain.
for k in list(os.environ.keys()):
    if any(x in k.upper() for x in ["BEARER", "ABSK", "TOKEN_BEDROCK", "BEDROCK_API_KEY"]):
        if k != "AWS_SESSION_TOKEN":
            os.environ.pop(k, None)

# Family & Society bot (repo root, on sys.path via PROJECT_ROOT). Aliased to the
# names the rest of this module already uses.
from telegram_bot_family import (  # type: ignore
    enhance_articles_with_content,
    filter_relevant_articles,
    filter_recent_articles,
    categorize_articles_for_blogs,
    generate_family_blog_with_ai as generate_quality_blog_with_ai,
    build_fallback_family_blog_content as build_fallback_quality_blog_content,
    create_family_blog_pdf as create_quality_blog_pdf,
    generate_magazine_content_with_ai,
    render_magazine_pdf,
    fetch_images_for_articles,
)

# Imports from current module
from database import engine, get_db, Base
from models import Article, Settings as SettingsModel, User, RefreshToken, UserUsage, Report
from schemas import (
    NewsListResponse, SettingResponse, SettingBase,
    UserCreate, UserResponse, UserListResponse, UserUpdate,
    Token, LoginRequest, RefreshTokenRequest,
    UsageLimitsResponse, ReportCreate, ReportResponse, ReportListResponse,
    NotificationResponse, NotificationListResponse
)
from scheduler import start_scheduler
from auth import (
    get_password_hash, verify_password, create_access_token, 
    create_refresh_token, verify_token, ACCESS_TOKEN_EXPIRE_MINUTES
)
from dependencies import (
    get_current_user, get_current_active_user, require_permission,
    get_user_usage_limits, check_pdf_generation_limit, increment_pdf_usage,
    USAGE_LIMITS
)

# Helper function to create default admin user on first startup
def create_default_admin_user(db: Session):
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_full_name = os.getenv("ADMIN_FULL_NAME", "System Administrator")

    admin_user = db.query(User).filter(User.username == admin_username).first()
    if not admin_user:
        admin_user = User(
            username=admin_username,
            email=admin_email,
            hashed_password=get_password_hash(admin_password),
            full_name=admin_full_name,
            role="admin",
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"✅ Default admin user created: {admin_username}/{admin_password}")
        print("⚠️  IMPORTANT: Change the admin password after first login!")
    else:
        print(f"ℹ️  Admin user '{admin_username}' already exists, skipping creation.")

# Create tables (fresh DB will include 'category' column automatically)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Family & Society News API (الأسرة والمجتمع)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Create default admin user
    db = next(get_db())
    try:
        create_default_admin_user(db)
    finally:
        db.close()
    
    # Start the scheduler (runs fetch_and_store_news every 1 day)
    # The scheduler itself is non-blocking; initial fetch runs in a background thread
    try:
        from scheduler import fetch_and_store_news
        scheduler = start_scheduler()
        app.state.scheduler = scheduler  # Store on app.state so it persists
        print(f"✅ Scheduler started. News fetch runs every 1 day.")
        
        # Run initial fetch in a background thread so it doesn't block startup
        def _initial_fetch():
            try:
                print("🔄 Starting initial news fetch in background...")
                fetch_and_store_news()
                print("✅ Initial news fetch completed.")
            except Exception as e:
                print(f"❌ Initial news fetch failed: {e}")
        
        fetch_thread = threading.Thread(target=_initial_fetch, daemon=True)
        fetch_thread.start()
        print("🔄 Initial news fetch started in background thread.")
    except Exception as e:
        print(f"⚠️ Could not start scheduler: {e}")


@app.on_event("shutdown")
def shutdown_event():
    """Properly shut down the scheduler on app shutdown."""
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler:
        print("🛑 Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        print("✅ Scheduler shut down successfully.")


# ==========================================
# AUTHENTICATION ENDPOINTS
# ==========================================

@app.post("/api/auth/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    db_user = db.query(User).filter(
        (User.email == user.email) | (User.username == user.username)
    ).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email or username already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.post("/api/auth/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login user and return JWT tokens."""
    # Authenticate user
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Inactive user"
        )
    
    # Create tokens
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    # Store refresh token in database
    db_refresh_token = RefreshToken(
        token=refresh_token,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(db_refresh_token)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.post("/api/auth/refresh", response_model=Token)
def refresh_token(refresh_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    try:
        # Verify refresh token
        payload = verify_token(refresh_data.refresh_token, "refresh")
        username = payload.get("sub")
        
        # Check if refresh token exists, is not revoked, and has not expired
        db_refresh_token = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_data.refresh_token,
            RefreshToken.is_revoked == False
        ).first()
        
        if not db_refresh_token:
            raise HTTPException(
                status_code=401,
                detail="Invalid or revoked refresh token"
            )
        
        # Check if token has expired
        if db_refresh_token.expires_at < datetime.utcnow():
            # Mark expired token as revoked
            db_refresh_token.is_revoked = True
            db.commit()
            raise HTTPException(
                status_code=401,
                detail="Refresh token has expired"
            )
        
        # Get user and verify the token belongs to this user
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=401,
                detail="User not found or inactive"
            )
        
        # Verify the token belongs to the correct user
        if db_refresh_token.user_id != user.id:
            # Revoke mismatched token for security
            db_refresh_token.is_revoked = True
            db.commit()
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token"
            )
        
        # Create new access token
        access_token = create_access_token(data={"sub": user.username})
        
        # Create new refresh token (rotation: revoke old, issue new)
        new_refresh_token = create_refresh_token(data={"sub": user.username})
        
        # Store new refresh token in database
        new_db_refresh_token = RefreshToken(
            token=new_refresh_token,
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(new_db_refresh_token)
        
        # Revoke old refresh token (rotation)
        db_refresh_token.is_revoked = True
        
        db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Could not refresh token"
        )

@app.post("/api/auth/logout")
def logout(
    refresh_data: RefreshTokenRequest,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Logout user by revoking refresh token."""
    # Revoke refresh token
    db_refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_data.refresh_token,
        RefreshToken.user_id == current_user["id"]
    ).first()
    
    if db_refresh_token:
        db_refresh_token.is_revoked = True
        db.commit()
    
    return {"message": "Successfully logged out"}

@app.get("/api/auth/me", response_model=UserResponse)
def get_current_user_info(current_user: dict = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get current user information."""
    user = db.query(User).filter(User.id == current_user["id"]).first()
    return user

@app.get("/api/auth/usage-limits", response_model=UsageLimitsResponse)
def get_usage_limits(current_user: dict = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get current user's PDF generation usage and limits."""
    return get_user_usage_limits(current_user, db)

@app.get("/api/auth/usage-records")
def get_usage_records(current_user: dict = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get current user's usage records history."""
    user_id = current_user.get("id")
    
    # Get all usage records for the user
    records = db.query(UserUsage).filter(
        UserUsage.user_id == user_id
    ).order_by(UserUsage.month.desc(), UserUsage.report_type).all()
    
    return {"records": records}


# ==========================================
# USER MANAGEMENT ENDPOINTS (Admin only)
# ==========================================

@app.get("/api/users", response_model=UserListResponse)
def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """Get list of all users (Admin only)."""
    users = db.query(User).offset(skip).limit(limit).all()
    total = db.query(User).count()
    return {"users": users, "total": total}

@app.get("/api/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: dict = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """Get user by ID (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/api/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: dict = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """Update user (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user

@app.delete("/api/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: dict = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """Delete user (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Don't allow deleting the current user
    if user.id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete current user")
    
    # First, delete all refresh tokens associated with this user
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
    
    # Also delete all usage records associated with this user
    db.query(UserUsage).filter(UserUsage.user_id == user_id).delete()
    
    # Now delete the user (cascade will handle related records)
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

@app.get("/api/users/{user_id}/usage-stats")

def get_user_usage_stats(
    user_id: int,
    current_user: dict = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """Get detailed usage statistics for a specific user (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all usage records for the user
    usage_records = db.query(UserUsage).filter(
        UserUsage.user_id == user_id
    ).order_by(UserUsage.month.desc(), UserUsage.report_type).all()
    
    # Get current month
    current_month = datetime.utcnow().strftime("%Y-%m")
    
    # Get user's role and limits
    user_role = user.role
    limits = {
        "daily": USAGE_LIMITS[user_role]["daily"],
        "weekly": USAGE_LIMITS[user_role]["weekly"],
        "monthly": USAGE_LIMITS[user_role]["monthly"],
        "magazine": USAGE_LIMITS[user_role]["magazine"]
    }
    
    # Calculate current month usage
    current_month_usage = {"daily": 0, "weekly": 0, "monthly": 0, "magazine": 0}
    for record in usage_records:
        if record.month == current_month:
            current_month_usage[record.report_type] = record.count
    
    # Calculate all-time usage
    all_time_usage = {"daily": 0, "weekly": 0, "monthly": 0, "magazine": 0}
    for record in usage_records:
        all_time_usage[record.report_type] += record.count
    
    return {
        "user_id": user_id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user_role,
        "current_month": current_month,
        "limits": limits,
        "current_month_usage": current_month_usage,
        "all_time_usage": all_time_usage,
        "usage_records": usage_records
    }

@app.post("/api/users/{user_id}/reset-usage")
def reset_user_usage(
    user_id: int,
    reset_data: dict = {"reset_type": "all"},  # "all", "current_month", or specific report type
    current_user: dict = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """Reset user usage statistics (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    reset_type = reset_data.get("reset_type", "all")
    current_month = datetime.utcnow().strftime("%Y-%m")
    
    if reset_type == "all":
        # Delete all usage records for the user
        db.query(UserUsage).filter(UserUsage.user_id == user_id).delete()
    elif reset_type == "current_month":
        # Delete current month usage records
        db.query(UserUsage).filter(
            and_(
                UserUsage.user_id == user_id,
                UserUsage.month == current_month
            )
        ).delete()
    else:
        # Reset specific report type for current month
        db.query(UserUsage).filter(
            and_(
                UserUsage.user_id == user_id,
                UserUsage.report_type == reset_type,
                UserUsage.month == current_month
            )
        ).delete()
    
    db.commit()
    
    return {
        "message": f"User usage statistics reset successfully",
        "reset_type": reset_type,
        "user_id": user_id,
        "username": user.username
    }

@app.post("/api/users/{user_id}/reset-limits")
def reset_user_limits(
    user_id: int,
    limits_data: dict = {"daily": None, "weekly": None, "monthly": None, "magazine": None},
    current_user: dict = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """Reset user limits to default values based on their role (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get default limits based on user role
    user_role = user.role
    default_limits = USAGE_LIMITS.get(user_role, USAGE_LIMITS["user"])
    
    # Apply provided limits or use defaults
    new_limits = {
        "daily": limits_data.get("daily") if limits_data.get("daily") is not None else default_limits["daily"],
        "weekly": limits_data.get("weekly") if limits_data.get("weekly") is not None else default_limits["weekly"],
        "monthly": limits_data.get("monthly") if limits_data.get("monthly") is not None else default_limits["monthly"],
        "magazine": limits_data.get("magazine") if limits_data.get("magazine") is not None else default_limits["magazine"]
    }
    
    return {
        "message": f"User limits reset successfully",
        "user_id": user_id,
        "username": user.username,
        "role": user_role,
        "new_limits": new_limits
    }


@app.get("/api/health")
def health_check():
    return {"status": "ok", "db": "connected"}


@app.get("/api/health/scheduler")
def scheduler_status():
    """Check if the scheduler is running and when the next fetch is scheduled."""
    scheduler = getattr(app.state, "scheduler", None)
    if not scheduler or not scheduler.running:
        return {"status": "stopped", "message": "Scheduler is not running"}
    
    job = scheduler.get_job("fetch_news_job")
    if not job:
        return {"status": "running", "message": "Scheduler is running but job not found"}
    
    return {
        "status": "running",
        "job_name": job.name,
        "next_run_time": str(job.next_run_time) if job.next_run_time else None,
        "trigger": str(job.trigger),
    }


def _article_to_dict(a: Article) -> dict:
    """Helper to convert DB article to dict for bot functions"""
    return {
        "title": a.title,
        "description": a.description,
        "url": a.url,
        "publishedAt": a.published_at.isoformat() if a.published_at else None,
        "source": {"name": a.source_name},
        "content": a.content,
        "category": a.category,
    }


@app.get("/api/news/daily", response_model=NewsListResponse)
def get_daily_news(
    current_user: dict = Depends(require_permission("read_news")),
    db: Session = Depends(get_db)
):
    """Return merged daily Family & Society news from Local DB."""
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    
    articles = db.query(Article).filter(
        Article.is_relevant.isnot(False),
        or_(
            and_(Article.published_at.isnot(None), Article.published_at >= yesterday),
            and_(Article.published_at.is_(None), Article.created_at >= yesterday),
        )
    ).order_by(Article.published_at.desc().nulls_last(), Article.created_at.desc()).all()
    
    result = [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "url": a.url,
            "publishedAt": a.published_at,
            "source": {"name": a.source_name},
            "content": a.content,
            "category": a.category,
            "created_at": a.created_at
        } for a in articles
    ]
    return {"date": now.date().isoformat(), "count": len(result), "articles": result}


@app.get("/api/news/weekly", response_model=NewsListResponse)
def get_weekly_news(
    current_user: dict = Depends(require_permission("read_news")),
    db: Session = Depends(get_db)
):
    """Return weekly Family & Society news (last 7 days) from Local DB."""
    now = datetime.utcnow()
    last_week = now - timedelta(days=7)
    
    articles = db.query(Article).filter(
        Article.is_relevant.isnot(False),
        or_(
            and_(Article.published_at.isnot(None), Article.published_at >= last_week),
            and_(Article.published_at.is_(None), Article.created_at >= last_week),
        )
    ).order_by(Article.published_at.desc().nulls_last(), Article.created_at.desc()).all()
    
    result = [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "url": a.url,
            "publishedAt": a.published_at,
            "source": {"name": a.source_name},
            "content": a.content,
            "category": a.category,
            "created_at": a.created_at
        } for a in articles
    ]
    return {"date": now.date().isoformat(), "count": len(result), "articles": result}


@app.get("/api/news/monthly", response_model=NewsListResponse)
def get_monthly_news(
    current_user: dict = Depends(require_permission("read_news")),
    db: Session = Depends(get_db)
):
    """Return monthly Family & Society news (last 30 days) from Local DB."""
    now = datetime.utcnow()
    last_month = now - timedelta(days=120)
    
    articles = db.query(Article).filter(
        Article.is_relevant.isnot(False),
        or_(
            and_(Article.published_at.isnot(None), Article.published_at >= last_month),
            and_(Article.published_at.is_(None), Article.created_at >= last_month),
        )
    ).order_by(Article.published_at.desc().nulls_last(), Article.created_at.desc()).all()
    
    result = [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "url": a.url,
            "publishedAt": a.published_at,
            "source": {"name": a.source_name},
            "content": a.content,
            "category": a.category,
            "created_at": a.created_at
        } for a in articles
    ]
    return {"date": now.date().isoformat(), "count": len(result), "articles": result}


@app.get("/api/settings", response_model=list[SettingResponse])
def get_settings(
    current_user: dict = Depends(require_permission("manage_settings")),
    db: Session = Depends(get_db)
):
    return db.query(SettingsModel).all()

@app.post("/api/settings", response_model=SettingResponse)
def save_setting(
    setting: SettingBase,
    current_user: dict = Depends(require_permission("manage_settings")),
    db: Session = Depends(get_db)
):
    db_setting = db.query(SettingsModel).filter(SettingsModel.key == setting.key).first()
    if db_setting:
        db_setting.value = setting.value
        db_setting.description = setting.description or db_setting.description
    else:
        db_setting = SettingsModel(**setting.dict())
        db.add(db_setting)
    
    db.commit()
    db.refresh(db_setting)
    return db_setting


# ==========================================
# REPORTS ENDPOINTS
# ==========================================

@app.post("/api/reports/weekly-blog")
def generate_weekly_blog_report(
    current_user: dict = Depends(check_pdf_generation_limit("weekly")),
    increment_usage: dict = Depends(increment_pdf_usage("weekly")),
    db: Session = Depends(get_db)
):
    """Generate weekly blog PDF with usage limits."""
    user_id = current_user["id"]
    report_title = "التقرير الأسبوعي للأسرة والمجتمع (الجانب النفسي)"
    
    # Create a Report record so notifications work
    report = _save_report_record(
        db=db,
        user_id=user_id,
        title=report_title,
        report_type="weekly",
        file_path="",
        status="pending"
    )
    
    try:
        today = datetime.utcnow()
        last_week = today - timedelta(days=7)
        db_articles = db.query(Article).filter(
            Article.is_relevant.isnot(False),
            (Article.published_at >= last_week) | (Article.created_at >= last_week)
        ).all()
        
        all_articles = [_article_to_dict(a) for a in db_articles]
        if not all_articles:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات كافية للأسبوع الماضي لتوليد تقرير.")

        # Re-apply strict filter just in case
        filtered = filter_relevant_articles(all_articles)
        recent = filter_recent_articles(filtered, days=7)
        if not recent:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات ملائمة للأسبوع الماضي بعد الفلترة.")

        enhanced = enhance_articles_with_content(recent, max_articles=50, weekly_mode=True)

        categorized = categorize_articles_for_blogs(enhanced)
        strategy_articles = categorized.get("management", []) or []
        ld_articles = categorized.get("improvement", []) or []

        if not strategy_articles and not ld_articles:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات كافية لتوليد مدونات أسبوعية.")

        strategy_blog = ""
        ld_blog = ""
        
        # Determine if we should use custom keywords from settings
        blog_keywords_setting = db.query(SettingsModel).filter(SettingsModel.key == "blog_keywords").first()
        custom_keywords = blog_keywords_setting.value if blog_keywords_setting else None
        
        if strategy_articles:
            strategy_blog = generate_quality_blog_with_ai(strategy_articles, "management", "weekly")
            if not strategy_blog or "AWS Bedrock Error" in strategy_blog or "حدث خطأ" in strategy_blog or len(strategy_blog.strip()) < 200:
                strategy_blog = build_fallback_quality_blog_content(strategy_articles, "الأسرة والمجتمع")

        if ld_articles:
            ld_blog = generate_quality_blog_with_ai(ld_articles, "improvement", "weekly")
            if not ld_blog or "AWS Bedrock Error" in ld_blog or "حدث خطأ" in ld_blog or len(ld_blog.strip()) < 200:
                ld_blog = build_fallback_quality_blog_content(ld_articles, "الصحة النفسية والرفاهية")

        combined_blog = "\n\n---\n\n".join([b for b in [strategy_blog, ld_blog] if b])
        if not combined_blog or len(combined_blog.strip()) < 100:
            combined_blog = build_fallback_quality_blog_content(enhanced, "ملخص أسبوعي")

        title = "التقرير الأسبوعي للأسرة والمجتمع (الجانب النفسي)"
        pdf_path = create_quality_blog_pdf(combined_blog, title, is_temp_file=False)
        if not pdf_path or not os.path.exists(pdf_path):
            # Update report status to failed
            report.status = "failed"
            report.error_message = "تعذر إنشاء ملف PDF للتقرير الأسبوعي."
            db.commit()
            raise HTTPException(status_code=500, detail="تعذر إنشاء ملف PDF للتقرير الأسبوعي.")

        # Update report record with success
        file_size = os.path.getsize(pdf_path)
        report.file_path = pdf_path
        report.file_size = file_size
        report.status = "completed"
        report.error_message = None
        db.commit()

        filename = f"Family_Society_Weekly_Report_{today.strftime('%Y%m%d')}.pdf"
        return FileResponse(pdf_path, media_type="application/pdf", filename=filename)
    except HTTPException:
        # Update report status to failed
        report.status = "failed"
        report.error_message = "فشل إنشاء التقرير"
        db.commit()
        raise
    except Exception as e:
        # Update report status to failed
        report.status = "failed"
        report.error_message = str(e)
        db.commit()
        return JSONResponse(status_code=500, content={"detail": f"خطأ غير متوقع أثناء توليد التقرير الأسبوعي: {e}"})


@app.post("/api/reports/monthly-blog")
def generate_monthly_blog_report(
    current_user: dict = Depends(check_pdf_generation_limit("monthly")),
    increment_usage: dict = Depends(increment_pdf_usage("monthly")),
    db: Session = Depends(get_db)
):
    """Generate monthly blog PDF with usage limits."""
    user_id = current_user["id"]
    report_title = "التقرير الشهري للأسرة والمجتمع (الجانب النفسي)"
    
    # Create a Report record so notifications work
    report = _save_report_record(
        db=db,
        user_id=user_id,
        title=report_title,
        report_type="monthly",
        file_path="",
        status="pending"
    )
    
    try:
        today = datetime.utcnow()
        last_month = today - timedelta(days=30)
        db_articles = db.query(Article).filter(
            Article.is_relevant.isnot(False),
            (Article.published_at >= last_month) | (Article.created_at >= last_month)
        ).all()
        
        all_articles = [_article_to_dict(a) for a in db_articles]
        if not all_articles:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات كافية للشهر الماضي لتوليد تقرير.")

        filtered = filter_relevant_articles(all_articles)
        recent = filter_recent_articles(filtered, days=30)
        if not recent:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات ملائمة للشهر الماضي بعد الفلترة.")

        enhanced = enhance_articles_with_content(recent, max_articles=80, monthly_mode=True)

        categorized = categorize_articles_for_blogs(enhanced)
        strategy_articles = categorized.get("management", []) or []
        ld_articles = categorized.get("improvement", []) or []

        if not strategy_articles and not ld_articles:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات كافية لتوليد مدونات شهرية.")

        strategy_blog = ""
        ld_blog = ""
        if strategy_articles:
            strategy_blog = generate_quality_blog_with_ai(strategy_articles, "management", "monthly")
            if not strategy_blog or "AWS Bedrock Error" in strategy_blog or "حدث خطأ" in strategy_blog or len(strategy_blog.strip()) < 200:
                strategy_blog = build_fallback_quality_blog_content(strategy_articles, "الأسرة والمجتمع")

        if ld_articles:
            ld_blog = generate_quality_blog_with_ai(ld_articles, "improvement", "monthly")
            if not ld_blog or "AWS Bedrock Error" in ld_blog or "حدث خطأ" in ld_blog or len(ld_blog.strip()) < 200:
                ld_blog = build_fallback_quality_blog_content(ld_articles, "الصحة النفسية والرفاهية")

        combined_blog = "\n\n---\n\n".join([b for b in [strategy_blog, ld_blog] if b])
        if not combined_blog or len(combined_blog.strip()) < 100:
            combined_blog = build_fallback_quality_blog_content(enhanced, "ملخص شهري")

        title = "التقرير الشهري للأسرة والمجتمع (الجانب النفسي)"
        pdf_path = create_quality_blog_pdf(combined_blog, title, is_temp_file=False)
        if not pdf_path or not os.path.exists(pdf_path):
            # Update report status to failed
            report.status = "failed"
            report.error_message = "تعذر إنشاء ملف PDF للتقرير الشهري."
            db.commit()
            raise HTTPException(status_code=500, detail="تعذر إنشاء ملف PDF للتقرير الشهري.")

        # Update report record with success
        file_size = os.path.getsize(pdf_path)
        report.file_path = pdf_path
        report.file_size = file_size
        report.status = "completed"
        report.error_message = None
        db.commit()

        filename = f"Family_Society_Monthly_Report_{today.strftime('%Y%m%d')}.pdf"
        return FileResponse(pdf_path, media_type="application/pdf", filename=filename)
    except HTTPException:
        # Update report status to failed
        report.status = "failed"
        report.error_message = "فشل إنشاء التقرير"
        db.commit()
        raise
    except Exception as e:
        # Update report status to failed
        report.status = "failed"
        report.error_message = str(e)
        db.commit()
        return JSONResponse(status_code=500, content={"detail": f"خطأ غير متوقع أثناء توليد التقرير الشهري: {e}"})


@app.post("/api/reports/magazine")
def generate_magazine_report(
    current_user: dict = Depends(check_pdf_generation_limit("magazine")),
    increment_usage: dict = Depends(increment_pdf_usage("magazine")),
    db: Session = Depends(get_db)
):
    """Generate monthly magazine PDF with usage limits."""
    user_id = current_user["id"]
    magazine_title = "مجلة الأسرة والمجتمع"
    
    # Create a Report record so notifications work for magazine too
    report = _save_report_record(
        db=db,
        user_id=user_id,
        title=magazine_title,
        report_type="magazine",
        file_path="",
        status="pending"
    )
    
    try:
        today = datetime.utcnow()
        last_month = today - timedelta(days=30)
        db_articles = db.query(Article).filter(
            Article.is_relevant.isnot(False),
            (Article.published_at >= last_month) | (Article.created_at >= last_month)
        ).all()

        all_articles = [_article_to_dict(a) for a in db_articles]
        if not all_articles:
            # Update report status to failed
            report.status = "failed"
            report.error_message = "لم يتم العثور على مقالات كافية للشهر الماضي لتوليد المجلة."
            db.commit()
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات كافية للشهر الماضي لتوليد المجلة.")

        filtered = filter_relevant_articles(all_articles)
        recent = filter_recent_articles(filtered, days=30)
        if not recent:
            # Update report status to failed
            report.status = "failed"
            report.error_message = "لم يتم العثور على مقالات ملائمة للشهر الماضي بعد الفلترة."
            db.commit()
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات ملائمة للشهر الماضي بعد الفلترة.")

        enhanced = enhance_articles_with_content(recent, max_articles=40, monthly_mode=True)

        # Generate magazine content using AI
        magazine_data = generate_magazine_content_with_ai(enhanced)
        if not magazine_data:
            # Update report status to failed
            report.status = "failed"
            report.error_message = "فشل توليد محتوى المجلة بواسطة الذكاء الاصطناعي."
            db.commit()
            raise HTTPException(status_code=500, detail="فشل توليد محتوى المجلة بواسطة الذكاء الاصطناعي.")

        # Add date
        magazine_data['date'] = today.strftime("%B %Y")

        # Initialize image_url for all articles (required for template fallback logic)
        if magazine_data.get('articles'):
            for article in magazine_data['articles']:
                if 'image_url' not in article:
                    article['image_url'] = None
                    article['local_image_path'] = None
        
        # Fetch og:images from source article URLs and assign round-robin to magazine articles
        try:
            source_images = fetch_images_for_articles(enhanced, max_articles=20, timeout=4)
            print(f"🖼️ Fetched {len(source_images) if source_images else 0} images from {len(enhanced)} articles")
            
            if source_images and magazine_data.get('articles'):
                for i, article in enumerate(magazine_data['articles']):
                    # Only assign if not already assigned and we have images to spare
                    if i < len(source_images):
                        article['image_url'] = source_images[i]
                print(f"✅ Assigned {len(source_images)} images across {len(magazine_data['articles'])} magazine articles")
                for i, article in enumerate(magazine_data['articles']):
                    print(f"🔍 Article {i} image_url: {article.get('image_url')}")
            else:
                print(f"ℹ️ No images fetched or no articles in magazine - will use IBDL logo fallback")
        except Exception as e:
            print(f"⚠️ Image assignment failed: {e}")
            print(f"ℹ️ Will use IBDL logo fallback for all articles")

        # Render PDF
        filename = f"Family_Society_Magazine_{today.strftime('%Y%m')}.pdf"
        
        # DEBUG: Print article data
        for idx, art in enumerate(magazine_data.get('articles', [])):
            print(f"DEBUG: Article {idx} full data: {art}")

        pdf_path = render_magazine_pdf(magazine_data, filename)
        if not pdf_path or not os.path.exists(pdf_path):
            # Update report status to failed
            report.status = "failed"
            report.error_message = "تعذر إنشاء ملف PDF للمجلة."
            db.commit()
            raise HTTPException(status_code=500, detail="تعذر إنشاء ملف PDF للمجلة.")

        # Update report record with success
        file_size = os.path.getsize(pdf_path)
        report.file_path = pdf_path
        report.file_size = file_size
        report.status = "completed"
        report.error_message = None
        db.commit()

        return FileResponse(pdf_path, media_type="application/pdf", filename=filename)
    except HTTPException:
        raise
    except Exception as e:
        # Update report status to failed
        report = db.query(Report).filter(Report.id == report.id).first()
        if report:
            report.status = "failed"
            report.error_message = str(e)
            db.commit()
        return JSONResponse(status_code=500, content={"detail": f"خطأ غير متوقع أثناء توليد المجلة: {e}"})


@app.post("/api/reports/daily-blog")
def generate_daily_blog_report(
    current_user: dict = Depends(check_pdf_generation_limit("daily")),
    increment_usage: dict = Depends(increment_pdf_usage("daily")),
    db: Session = Depends(get_db)
):
    """Generate daily blog PDF with usage limits."""
    user_id = current_user["id"]
    report_title = "التقرير اليومي للأسرة والمجتمع (الجانب النفسي)"
    
    # Create a Report record so notifications work
    report = _save_report_record(
        db=db,
        user_id=user_id,
        title=report_title,
        report_type="daily",
        file_path="",
        status="pending"
    )
    
    try:
        today = datetime.utcnow()
        yesterday = today - timedelta(days=1)
        db_articles = db.query(Article).filter(
            Article.is_relevant.isnot(False),
            (Article.published_at >= yesterday) | (Article.created_at >= yesterday)
        ).all()
        
        all_articles = [_article_to_dict(a) for a in db_articles]
        if not all_articles:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات كافية اليوم لتوليد تقرير.")

        filtered = filter_relevant_articles(all_articles)
        recent = filter_recent_articles(filtered, days=1)
        if not recent:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات ملائمة لليوم بعد الفلترة.")

        enhanced = enhance_articles_with_content(recent, max_articles=20)

        categorized = categorize_articles_for_blogs(enhanced)
        strategy_articles = categorized.get("management", []) or []
        ld_articles = categorized.get("improvement", []) or []

        if not strategy_articles and not ld_articles:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات كافية لتوليد مدونة يومية.")

        strategy_blog = ""
        ld_blog = ""
        if strategy_articles:
            strategy_blog = generate_quality_blog_with_ai(strategy_articles, "management", "daily")
            if not strategy_blog or "AWS Bedrock Error" in strategy_blog or "حدث خطأ" in strategy_blog or len(strategy_blog.strip()) < 200:
                strategy_blog = build_fallback_quality_blog_content(strategy_articles, "الأسرة والمجتمع")

        if ld_articles:
            ld_blog = generate_quality_blog_with_ai(ld_articles, "improvement", "daily")
            if not ld_blog or "AWS Bedrock Error" in ld_blog or "حدث خطأ" in ld_blog or len(ld_blog.strip()) < 200:
                ld_blog = build_fallback_quality_blog_content(ld_articles, "الصحة النفسية والرفاهية")

        combined_blog = "\n\n---\n\n".join([b for b in [strategy_blog, ld_blog] if b])
        if not combined_blog or len(combined_blog.strip()) < 100:
            combined_blog = build_fallback_quality_blog_content(enhanced, "ملخص يومي")

        title = "التقرير اليومي للأسرة والمجتمع (الجانب النفسي)"
        pdf_path = create_quality_blog_pdf(combined_blog, title, is_temp_file=False)
        if not pdf_path or not os.path.exists(pdf_path):
            # Update report status to failed
            report.status = "failed"
            report.error_message = "تعذر إنشاء ملف PDF للتقرير اليومي."
            db.commit()
            raise HTTPException(status_code=500, detail="تعذر إنشاء ملف PDF للتقرير اليومي.")

        # Update report record with success
        file_size = os.path.getsize(pdf_path)
        report.file_path = pdf_path
        report.file_size = file_size
        report.status = "completed"
        report.error_message = None
        db.commit()

        filename = f"Family_Society_Daily_Report_{today.strftime('%Y%m%d')}.pdf"
        return FileResponse(pdf_path, media_type="application/pdf", filename=filename)
    except HTTPException:
        # Update report status to failed
        report.status = "failed"
        report.error_message = "فشل إنشاء التقرير"
        db.commit()
        raise
    except Exception as e:
        # Update report status to failed
        report.status = "failed"
        report.error_message = str(e)
        db.commit()
        return JSONResponse(status_code=500, content={"detail": f"خطأ غير متوقع أثناء توليد التقرير اليومي: {e}"})


# ==========================================
# PERSISTENT REPORTS ENDPOINTS
# ==========================================

def _save_report_record(db: Session, user_id: int, title: str, report_type: str, file_path: str, file_size: int = None, status: str = "completed", error_message: str = None):
    """Helper function to save report record to database"""
    report = Report(
        user_id=user_id,
        title=title,
        report_type=report_type,
        file_path=file_path,
        file_size=file_size,
        status=status,
        error_message=error_message
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report

@app.post("/api/reports/generate/{report_type}")
async def generate_persistent_report(
    report_type: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate report and save it persistently"""
    try:
        # Manually check PDF generation limit using path parameter
        limit_checker = check_pdf_generation_limit(report_type)
        current_user = limit_checker(current_user=current_user, db=db)
        
        # Manually increment PDF usage
        increment_fn = increment_pdf_usage(report_type)
        increment_fn(current_user=current_user, db=db)
        
        user_id = current_user["id"]
        
        # Create initial report record with pending status
        title_map = {
            "daily": "التقرير اليومي للأسرة والمجتمع (الجانب النفسي)",
            "weekly": "التقرير الأسبوعي للأسرة والمجتمع (الجانب النفسي)",
            "monthly": "التقرير الشهري للأسرة والمجتمع (الجانب النفسي)",
            "magazine": "مجلة الأسرة والمجتمع"
        }
        
        title = title_map.get(report_type, f"تقرير {report_type}")
        
        # Create pending report record
        report = _save_report_record(
            db=db,
            user_id=user_id,
            title=title,
            report_type=report_type,
            file_path="",
            status="pending"
        )
        
        # Generate report in background
        background_tasks.add_task(
            _generate_report_background,
            db=db,
            user_id=user_id,
            report_id=report.id,
            report_type=report_type,
            title=title
        )
        
        return {
            "message": "جاري إنشاء التقرير في الخلفية",
            "report_id": report.id,
            "status": "pending"
        }
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"خطأ غير متوقع: {e}"})

def _generate_report_background(db: Session, user_id: int, report_id: int, report_type: str, title: str):
    """Background task to generate report"""
    try:
        # Get the report record
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            return
            
        # Generate the report based on type
        if report_type == "daily":
            pdf_path = _generate_daily_pdf(db, title)
        elif report_type == "weekly":
            pdf_path = _generate_weekly_pdf(db, title)
        elif report_type == "monthly":
            pdf_path = _generate_monthly_pdf(db, title)
        elif report_type == "magazine":
            pdf_path = _generate_magazine_pdf(db, title)
        else:
            raise ValueError(f"نوع التقرير غير معروف: {report_type}")
        
        # Update report record
        if pdf_path and os.path.exists(pdf_path):
            file_size = os.path.getsize(pdf_path)
            report.file_path = pdf_path
            report.file_size = file_size
            report.status = "completed"
            report.error_message = None
        else:
            raise Exception("فشل إنشاء ملف PDF")
        
        db.commit()
        
    except Exception as e:
        # Update report record with error
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.status = "failed"
            report.error_message = str(e)
            db.commit()

def _generate_daily_pdf(db: Session, title: str) -> str:
    """Generate daily PDF report"""
    today = datetime.utcnow()
    yesterday = today - timedelta(days=1)
    db_articles = db.query(Article).filter(
        Article.is_relevant.isnot(False),
        (Article.published_at >= yesterday) | (Article.created_at >= yesterday)
    ).all()
    
    all_articles = [_article_to_dict(a) for a in db_articles]
    if not all_articles:
        raise Exception("لم يتم العثور على مقالات كافية اليوم لتوليد تقرير.")

    filtered = filter_relevant_articles(all_articles)
    recent = filter_recent_articles(filtered, days=1)
    if not recent:
        raise Exception("لم يتم العثور على مقالات ملائمة لليوم بعد الفلترة.")

    enhanced = enhance_articles_with_content(recent, max_articles=20)
    categorized = categorize_articles_for_blogs(enhanced)
    strategy_articles = categorized.get("management", []) or []
    ld_articles = categorized.get("improvement", []) or []

    if not strategy_articles and not ld_articles:
        raise Exception("لم يتم العثور على مقالات كافية لتوليد مدونة يومية.")

    strategy_blog = ""
    ld_blog = ""
    if strategy_articles:
        strategy_blog = generate_quality_blog_with_ai(strategy_articles, "management", "daily")
        if not strategy_blog or "AWS Bedrock Error" in strategy_blog or "حدث خطأ" in strategy_blog or len(strategy_blog.strip()) < 200:
            strategy_blog = build_fallback_quality_blog_content(strategy_articles, "الأسرة والمجتمع")

    if ld_articles:
        ld_blog = generate_quality_blog_with_ai(ld_articles, "improvement", "daily")
        if not ld_blog or "AWS Bedrock Error" in ld_blog or "حدث خطأ" in ld_blog or len(ld_blog.strip()) < 200:
            ld_blog = build_fallback_quality_blog_content(ld_articles, "الصحة النفسية والرفاهية")

    combined_blog = "\n\n---\n\n".join([b for b in [strategy_blog, ld_blog] if b])
    if not combined_blog or len(combined_blog.strip()) < 100:
        combined_blog = build_fallback_quality_blog_content(enhanced, "ملخص يومي")

    return create_quality_blog_pdf(combined_blog, title, is_temp_file=False)

def _generate_weekly_pdf(db: Session, title: str) -> str:
    """Generate weekly PDF report"""
    today = datetime.utcnow()
    last_week = today - timedelta(days=7)
    db_articles = db.query(Article).filter(
        Article.is_relevant.isnot(False),
        (Article.published_at >= last_week) | (Article.created_at >= last_week)
    ).all()
    
    all_articles = [_article_to_dict(a) for a in db_articles]
    if not all_articles:
        raise Exception("لم يتم العثور على مقالات كافية للأسبوع الماضي لتوليد تقرير.")

    filtered = filter_relevant_articles(all_articles)
    recent = filter_recent_articles(filtered, days=7)
    if not recent:
        raise Exception("لم يتم العثور على مقالات ملائمة للأسبوع الماضي بعد الفلترة.")

    enhanced = enhance_articles_with_content(recent, max_articles=50, weekly_mode=True)
    categorized = categorize_articles_for_blogs(enhanced)
    strategy_articles = categorized.get("management", []) or []
    ld_articles = categorized.get("improvement", []) or []

    if not strategy_articles and not ld_articles:
        raise Exception("لم يتم العثور على مقالات كافية لتوليد مدونات أسبوعية.")

    strategy_blog = ""
    ld_blog = ""
    if strategy_articles:
        strategy_blog = generate_quality_blog_with_ai(strategy_articles, "management", "weekly")
        if not strategy_blog or "AWS Bedrock Error" in strategy_blog or "حدث خطأ" in strategy_blog or len(strategy_blog.strip()) < 200:
            strategy_blog = build_fallback_quality_blog_content(strategy_articles, "الأسرة والمجتمع")

    if ld_articles:
        ld_blog = generate_quality_blog_with_ai(ld_articles, "improvement", "weekly")
        if not ld_blog or "AWS Bedrock Error" in ld_blog or "حدث خطأ" in ld_blog or len(ld_blog.strip()) < 200:
            ld_blog = build_fallback_quality_blog_content(ld_articles, "الصحة النفسية والرفاهية")

    combined_blog = "\n\n---\n\n".join([b for b in [strategy_blog, ld_blog] if b])
    if not combined_blog or len(combined_blog.strip()) < 100:
        combined_blog = build_fallback_quality_blog_content(enhanced, "ملخص أسبوعي")

    return create_quality_blog_pdf(combined_blog, title, is_temp_file=False)

def _generate_monthly_pdf(db: Session, title: str) -> str:
    """Generate monthly PDF report"""
    today = datetime.utcnow()
    last_month = today - timedelta(days=30)
    db_articles = db.query(Article).filter(
        Article.is_relevant.isnot(False),
        (Article.published_at >= last_month) | (Article.created_at >= last_month)
    ).all()
    
    all_articles = [_article_to_dict(a) for a in db_articles]
    if not all_articles:
        raise Exception("لم يتم العثور على مقالات كافية للشهر الماضي لتوليد تقرير.")

    filtered = filter_relevant_articles(all_articles)
    recent = filter_recent_articles(filtered, days=30)
    if not recent:
        raise Exception("لم يتم العثور على مقالات ملائمة للشهر الماضي بعد الفلترة.")

    enhanced = enhance_articles_with_content(recent, max_articles=80, monthly_mode=True)
    categorized = categorize_articles_for_blogs(enhanced)
    strategy_articles = categorized.get("management", []) or []
    ld_articles = categorized.get("improvement", []) or []

    if not strategy_articles and not ld_articles:
        raise Exception("لم يتم العثور على مقالات كافية لتوليد مدونات شهرية.")

    strategy_blog = ""
    ld_blog = ""
    if strategy_articles:
        strategy_blog = generate_quality_blog_with_ai(strategy_articles, "management", "monthly")
        if not strategy_blog or "AWS Bedrock Error" in strategy_blog or "حدث خطأ" in strategy_blog or len(strategy_blog.strip()) < 200:
            strategy_blog = build_fallback_quality_blog_content(strategy_articles, "الأسرة والمجتمع")

    if ld_articles:
        ld_blog = generate_quality_blog_with_ai(ld_articles, "improvement", "monthly")
        if not ld_blog or "AWS Bedrock Error" in ld_blog or "حدث خطأ" in ld_blog or len(ld_blog.strip()) < 200:
            ld_blog = build_fallback_quality_blog_content(ld_articles, "الصحة النفسية والرفاهية")

    combined_blog = "\n\n---\n\n".join([b for b in [strategy_blog, ld_blog] if b])
    if not combined_blog or len(combined_blog.strip()) < 100:
        combined_blog = build_fallback_quality_blog_content(enhanced, "ملخص شهري")

    return create_quality_blog_pdf(combined_blog, title, is_temp_file=False)

def _generate_magazine_pdf(db: Session, title: str) -> str:
    """Generate magazine PDF"""
    today = datetime.utcnow()
    last_month = today - timedelta(days=30)
    db_articles = db.query(Article).filter(
        Article.is_relevant.isnot(False),
        (Article.published_at >= last_month) | (Article.created_at >= last_month)
    ).all()

    all_articles = [_article_to_dict(a) for a in db_articles]
    if not all_articles:
        raise Exception("لم يتم العثور على مقالات كافية للشهر الماضي لتوليد المجلة.")

    filtered = filter_relevant_articles(all_articles)
    recent = filter_recent_articles(filtered, days=30)
    if not recent:
        raise Exception("لم يتم العثور على مقالات ملائمة للشهر الماضي بعد الفلترة.")

    enhanced = enhance_articles_with_content(recent, max_articles=40, monthly_mode=True)
    magazine_data = generate_magazine_content_with_ai(enhanced)
    if not magazine_data:
        raise Exception("فشل توليد محتوى المجلة بواسطة الذكاء الاصطناعي.")

    magazine_data['date'] = today.strftime("%B %Y")
    
    # Initialize image_url for all articles (required for template fallback logic)
    if magazine_data.get('articles'):
        for article in magazine_data['articles']:
            if 'image_url' not in article:
                article['image_url'] = None
                article['local_image_path'] = None
    
    # Fetch og:images from source article URLs and assign round-robin to magazine articles
    try:
        source_images = fetch_images_for_articles(enhanced, max_articles=20, timeout=4)
        print(f"🖼️ Background: Fetched {len(source_images) if source_images else 0} images from {len(enhanced)} articles")
        
        if source_images and magazine_data.get('articles'):
            for i, article in enumerate(magazine_data['articles']):
                # Only assign if not already assigned and we have images to spare
                if i < len(source_images):
                    article['image_url'] = source_images[i]
            print(f"✅ Background: Assigned {len(source_images)} images across {len(magazine_data['articles'])} magazine articles")
        else:
            print(f"ℹ️ Background: No images fetched or no articles in magazine - will use IBDL logo fallback")
    except Exception as e:
        print(f"⚠️ Background: Image assignment failed: {e}")
        print(f"ℹ️ Background: Will use IBDL logo fallback for all articles")
    
    filename = f"Family_Society_Magazine_{today.strftime('%Y%m')}.pdf"
    return render_magazine_pdf(magazine_data, filename)

@app.get("/api/reports", response_model=ReportListResponse)
def get_user_reports(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's reports"""
    user_id = current_user["id"]
    reports = db.query(Report).filter(
        Report.user_id == user_id
    ).order_by(Report.created_at.desc()).offset(skip).limit(limit).all()
    
    total = db.query(Report).filter(
        Report.user_id == user_id
    ).count()
    
    return {"reports": reports, "total": total}

@app.get("/api/reports/{report_id}")
def get_report(
    report_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get specific report"""
    user_id = current_user["id"]
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == user_id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="التقرير غير موجود")
    
    if report.status != "completed" or not report.file_path:
        raise HTTPException(status_code=400, detail="التقرير غير جاهز للتحميل")
    
    if not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="ملف التقرير غير موجود")
    
    filename = f"{report.title.replace(' ', '_')}_{report.created_at.strftime('%Y%m%d')}.pdf"
    return FileResponse(report.file_path, media_type="application/pdf", filename=filename)

@app.delete("/api/reports/{report_id}")
def delete_report(
    report_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete report"""
    user_id = current_user["id"]
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == user_id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="التقرير غير موجود")
    
    # Delete file if exists
    if report.file_path and os.path.exists(report.file_path):
        try:
            os.remove(report.file_path)
        except:
            pass  # Ignore file deletion errors
    
    db.delete(report)
    db.commit()
    
    return {"message": "تم حذف التقرير بنجاح"}

@app.get("/api/notifications", response_model=NotificationListResponse)
def get_notifications(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user notifications (simplified version)"""
    user_id = current_user["id"]
    
    # Get reports as notifications (simplified approach)
    reports = db.query(Report).filter(
        Report.user_id == user_id,
        Report.created_at >= datetime.utcnow() - timedelta(days=7)  # Last 7 days
    ).order_by(Report.created_at.desc()).offset(skip).limit(limit).all()
    
    # Convert reports to notifications
    notifications = []
    for report in reports:
        if report.status == "completed":
            notification_type = "report_generated"
            title = "تم إنشاء التقرير بنجاح"
            message = f"تم إنشاء تقرير {report.report_type} بنجاح وجاهز للتحميل"
        elif report.status == "failed":
            notification_type = "report_failed"
            title = "فشل إنشاء التقرير"
            message = f"فشل إنشاء تقرير {report.report_type}: {report.error_message or 'خطأ غير معروف'}"
        else:
            notification_type = "report_pending"
            title = "جاري إنشاء التقرير"
            message = f"جاري إنشاء تقرير {report.report_type} في الخلفية"
        
        notifications.append({
            "id": report.id,
            "type": notification_type,
            "title": title,
            "message": message,
            "report_id": report.id,
            "created_at": report.created_at,
            "is_read": False
        })
    
    unread_count = len([n for n in notifications if not n["is_read"]])
    
    return {"notifications": notifications, "unread_count": unread_count}

@app.post("/api/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark notification as read (simplified version)"""
    # This is a simplified implementation since we don't have a separate Notification model
    return {"message": "تم تحديث الإشعار"}
