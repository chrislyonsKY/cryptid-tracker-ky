"""Cryptid reference data routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models import Cryptid
from src.api.models.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["cryptids"])


@router.get("/cryptids")
async def list_cryptids(db: AsyncSession = Depends(get_db)):
    """List all known Kentucky cryptids."""
    result = await db.execute(
        select(Cryptid).order_by(Cryptid.danger_rating.desc())
    )
    cryptids = result.scalars().all()
    return [c.to_dict() for c in cryptids]


@router.get("/cryptids/{slug}")
async def get_cryptid(slug: str, db: AsyncSession = Depends(get_db)):
    """Get a single cryptid by slug."""
    result = await db.execute(
        select(Cryptid).where(Cryptid.slug == slug)
    )
    cryptid = result.scalar_one_or_none()

    if not cryptid:
        raise HTTPException(404, f"Cryptid '{slug}' not found")

    return cryptid.to_dict()
