"""
Authentication service for JWT token generation and password management
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, Token, UserResponse


class AuthService:
    """Authentication service for JWT and password management"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.algorithm = settings.ALGORITHM
        self.secret_key = settings.SECRET_KEY
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def decode_access_token(self, token: str) -> Optional[dict]:
        """Decode and validate a JWT access token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
    
    def generate_reset_token(self) -> str:
        """Generate a secure password reset token"""
        return secrets.token_urlsafe(32)
    
    def generate_verification_token(self) -> str:
        """Generate a secure email verification token"""
        return secrets.token_urlsafe(32)
    
    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password"""
        result = await db.execute(
            select(User).where(
                and_(
                    User.email == email,
                    User.is_active == True
                )
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            return None
        
        # Verify password
        if not self.verify_password(password, user.password_hash):
            # Increment failed attempts
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            
            # Lock account after 5 failed attempts for 30 minutes
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            
            await db.commit()
            return None
        
        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        await db.commit()
        
        return user
    
    async def create_user(self, db: AsyncSession, user_data: UserCreate) -> User:
        """Create a new user with hashed password"""
        hashed_password = self.hash_password(user_data.password)
        
        user = User(
            email=user_data.email,
            password_hash=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role,
            is_active=True,
            is_verified=False,  # Require email verification
            email_verification_token=self.generate_verification_token(),
            email_verification_expires=datetime.utcnow() + timedelta(hours=24)
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    async def create_token_response(self, user: User) -> Token:
        """Create a complete token response with user data"""
        access_token = self.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        
        user_response = UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            organization_id=user.organization_id,
            team_id=user.team_id,
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login=user.last_login,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=self.access_token_expire_minutes * 60,
            user=user_response
        )
    
    async def verify_email(self, db: AsyncSession, token: str) -> Optional[User]:
        """Verify email with token and return the user"""
        result = await db.execute(
            select(User).where(
                and_(
                    User.email_verification_token == token,
                    User.email_verification_expires > datetime.utcnow()
                )
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        user.is_verified = True
        user.email_verification_token = None
        user.email_verification_expires = None
        await db.commit()
        await db.refresh(user)
        return user
    
    async def generate_email_verification_token(self, db: AsyncSession, user: User) -> Optional[User]:
        """Generate new email verification token for user"""
        if user.is_verified:
            return None
        
        user.email_verification_token = self.generate_verification_token()
        user.email_verification_expires = datetime.utcnow() + timedelta(hours=24)
        await db.commit()
        await db.refresh(user)
        return user
    
    async def request_password_reset(self, db: AsyncSession, email: str) -> Optional[User]:
        """Request password reset for user"""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        user.password_reset_token = self.generate_reset_token()
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        await db.commit()
        return user
    
    async def reset_password(self, db: AsyncSession, token: str, new_password: str) -> bool:
        """Reset password with token"""
        result = await db.execute(
            select(User).where(
                and_(
                    User.password_reset_token == token,
                    User.password_reset_expires > datetime.utcnow()
                )
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            return False

        user.password_hash = self.hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        user.failed_login_attempts = 0  # Reset failed attempts
        user.locked_until = None  # Unlock account
        await db.commit()
        return True

    async def change_password(self, db: AsyncSession, user: User, current_password: str, new_password: str) -> bool:
        """
        Change password for authenticated user
        Requires current password verification for security
        """
        # Verify current password
        if not self.verify_password(current_password, user.password_hash):
            return False

        # Hash and update to new password
        user.password_hash = self.hash_password(new_password)
        user.failed_login_attempts = 0  # Reset any failed attempts
        user.locked_until = None  # Unlock account if locked
        await db.commit()
        return True


# Global auth service instance
auth_service = AuthService()