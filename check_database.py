"""
Database inspection script - Check all data in the database
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

async def check_database():
    """Check all data in the database"""
    from sqlalchemy import text
    from app.db.session import get_db_session

    print("=" * 60)
    print("   DATABASE INSPECTION REPORT")
    print("=" * 60)

    async with get_db_session() as db:
        # Check Users
        print("\n📋 USERS:")
        print("-" * 40)
        result = await db.execute(text("SELECT id, email, role, is_active, is_verified, created_at FROM users ORDER BY id"))
        users = result.fetchall()
        if users:
            for u in users:
                print(f"  ID: {u[0]} | Email: {u[1]} | Role: {u[2]} | Active: {u[3]} | Verified: {u[4]} | Created: {u[5]}")
        else:
            print("  (No users found)")

        # Check Sessions
        print("\n📋 SESSIONS:")
        print("-" * 40)
        result = await db.execute(text("SELECT id, user_id, customer_name, opportunity_name, status, created_at FROM sessions ORDER BY id"))
        sessions = result.fetchall()
        if sessions:
            for s in sessions:
                print(f"  ID: {s[0]} | User: {s[1]} | Customer: {s[2]} | Opportunity: {s[3]} | Status: {s[4]}")
        else:
            print("  (No sessions found)")

        # Check Audio Files
        print("\n📋 AUDIO_FILES:")
        print("-" * 40)
        result = await db.execute(text("SELECT id, session_id, filename, file_size, duration_seconds FROM audio_files ORDER BY id"))
        audio_files = result.fetchall()
        if audio_files:
            for a in audio_files:
                print(f"  ID: {a[0]} | Session: {a[1]} | File: {a[2]} | Size: {a[3]} | Duration: {a[4]}s")
        else:
            print("  (No audio files found)")

        # Check Transcripts
        print("\n📋 TRANSCRIPTS:")
        print("-" * 40)
        result = await db.execute(text("SELECT id, session_id, language, word_count, created_at FROM transcripts ORDER BY id"))
        transcripts = result.fetchall()
        if transcripts:
            for t in transcripts:
                print(f"  ID: {t[0]} | Session: {t[1]} | Language: {t[2]} | Words: {t[3]}")
        else:
            print("  (No transcripts found)")

        # Check Session Responses count
        print("\n📋 SESSION_RESPONSES:")
        print("-" * 40)
        result = await db.execute(text("SELECT COUNT(*) FROM session_responses"))
        response_count = result.scalar()
        print(f"  Total responses: {response_count}")

        # Check Scoring Results
        print("\n📋 SCORING_RESULTS:")
        print("-" * 40)
        result = await db.execute(text("SELECT id, session_id, total_score, risk_band, items_validated, items_total FROM scoring_results ORDER BY id"))
        scores = result.fetchall()
        if scores:
            for s in scores:
                print(f"  ID: {s[0]} | Session: {s[1]} | Score: {s[2]} | Risk: {s[3]} | Items: {s[4]}/{s[5]}")
        else:
            print("  (No scoring results found)")

        # Check Coaching Feedback
        print("\n📋 COACHING_FEEDBACK:")
        print("-" * 40)
        result = await db.execute(text("SELECT id, session_id, audio_duration, generated_at FROM coaching_feedback ORDER BY id"))
        coaching = result.fetchall()
        if coaching:
            for c in coaching:
                print(f"  ID: {c[0]} | Session: {c[1]} | Audio Duration: {c[2]}s | Generated: {c[3]}")
        else:
            print("  (No coaching feedback found)")

        # Check Reports
        print("\n📋 REPORTS:")
        print("-" * 40)
        result = await db.execute(text("SELECT id, session_id, pdf_file_size, is_generated, generated_at FROM reports ORDER BY id"))
        reports = result.fetchall()
        if reports:
            for r in reports:
                print(f"  ID: {r[0]} | Session: {r[1]} | Size: {r[2]} bytes | Generated: {r[3]} | At: {r[4]}")
        else:
            print("  (No reports found)")

        # Check Categories
        print("\n📋 CHECKLIST_CATEGORIES:")
        print("-" * 40)
        result = await db.execute(text("SELECT id, name, \"order\", is_active FROM checklist_categories ORDER BY \"order\""))
        categories = result.fetchall()
        if categories:
            for c in categories:
                print(f"  ID: {c[0]} | Name: {c[1]} | Order: {c[2]} | Active: {c[3]}")
        else:
            print("  (No categories found)")

        # Checklist Items count
        print("\n📋 CHECKLIST_ITEMS:")
        print("-" * 40)
        result = await db.execute(text("SELECT COUNT(*) FROM checklist_items"))
        item_count = result.scalar()
        print(f"  Total checklist items: {item_count}")

        # Organizations
        print("\n📋 ORGANIZATIONS:")
        print("-" * 40)
        result = await db.execute(text("SELECT id, name, domain, is_active FROM organizations ORDER BY id"))
        orgs = result.fetchall()
        if orgs:
            for o in orgs:
                print(f"  ID: {o[0]} | Name: {o[1]} | Domain: {o[2]} | Active: {o[3]}")
        else:
            print("  (No organizations found)")

        # Audit Logs
        print("\n📋 AUDIT_LOGS:")
        print("-" * 40)
        result = await db.execute(text("SELECT COUNT(*) FROM audit_logs"))
        audit_count = result.scalar()
        print(f"  Total audit logs: {audit_count}")

        # Summary
        print("\n" + "=" * 60)
        print("   SUMMARY")
        print("=" * 60)
        print(f"  Users: {len(users)}")
        print(f"  Sessions: {len(sessions)}")
        print(f"  Audio Files: {len(audio_files)}")
        print(f"  Transcripts: {len(transcripts)}")
        print(f"  Session Responses: {response_count}")
        print(f"  Scoring Results: {len(scores)}")
        print(f"  Coaching Feedback: {len(coaching)}")
        print(f"  Reports: {len(reports)}")
        print(f"  Categories: {len(categories)}")
        print(f"  Checklist Items: {item_count}")
        print(f"  Organizations: {len(orgs)}")
        print(f"  Audit Logs: {audit_count}")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(check_database())
