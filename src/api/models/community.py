"""
SQLAlchemy ORM models for MySQL community features.

Tables: users, comments, votes
See ai-dev/field-schema.md for schema definitions.
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class MySQLBase(DeclarativeBase):
    """Declarative base for MySQL models."""
    pass


class User(MySQLBase):
    """Community user account."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True)
    created_at = Column(DateTime, server_default=func.now())

    comments = relationship("Comment", back_populates="user", lazy="selectin")
    votes = relationship("Vote", back_populates="user", lazy="selectin")

    def to_dict(self) -> dict:
        """Serialize user to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Comment(MySQLBase):
    """Comment on a sighting (cross-references PostgreSQL sighting UUID)."""

    __tablename__ = "comments"
    __table_args__ = (
        Index("idx_comments_sighting", "sighting_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    sighting_id = Column(String(36), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="comments", lazy="selectin")

    def to_dict(self) -> dict:
        """Serialize comment to dictionary."""
        return {
            "id": self.id,
            "sighting_id": self.sighting_id,
            "user_id": self.user_id,
            "username": self.user.display_name if self.user else None,
            "body": self.body,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Vote(MySQLBase):
    """Credibility vote on a sighting."""

    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("sighting_id", "user_id", name="uq_vote_sighting_user"),
        Index("idx_votes_sighting", "sighting_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    sighting_id = Column(String(36), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    value = Column(SmallInteger, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="votes", lazy="selectin")
