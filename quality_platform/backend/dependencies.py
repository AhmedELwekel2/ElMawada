from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from database import get_db
from models import User, RefreshToken, UserUsage
from schemas import TokenData, UsageLimitsResponse
from auth import verify_token, get_password_hash, has_permission

security = HTTPBearer()

# Usage limits for different user roles
USAGE_LIMITS = {
    "admin": {
        "daily": 30,
        "weekly": 20,
        "monthly": 15,
        "magazine": 10,
    },
    "editor": {
        "daily": 4,
        "weekly": 4,
        "monthly": 4,
        "magazine": 2,
    },
    "viewer": {
        "daily": 4,
        "weekly": 4,
        "monthly": 4,
        "magazine": 2,
    }
}

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    payload = verify_token(token, "access")
    
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
        )
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active
    }

def get_current_active_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get current active user (redundant but explicit)."""
    return current_user

def require_permission(permission: str):
    """Dependency to check if user has required permission."""
    def permission_checker(current_user: Dict[str, Any] = Depends(get_current_active_user)):
        if not has_permission(current_user.get("role"), permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return permission_checker

def get_user_usage_limits(current_user: Dict[str, Any] = Depends(get_current_active_user), db: Session = Depends(get_db)) -> UsageLimitsResponse:
    """Get user's current usage and limits for PDF generation."""
    user_role = current_user.get("role")
    user_id = current_user.get("id")
    
    # Get current month
    current_month = datetime.utcnow().strftime("%Y-%m")
    
    # Get user's current usage for this month
    usage_records = db.query(UserUsage).filter(
        and_(
            UserUsage.user_id == user_id,
            UserUsage.month == current_month
        )
    ).all()
    
    # Initialize usage dictionary
    usage = {"daily": 0, "weekly": 0, "monthly": 0, "magazine": 0}
    
    # Sum up usage counts
    for record in usage_records:
        if record.report_type in usage:
            usage[record.report_type] += record.count
    
    # Get limits for user role
    limits = USAGE_LIMITS.get(user_role, USAGE_LIMITS["viewer"])
    
    return UsageLimitsResponse(
        daily_limit=limits["daily"],
        weekly_limit=limits["weekly"],
        monthly_limit=limits["monthly"],
        magazine_limit=limits["magazine"],
        current_month=current_month,
        usage=usage
    )

def check_pdf_generation_limit(report_type: str):
    """Dependency to check if user has reached PDF generation limit."""
    def limit_checker(
        current_user: Dict[str, Any] = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ):
        user_role = current_user.get("role")
        user_id = current_user.get("id")
        
        # Viewer role cannot generate PDFs - needs admin approval
        if user_role == "viewer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not approved to generate PDF reports yet. Please contact an administrator to upgrade your role.",
            )
        
        # Admin has unlimited access
        if user_role == "admin":
            return current_user
        
        # Get current month
        current_month = datetime.utcnow().strftime("%Y-%m")
        
        # Get or create usage record for this report type
        usage_record = db.query(UserUsage).filter(
            and_(
                UserUsage.user_id == user_id,
                UserUsage.report_type == report_type,
                UserUsage.month == current_month
            )
        ).first()
        
        if not usage_record:
            # Create new usage record
            usage_record = UserUsage(
                user_id=user_id,
                report_type=report_type,
                month=current_month,
                count=0
            )
            db.add(usage_record)
            db.commit()
            db.refresh(usage_record)
        
        # Check if limit reached
        limit = USAGE_LIMITS[user_role][report_type]
        if usage_record.count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly {report_type} PDF limit ({limit}) reached. Please try again next month."
            )
        
        return current_user
    
    return limit_checker

def increment_pdf_usage(report_type: str):
    """Dependency to increment PDF usage count after successful generation."""
    def increment_usage(
        current_user: Dict[str, Any] = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ):
        user_role = current_user.get("role")
        user_id = current_user.get("id")
        
        # Get current month
        current_month = datetime.utcnow().strftime("%Y-%m")
        
        # Get or create usage record
        usage_record = db.query(UserUsage).filter(
            and_(
                UserUsage.user_id == user_id,
                UserUsage.report_type == report_type,
                UserUsage.month == current_month
            )
        ).first()
        
        if usage_record:
            usage_record.count += 1
            db.commit()
        else:
            # Create new usage record
            new_record = UserUsage(
                user_id=user_id,
                report_type=report_type,
                month=current_month,
                count=1
            )
            db.add(new_record)
            db.commit()
    
    return increment_usage
