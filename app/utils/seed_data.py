"""
Seed database with client's checklist data (92 items from 10 Excel files)

Usage:
    python -m app.utils.seed_data
"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import (
    ChecklistCategory,
    ChecklistItem,
    CoachingQuestion,
    Organization,
)


# Checklist categories mapping (10 categories, 92 total items)
CHECKLIST_CATEGORIES = [
    {
        "name": "Trigger Event & Impact",
        "description": "Why the customer is buying and measurable results expected",
        "order": 1,
        "item_count": 10,
        "file": "Trigger_Event_and_Impact_Coaching_With_Mindset.xlsx",
    },
    {
        "name": "Trigger Priority",
        "description": "Is this truly a priority for decision influencers?",
        "order": 2,
        "item_count": 8,
        "file": "Trigger_Priority_Coaching_With_Mindset.xlsx",
    },
    {
        "name": "Sales Target",
        "description": "What, how much, when they plan to buy",
        "order": 3,
        "item_count": 8,
        "file": "Sales_Target_Coaching_With_Mindset.xlsx",
    },
    {
        "name": "Decision Influencer",
        "description": "Who influences the purchase decision and their priorities",
        "order": 4,
        "item_count": 7,
        "file": "Decision_Influencer_Coaching_With_Mindset.xlsx",
    },
    {
        "name": "Individual Impact",
        "description": "Impact of solution on decision influencers individually",
        "order": 5,
        "item_count": 8,
        "file": "Individual_Impact_Coaching_Final.xlsx",
    },
    {
        "name": "Mentor",
        "description": "Internal champion or coach for the deal",
        "order": 6,
        "item_count": 12,
        "file": "Mentor_Coaching_With_Mindset.xlsx",
    },
    {
        "name": "Decision Making Process",
        "description": "How the organization makes buying decisions",
        "order": 7,
        "item_count": 12,
        "file": "Decision_Making_Process_Coaching_With_Mindset.xlsx",
    },
    {
        "name": "Fit",
        "description": "How well solution fits customer's requirements",
        "order": 8,
        "item_count": 10,
        "file": "Fit_Coaching_With_Mindset.xlsx",
    },
    {
        "name": "Alternatives",
        "description": "Competitive alternatives being considered",
        "order": 9,
        "item_count": 8,
        "file": "Alternatives_Coaching_Import.xlsx",
    },
    {
        "name": "Our Solution Ranking",
        "description": "How we rank vs. competitors",
        "order": 10,
        "item_count": 9,
        "file": "Our_Solution_Ranking_Coaching_With_Mindset.xlsx",
    },
]


# Sample checklist items (will be expanded from actual Excel files)
# For now, creating placeholder structure
SAMPLE_ITEMS = {
    "Trigger Event & Impact": [
        {
            "title": "Trigger Event Identified",
            "definition": "What specific event or change triggered this buying cycle?",
            "key_behavior": "Actively listens and probes to uncover the root cause of change",
            "key_mindset": "Every purchase has a trigger - find it to understand urgency",
            "order": 1,
        },
        # Add more items from Excel files...
    ],
}


async def seed_categories(db: AsyncSession) -> dict[str, ChecklistCategory]:
    """Create checklist categories"""
    print("\\n🌱 Seeding checklist categories...")

    categories = {}
    for cat_data in CHECKLIST_CATEGORIES:
        # Check if category exists
        result = await db.execute(
            select(ChecklistCategory).where(ChecklistCategory.name == cat_data["name"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  ⏭️  Category '{cat_data['name']}' already exists")
            categories[cat_data["name"]] = existing
        else:
            category = ChecklistCategory(
                name=cat_data["name"],
                description=cat_data["description"],
                order=cat_data["order"],
                default_weight=1.0,
                max_score=10,
            )
            db.add(category)
            await db.flush()  # Get ID without committing
            categories[cat_data["name"]] = category
            print(f"  ✅ Created category: {cat_data['name']}")

    await db.commit()
    print(f"✅ Created {len(CHECKLIST_CATEGORIES)} categories")

    return categories


async def seed_default_organization(db: AsyncSession) -> Organization:
    """
    DEPRECATED: No longer creates a default organization.
    Organizations should be created dynamically during user registration.

    This function is kept for backward compatibility but does nothing.
    """
    print("\\n⏭️  Skipping default organization (created on-demand during registration)")
    return None


async def seed_sample_items(db: AsyncSession, categories: dict):
    """
    Seed sample checklist items for development.
    TODO: Expand this to parse all 10 Excel files and import all 92 items.
    """
    print("\\n🌱 Seeding sample checklist items...")
    print("⚠️  NOTE: This is a sample. Full import script will parse 10 Excel files.")

    # For now, just create a few sample items
    sample_category = categories.get("Trigger Event & Impact")
    if not sample_category:
        print("❌ Category not found")
        return

    # Check if items already exist
    result = await db.execute(
        select(ChecklistItem).where(ChecklistItem.category_id == sample_category.id)
    )
    existing_items = result.scalars().all()

    if existing_items:
        print(f"  ⏭️  {len(existing_items)} items already exist in this category")
        return

    # Create sample item
    sample_item = ChecklistItem(
        category_id=sample_category.id,
        title="Trigger Event Identified",
        definition="What specific event or change triggered this buying cycle?",
        key_behavior="Actively listens and probes to uncover the root cause of change",
        key_mindset="Every purchase has a trigger - find it to understand urgency",
        order=1,
        weight=1.0,
        points=1.087,
    )
    db.add(sample_item)
    await db.flush()

    # Add sample coaching question
    sample_question = CoachingQuestion(
        item_id=sample_item.id,
        section="Discovery Questions",
        question="What event or change prompted you to start looking for a solution now?",
        order=1,
    )
    db.add(sample_question)

    await db.commit()
    print("✅ Created 1 sample checklist item (92 total items to be imported)")


async def main():
    """Main seed function"""
    print("\\n" + "=" * 60)
    print("🌱 SEEDING DATABASE: The Sales Checklist™")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        try:
            # Seed in order
            await seed_default_organization(db)
            categories = await seed_categories(db)
            await seed_sample_items(db, categories)

            print("\\n" + "=" * 60)
            print("✅ DATABASE SEEDING COMPLETED!")
            print("=" * 60)
            print("\\n📊 Summary:")
            print(f"  • 10 Checklist Categories created")
            print(f"  • Sample items created")
            print("\\n⚠️  TODO: Parse 10 Excel files to import all 92 checklist items")
            print("\\n")

        except Exception as e:
            print(f"\\n❌ ERROR: {e}")
            await db.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
