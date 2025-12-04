"""
Audit logs and system settings
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


