"""
Script to promote a user to SYSTEM_ADMIN role
Usage: python scripts/promote_to_system_admin.py <email>
"""
import sys
import asyncio
from sqlalchemy import select
from app.db.session import async_session_maker
from app.models import User


async def promote_user_to_system_admin(email: str):
    """Promote a user to SYSTEM_ADMIN role"""
    async with async_session_maker() as db:
        # Find user by email
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            print(f"❌ User with email '{email}' not found")
            return False

        # Show current status
        print(f"\n📧 User: {user.email}")
        print(f"👤 Name: {user.first_name} {user.last_name}")
        print(f"🔑 Current Role: {user.role}")
        print(f"🏢 Organization ID: {user.organization_id}")
        print(f"👥 Team ID: {user.team_id}")

        # Check if already SYSTEM_ADMIN
        if user.role == "SYSTEM_ADMIN":
            print(f"\n✅ User is already a SYSTEM_ADMIN")
            return True

        # Promote to SYSTEM_ADMIN
        user.role = "SYSTEM_ADMIN"
        await db.commit()

        print(f"\n🎉 SUCCESS! User promoted to SYSTEM_ADMIN")
        print(f"✅ New Role: {user.role}")
        return True


async def list_all_users():
    """List all users in the database"""
    async with async_session_maker() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()

        if not users:
            print("❌ No users found in database")
            return

        print(f"\n📋 Found {len(users)} user(s):\n")
        for user in users:
            print(f"  📧 {user.email}")
            print(f"     Role: {user.role}")
            print(f"     Name: {user.first_name} {user.last_name}")
            print(f"     ID: {user.id}")
            print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/promote_to_system_admin.py <email>")
        print("\nOr use: python scripts/promote_to_system_admin.py --list")
        print("\nExample: python scripts/promote_to_system_admin.py admin@test.com")
        sys.exit(1)

    if sys.argv[1] == "--list":
        asyncio.run(list_all_users())
    else:
        email = sys.argv[1]
        success = asyncio.run(promote_user_to_system_admin(email))
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
