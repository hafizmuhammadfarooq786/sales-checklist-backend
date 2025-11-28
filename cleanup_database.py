"""
Database cleanup script - Remove test/demo data
Keeps only real admin user and essential checklist data
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Define what to keep
KEEP_EMAIL = "hafizmuhammadfarooq712@gmail.com"  # Real admin user

async def cleanup_database():
    """Clean up test/demo data from the database"""
    from sqlalchemy import text
    from app.db.session import get_db_session

    print("=" * 60)
    print("   DATABASE CLEANUP")
    print("=" * 60)
    print(f"\n⚠️  This will DELETE all test data!")
    print(f"   Keeping only user: {KEEP_EMAIL}")
    print("\n" + "-" * 60)

    async with get_db_session() as db:
        # Get user ID to keep
        result = await db.execute(text(
            f"SELECT id, email FROM users WHERE email = '{KEEP_EMAIL}'"
        ))
        keep_user = result.fetchone()

        if keep_user:
            keep_user_id = keep_user[0]
            print(f"\n✅ User to KEEP: {keep_user[1]} (ID: {keep_user_id})")
        else:
            print(f"\n⚠️  Admin user not found: {KEEP_EMAIL}")
            keep_user_id = None

        # Get users to delete
        result = await db.execute(text(
            f"SELECT id, email FROM users WHERE email != '{KEEP_EMAIL}'"
        ))
        delete_users = result.fetchall()
        delete_user_ids = [u[0] for u in delete_users]

        print(f"\n❌ Users to DELETE: {len(delete_users)}")
        for u in delete_users:
            print(f"   - {u[1]} (ID: {u[0]})")

        if delete_user_ids:
            # Get all sessions to delete (from test users)
            ids_str = ','.join(str(id) for id in delete_user_ids)
            result = await db.execute(text(
                f"SELECT id FROM sessions WHERE user_id IN ({ids_str})"
            ))
            session_ids = [r[0] for r in result.fetchall()]
            print(f"\n📋 Sessions from test users to delete: {session_ids}")

            if session_ids:
                session_ids_str = ','.join(str(id) for id in session_ids)

                # Delete in order (respecting foreign keys)
                await db.execute(text(f"DELETE FROM reports WHERE session_id IN ({session_ids_str})"))
                print("   ✓ Deleted reports")

                await db.execute(text(f"DELETE FROM coaching_feedback WHERE session_id IN ({session_ids_str})"))
                print("   ✓ Deleted coaching_feedback")

                await db.execute(text(f"DELETE FROM scoring_results WHERE session_id IN ({session_ids_str})"))
                print("   ✓ Deleted scoring_results")

                await db.execute(text(f"DELETE FROM session_responses WHERE session_id IN ({session_ids_str})"))
                print("   ✓ Deleted session_responses")

                await db.execute(text(f"DELETE FROM transcripts WHERE session_id IN ({session_ids_str})"))
                print("   ✓ Deleted transcripts")

                await db.execute(text(f"DELETE FROM audio_files WHERE session_id IN ({session_ids_str})"))
                print("   ✓ Deleted audio_files")

                await db.execute(text(f"DELETE FROM salesforce_sync WHERE session_id IN ({session_ids_str})"))
                print("   ✓ Deleted salesforce_sync")

                await db.execute(text(f"DELETE FROM sessions WHERE id IN ({session_ids_str})"))
                print("   ✓ Deleted sessions")

            # Delete audit logs for test users
            await db.execute(text(f"DELETE FROM audit_logs WHERE user_id IN ({ids_str})"))
            print("   ✓ Deleted audit_logs")

            # Delete test users
            await db.execute(text(f"DELETE FROM users WHERE id IN ({ids_str})"))
            print("   ✓ Deleted test users")

        # Also clean up admin's test sessions
        if keep_user_id:
            result = await db.execute(text(
                f"SELECT id, customer_name FROM sessions WHERE user_id = {keep_user_id}"
            ))
            admin_sessions = result.fetchall()

            if admin_sessions:
                print(f"\n⚠️  Admin has {len(admin_sessions)} test sessions:")
                for s in admin_sessions:
                    print(f"   - Session {s[0]}: {s[1]}")

                admin_session_ids = [s[0] for s in admin_sessions]
                admin_ids_str = ','.join(str(id) for id in admin_session_ids)

                await db.execute(text(f"DELETE FROM reports WHERE session_id IN ({admin_ids_str})"))
                await db.execute(text(f"DELETE FROM coaching_feedback WHERE session_id IN ({admin_ids_str})"))
                await db.execute(text(f"DELETE FROM scoring_results WHERE session_id IN ({admin_ids_str})"))
                await db.execute(text(f"DELETE FROM session_responses WHERE session_id IN ({admin_ids_str})"))
                await db.execute(text(f"DELETE FROM transcripts WHERE session_id IN ({admin_ids_str})"))
                await db.execute(text(f"DELETE FROM audio_files WHERE session_id IN ({admin_ids_str})"))
                await db.execute(text(f"DELETE FROM salesforce_sync WHERE session_id IN ({admin_ids_str})"))
                await db.execute(text(f"DELETE FROM sessions WHERE id IN ({admin_ids_str})"))
                print("   ✓ Deleted admin's test sessions")

        # Commit all changes
        await db.commit()
        print("\n✅ Database cleanup complete!")

        # Verify
        print("\n" + "=" * 60)
        print("   POST-CLEANUP VERIFICATION")
        print("=" * 60)

        result = await db.execute(text("SELECT COUNT(*) FROM users"))
        print(f"\n  Users remaining: {result.scalar()}")

        result = await db.execute(text("SELECT COUNT(*) FROM sessions"))
        print(f"  Sessions remaining: {result.scalar()}")

        result = await db.execute(text("SELECT COUNT(*) FROM audio_files"))
        print(f"  Audio files remaining: {result.scalar()}")

        result = await db.execute(text("SELECT COUNT(*) FROM transcripts"))
        print(f"  Transcripts remaining: {result.scalar()}")

        result = await db.execute(text("SELECT COUNT(*) FROM session_responses"))
        print(f"  Session responses remaining: {result.scalar()}")

        result = await db.execute(text("SELECT COUNT(*) FROM checklist_categories"))
        print(f"  Categories: {result.scalar()}")

        result = await db.execute(text("SELECT COUNT(*) FROM checklist_items"))
        print(f"  Checklist items: {result.scalar()}")

        result = await db.execute(text("SELECT id, email, role FROM users"))
        users = result.fetchall()
        print("\n  Remaining Users:")
        for u in users:
            print(f"    - ID {u[0]}: {u[1]} ({u[2]})")

        print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(cleanup_database())
