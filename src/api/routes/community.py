"""
Community feature routes — users, comments, votes (MySQL-backed).

These demonstrate the MySQL Aiven service for transactional community data.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.community import User, Comment, Vote
from src.api.models.database import get_mysql_db
from src.api.models.schemas import CommentCreate, VoteCreate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/community", tags=["community"])


# --- Users ---

@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_mysql_db)):
    """List community users."""
    result = await db.execute(select(User).order_by(User.created_at.desc()).limit(50))
    users = result.scalars().all()
    return [u.to_dict() for u in users]


@router.post("/users", status_code=201)
async def create_user(
    username: str,
    display_name: str,
    email: str | None = None,
    db: AsyncSession = Depends(get_mysql_db),
):
    """Register a new community user."""
    user = User(username=username, display_name=display_name, email=email)
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
        return user.to_dict()
    except Exception:
        await db.rollback()
        logger.exception("Failed to create user %s", username)
        raise HTTPException(409, "Username or email already exists")


# --- Comments ---

@router.get("/sightings/{sighting_id}/comments")
async def get_comments(sighting_id: str, db: AsyncSession = Depends(get_mysql_db)):
    """Get comments for a sighting."""
    result = await db.execute(
        select(Comment)
        .where(Comment.sighting_id == sighting_id)
        .order_by(Comment.created_at.desc())
    )
    comments = result.scalars().all()
    return [c.to_dict() for c in comments]


@router.post("/comments", status_code=201)
async def create_comment(body: CommentCreate, db: AsyncSession = Depends(get_mysql_db)):
    """Add a comment to a sighting."""
    comment = Comment(
        sighting_id=body.sighting_id,
        user_id=body.user_id,
        body=body.body,
    )
    db.add(comment)
    try:
        await db.commit()
        await db.refresh(comment)
        return comment.to_dict()
    except Exception:
        await db.rollback()
        logger.exception("Failed to create comment")
        raise HTTPException(400, "Failed to create comment")


# --- Votes ---

@router.get("/sightings/{sighting_id}/votes")
async def get_votes(sighting_id: str, db: AsyncSession = Depends(get_mysql_db)):
    """Get vote tally for a sighting."""
    result = await db.execute(
        select(func.sum(Vote.value)).where(Vote.sighting_id == sighting_id)
    )
    total = result.scalar() or 0
    return {"sighting_id": sighting_id, "score": total}


@router.post("/votes", status_code=201)
async def cast_vote(body: VoteCreate, db: AsyncSession = Depends(get_mysql_db)):
    """Cast a credibility vote on a sighting."""
    vote = Vote(
        sighting_id=body.sighting_id,
        user_id=body.user_id,
        value=body.value,
    )
    db.add(vote)
    try:
        await db.commit()
        return {"status": "voted", "value": body.value}
    except Exception:
        await db.rollback()
        logger.exception("Failed to cast vote")
        raise HTTPException(409, "Already voted on this sighting")
