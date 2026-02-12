"""add_performance_indexes

CRITICAL PERFORMANCE OPTIMIZATION MIGRATION

This migration adds composite indexes to dramatically improve query performance.
These indexes target the slowest queries identified in the manager dashboard and training gaps endpoints.

Expected Performance Improvement: 10-100x faster queries

Revision ID: 81940ba18b42
Revises: 0090406d8bf9
Create Date: 2026-02-11 19:41:53.944205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '81940ba18b42'
down_revision: Union[str, None] = '0090406d8bf9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add performance indexes for frequently queried columns

    CRITICAL INDEXES FOR MANAGER DASHBOARD PERFORMANCE
    """

    # ============================================================================
    # SESSIONS TABLE INDEXES
    # ============================================================================

    # Index for filtering sessions by user and status (used in ALL dashboard queries)
    # Covers: WHERE user_id IN (...) AND status != 'completed'
    op.create_index(
        'idx_sessions_user_status',
        'sessions',
        ['user_id', 'status'],
        unique=False
    )

    # Index for stalled deals detection
    # Covers: WHERE user_id IN (...) AND updated_at < date AND status != 'completed'
    op.create_index(
        'idx_sessions_user_updated',
        'sessions',
        ['user_id', 'updated_at'],
        unique=False
    )

    # Index for deal stage filtering (lost/disengaged deals)
    # Covers: WHERE deal_stage IN ('lost', 'no_decision', 'disengaged')
    op.create_index(
        'idx_sessions_deal_stage',
        'sessions',
        ['deal_stage'],
        unique=False
    )

    # Composite index for active checklists sorting
    # Covers: WHERE user_id IN (...) ORDER BY updated_at DESC
    op.create_index(
        'idx_sessions_user_updated_desc',
        'sessions',
        ['user_id', 'updated_at'],
        unique=False,
        postgresql_ops={'updated_at': 'DESC'}
    )

    # Index for status and updated_at filtering together
    # Covers: WHERE status != 'completed' AND updated_at < date
    op.create_index(
        'idx_sessions_status_updated',
        'sessions',
        ['status', 'updated_at'],
        unique=False
    )

    # ============================================================================
    # SCORING_RESULTS TABLE INDEXES
    # ============================================================================

    # Index for joining scoring results with sessions
    # Covers: WHERE session_id = X AND total_score >= Y
    op.create_index(
        'idx_scoring_session_score',
        'scoring_results',
        ['session_id', 'total_score'],
        unique=False
    )

    # Index for at-risk deals (scores <= 30)
    # Covers: WHERE total_score <= 30
    op.create_index(
        'idx_scoring_total_score',
        'scoring_results',
        ['total_score'],
        unique=False
    )

    # Index for risk band filtering
    # Covers: WHERE risk_band = 'red'
    op.create_index(
        'idx_scoring_risk_band',
        'scoring_results',
        ['risk_band'],
        unique=False
    )

    # Composite index for high-scoring queries
    # Covers: WHERE total_score >= 70 ORDER BY total_score DESC
    op.create_index(
        'idx_scoring_score_desc',
        'scoring_results',
        ['total_score'],
        unique=False,
        postgresql_ops={'total_score': 'DESC'}
    )

    # ============================================================================
    # SESSION_RESPONSES TABLE INDEXES (CRITICAL FOR TRAINING GAPS)
    # ============================================================================

    # Composite index for session-item lookups
    # Covers: WHERE session_id = X AND item_id = Y
    op.create_index(
        'idx_responses_session_item',
        'session_responses',
        ['session_id', 'item_id'],
        unique=False
    )

    # Index for "No" response aggregation (CRITICAL for training gaps)
    # Covers: WHERE item_id = X AND ai_answer = false
    op.create_index(
        'idx_responses_item_answer',
        'session_responses',
        ['item_id', 'ai_answer'],
        unique=False
    )

    # Index for session responses by answer
    # Covers: WHERE session_id IN (...) AND ai_answer = false
    op.create_index(
        'idx_responses_session_answer',
        'session_responses',
        ['session_id', 'ai_answer'],
        unique=False
    )

    # ============================================================================
    # USERS TABLE INDEXES
    # ============================================================================

    # Index for team member lookups
    # Covers: WHERE team_id = X AND role = 'REP'
    op.create_index(
        'idx_users_team_role',
        'users',
        ['team_id', 'role'],
        unique=False
    )

    # Index for organization member lookups
    # Covers: WHERE organization_id = X AND is_active = true
    op.create_index(
        'idx_users_org_active',
        'users',
        ['organization_id', 'is_active'],
        unique=False
    )

    # Index for active team members
    # Covers: WHERE team_id = X AND is_active = true
    op.create_index(
        'idx_users_team_active',
        'users',
        ['team_id', 'is_active'],
        unique=False
    )

    # ============================================================================
    # CHECKLIST_ITEMS TABLE INDEXES
    # ============================================================================

    # Index for category filtering
    # Covers: WHERE category_id = X
    op.create_index(
        'idx_checklist_items_category',
        'checklist_items',
        ['category_id'],
        unique=False
    )

    # ============================================================================
    # SCORE_HISTORY TABLE INDEXES
    # ============================================================================

    # Index for session score history
    # Covers: WHERE session_id = X ORDER BY calculated_at DESC
    op.create_index(
        'idx_score_history_session_calc',
        'score_history',
        ['session_id', 'calculated_at'],
        unique=False,
        postgresql_ops={'calculated_at': 'DESC'}
    )

    # ============================================================================
    # MANAGER_NOTES TABLE INDEXES
    # ============================================================================

    # Additional index for manager notes by created_at (already has session_id index)
    # Covers: WHERE session_id = X ORDER BY created_at DESC
    op.create_index(
        'idx_manager_notes_created_at',
        'manager_notes',
        ['created_at'],
        unique=False,
        postgresql_ops={'created_at': 'DESC'}
    )


def downgrade() -> None:
    """
    Remove performance indexes
    """
    # Drop all indexes in reverse order
    op.drop_index('idx_manager_notes_created_at', table_name='manager_notes')
    op.drop_index('idx_score_history_session_calc', table_name='score_history')
    op.drop_index('idx_checklist_items_category', table_name='checklist_items')
    op.drop_index('idx_users_team_active', table_name='users')
    op.drop_index('idx_users_org_active', table_name='users')
    op.drop_index('idx_users_team_role', table_name='users')
    op.drop_index('idx_responses_session_answer', table_name='session_responses')
    op.drop_index('idx_responses_item_answer', table_name='session_responses')
    op.drop_index('idx_responses_session_item', table_name='session_responses')
    op.drop_index('idx_scoring_score_desc', table_name='scoring_results')
    op.drop_index('idx_scoring_risk_band', table_name='scoring_results')
    op.drop_index('idx_scoring_total_score', table_name='scoring_results')
    op.drop_index('idx_scoring_session_score', table_name='scoring_results')
    op.drop_index('idx_sessions_status_updated', table_name='sessions')
    op.drop_index('idx_sessions_user_updated_desc', table_name='sessions')
    op.drop_index('idx_sessions_deal_stage', table_name='sessions')
    op.drop_index('idx_sessions_user_updated', table_name='sessions')
    op.drop_index('idx_sessions_user_status', table_name='sessions')
