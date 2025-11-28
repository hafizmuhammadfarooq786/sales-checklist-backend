"""
Authentication endpoint tests - validates JWT security fixes
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.auth
class TestAuthentication:
    """Test authentication and authorization flows"""

    @pytest.mark.asyncio
    async def test_register_user(self, client):
        """Test user registration creates account and returns token"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/auth/register",
                json={
                    "email": "newuser@example.com",
                    "password": "SecurePass123!",
                    "first_name": "New",
                    "last_name": "User"
                }
            )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client, test_user):
        """Test registering with existing email fails"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/auth/register",
                json={
                    "email": test_user.email,
                    "password": "SecurePass123!",
                    "first_name": "Duplicate",
                    "last_name": "User"
                }
            )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_success(self, client, test_user):
        """Test successful login returns valid JWT token"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "Test123!@#"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client, test_user):
        """Test login with wrong password fails"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "WrongPassword123!"
                }
            )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        """Test login with non-existent email fails"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/auth/login",
                json={
                    "email": "nonexistent@example.com",
                    "password": "Password123!"
                }
            )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_current_user_authenticated(self, client, auth_headers):
        """Test authenticated user can access /me endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(
                "/api/v1/auth/me",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["first_name"] == "Test"
        assert data["role"] == "rep"

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, client):
        """
        CRITICAL SECURITY TEST: Verify no auth bypass exists
        Tests the P0-1 fix - must require authentication
        """
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/auth/me")

        assert response.status_code == 401
        assert "authorization" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client):
        """Test invalid JWT token is rejected"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer invalid_token_here"}
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_malformed_token(self, client):
        """Test malformed token format is rejected"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(
                "/api/v1/auth/me",
                headers={"Authorization": "InvalidFormat"}
            )

        assert response.status_code == 401


@pytest.mark.auth
class TestPasswordReset:
    """Test password reset flow"""

    @pytest.mark.asyncio
    async def test_forgot_password_existing_user(self, client, test_user):
        """Test password reset request for existing user"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/auth/forgot-password",
                json={"email": test_user.email}
            )

        # Should always return 200 to prevent email enumeration
        assert response.status_code == 200
        assert "link has been sent" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_user(self, client):
        """Test password reset for non-existent user (anti-enumeration)"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/auth/forgot-password",
                json={"email": "nonexistent@example.com"}
            )

        # Should return same response to prevent email enumeration
        assert response.status_code == 200
        assert "link has been sent" in response.json()["message"].lower()


@pytest.mark.auth
class TestPasswordChange:
    """Test password change functionality for authenticated users"""

    @pytest.mark.asyncio
    async def test_change_password_success(self, client, auth_headers):
        """Test successful password change with correct current password"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/auth/change-password",
                headers=auth_headers,
                json={
                    "current_password": "Test123!@#",
                    "new_password": "NewSecurePass123!"
                }
            )

        assert response.status_code == 200
        assert "successfully" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, client, auth_headers):
        """Test password change fails with incorrect current password"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/auth/change-password",
                headers=auth_headers,
                json={
                    "current_password": "WrongPassword123!",
                    "new_password": "NewSecurePass123!"
                }
            )

        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_change_password_same_password(self, client, auth_headers):
        """Test password change rejects same password as new password"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/auth/change-password",
                headers=auth_headers,
                json={
                    "current_password": "Test123!@#",
                    "new_password": "Test123!@#"
                }
            )

        assert response.status_code == 400
        assert "different" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_change_password_unauthenticated(self, client):
        """
        SECURITY TEST: Verify password change requires authentication
        """
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "Test123!@#",
                    "new_password": "NewSecurePass123!"
                }
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_change_password_too_short(self, client, auth_headers):
        """Test password change rejects password shorter than 8 characters"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/auth/change-password",
                headers=auth_headers,
                json={
                    "current_password": "Test123!@#",
                    "new_password": "Short1!"
                }
            )

        # Pydantic validation should reject this
        assert response.status_code == 422
