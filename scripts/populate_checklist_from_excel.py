"""
Migration script to populate the 10-item checklist from Excel files

This script reads the 10 Excel files and populates:
1. checklist_categories (10 categories)
2. checklist_items (10 items, one per category)
3. coaching_questions (coaching questions for each item)
"""
import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.checklist import ChecklistCategory, ChecklistItem, CoachingQuestion

# Excel files mapping to categories
CHECKLIST_FILES = {
    1: {
        "file": "Trigger_Event_and_Impact_Coaching_With_Mindset.xlsx",
        "name": "Trigger Event & Impact",
        "description": "Understanding what motivates the customer to act"
    },
    2: {
        "file": "Trigger_Priority_Coaching_With_Mindset.xlsx",
        "name": "Trigger Priority",
        "description": "Validating the project is a clear priority"
    },
    3: {
        "file": "Sales_Target_Coaching_With_Mindset.xlsx",
        "name": "Sales Target",
        "description": "What customer plans to buy, how much, and when"
    },
    4: {
        "file": "Decision_Influencer_Coaching_With_Mindset.xlsx",
        "name": "Decision Influencer",
        "description": "Identifying and engaging key decision makers"
    },
    5: {
        "file": "Decision_Making_Process_Coaching_With_Mindset.xlsx",
        "name": "Decision Making Process",
        "description": "Understanding how decisions are made and who is involved"
    },
    6: {
        "file": "Alternatives_Coaching_Import.xlsx",
        "name": "Alternatives",
        "description": "Identifying and neutralizing competitive alternatives"
    },
    7: {
        "file": "Fit_Coaching_With_Mindset.xlsx",
        "name": "Fit",
        "description": "Confirming the customer meets our fit criteria"
    },
    8: {
        "file": "Individual_Impact_Coaching_Final.xlsx",
        "name": "Individual Impact",
        "description": "How each decision influencer is personally impacted"
    },
    9: {
        "file": "Mentor_Coaching_With_Mindset.xlsx",
        "name": "Mentor",
        "description": "Developing someone who wants you to be successful"
    },
    10: {
        "file": "Our_Solution_Ranking_Coaching_With_Mindset.xlsx",
        "name": "Our Solution Ranking",
        "description": "How decision influencers rank our solution versus alternatives"
    }
}

EXCEL_FOLDER = "/Users/muhammadfarooq/Documents/UPWORK BUSINESS/Dave Varner/Checklist Sheets/"


def read_excel_file(file_path: str) -> dict:
    """Read Excel file and extract Definition, Key Behavior, and Coaching Questions"""
    df = pd.read_excel(file_path)

    data = {
        "definition": None,
        "key_behavior": None,
        "coaching_questions": []
    }

    for _, row in df.iterrows():
        section = str(row['Section']).strip()
        content = str(row['Content']).strip()

        if section == "Definition":
            data["definition"] = content
        elif "Key Salesperson Behavior" in section or section == "Key Salesperson Behavior":
            data["key_behavior"] = content
        elif section not in ["Definition", "Key Salesperson Behavior", "nan"]:
            # This is a coaching question
            if content and content != "nan":
                data["coaching_questions"].append({
                    "section": section,
                    "content": content
                })

    return data


def populate_database():
    """Populate database with 10 checklist items from Excel files"""

    # Create database session - use psycopg2 for sync operations
    sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    # Handle SSL parameters for psycopg2
    if "?" in sync_db_url:
        # Remove query parameters that psycopg2 doesn't support in DSN format
        base_url = sync_db_url.split("?")[0]
        # psycopg2 will use SSL automatically if needed
        sync_db_url = base_url

    engine = create_engine(sync_db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        print("🚀 Starting checklist population from Excel files...")
        print(f"📁 Excel folder: {EXCEL_FOLDER}\n")

        # Clear existing data
        print("🗑️  Clearing existing checklist data...")
        db.query(CoachingQuestion).delete()
        db.query(ChecklistItem).delete()
        db.query(ChecklistCategory).delete()
        db.commit()
        print("✅ Existing data cleared\n")

        # Process each category
        for order, info in CHECKLIST_FILES.items():
            file_name = info["file"]
            file_path = os.path.join(EXCEL_FOLDER, file_name)

            print(f"📄 Processing {order}/10: {info['name']}")
            print(f"   File: {file_name}")

            if not os.path.exists(file_path):
                print(f"   ❌ File not found: {file_path}")
                continue

            # Read Excel file
            data = read_excel_file(file_path)

            # Create Category
            category = ChecklistCategory(
                name=info["name"],
                description=info["description"],
                order=order,
                default_weight=1.0,
                max_score=10,
                is_active=True
            )
            db.add(category)
            db.flush()  # Get category ID

            print(f"   ✅ Category created (ID: {category.id})")

            # Create ChecklistItem
            item = ChecklistItem(
                category_id=category.id,
                title=info["name"],
                definition=data["definition"] or f"Checklist item for {info['name']}",
                key_behavior=data["key_behavior"],
                key_mindset=None,  # Not in current Excel structure
                order=1,  # Only 1 item per category
                weight=1.0,
                points=10.0,  # 10 points per item
                is_active=True
            )
            db.add(item)
            db.flush()  # Get item ID

            print(f"   ✅ Item created (ID: {item.id})")
            print(f"   📝 Definition: {data['definition'][:80]}...")

            # Create Coaching Questions
            question_count = 0
            for q_order, q_data in enumerate(data["coaching_questions"], start=1):
                question = CoachingQuestion(
                    item_id=item.id,
                    section=q_data["section"],
                    question=q_data["content"],
                    order=q_order,
                    is_active=True
                )
                db.add(question)
                question_count += 1

            print(f"   ✅ {question_count} coaching questions added\n")

        # Commit all changes
        db.commit()

        # Print summary
        categories_count = db.query(ChecklistCategory).count()
        items_count = db.query(ChecklistItem).count()
        questions_count = db.query(CoachingQuestion).count()

        print("\n" + "="*60)
        print("✨ CHECKLIST POPULATION COMPLETE!")
        print("="*60)
        print(f"📊 Summary:")
        print(f"   • Categories created: {categories_count}")
        print(f"   • Checklist items created: {items_count}")
        print(f"   • Coaching questions created: {questions_count}")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    populate_database()
