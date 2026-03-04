"""
Synthetic sighting generator — produces realistic cryptid sightings for demo.

Supports batch mode (seed N sightings) and stream mode (continuous real-time).
See ai-dev/architecture.md for generation strategies.

Usage:
    python -m src.generator.main --mode batch --count 100
    python -m src.generator.main --mode stream --interval-min 5 --interval-max 30
    python -m src.generator.main --mode stream --cryptid bigfoot
"""

import argparse
import logging
import random
import signal
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

from src.generator.producer import create_producer, produce_sighting
from src.generator.strategies import (
    CRYPTID_PROFILES,
    generate_description,
    generate_evidence_level,
    generate_location,
    generate_random_name,
    get_seasonal_weight,
)

logger = logging.getLogger(__name__)

_running = True


def _signal_handler(signum, frame):
    """Graceful shutdown on signal."""
    global _running
    logger.info("Received signal %s, stopping generator...", signum)
    _running = False


def generate_sighting(
    cryptid_slug: str | None = None,
    days_back: int = 0,
) -> dict:
    """
    Generate a single synthetic sighting.

    Args:
        cryptid_slug: Force a specific cryptid type, or None for weighted random.
        days_back: Maximum days in the past for the sighting date.

    Returns:
        Dict matching the sighting-raw Kafka message schema.
    """
    # Select cryptid
    if cryptid_slug and cryptid_slug in CRYPTID_PROFILES:
        profile = CRYPTID_PROFILES[cryptid_slug]
    else:
        # Weighted selection — higher danger = slightly less common
        slugs = list(CRYPTID_PROFILES.keys())
        profiles = [CRYPTID_PROFILES[s] for s in slugs]
        weights = [1.0 / max(p.danger_rating, 1) for p in profiles]
        profile = random.choices(profiles, weights=weights, k=1)[0]

    # Generate location
    lat, lon = generate_location(profile)

    # Generate date
    if days_back > 0:
        offset_days = random.randint(0, days_back)
        sighting_date = datetime.now(timezone.utc) - timedelta(days=offset_days)
    else:
        sighting_date = datetime.now(timezone.utc)

    # Apply seasonal weighting — skip if off-season (30% chance)
    month = sighting_date.month
    seasonal_weight = get_seasonal_weight(profile, month)
    if random.random() > seasonal_weight:
        # Re-roll to a peak month
        if profile.peak_months:
            import calendar
            new_month = random.choice(profile.peak_months)
            max_day = calendar.monthrange(sighting_date.year, new_month)[1]
            sighting_date = sighting_date.replace(
                month=new_month,
                day=min(sighting_date.day, max_day),
            )

    # Generate time of day
    peak_start, peak_end = profile.peak_hours
    if random.random() < 0.7:  # 70% during peak hours
        if peak_start <= peak_end:
            hour = random.randint(peak_start, peak_end)
        else:
            hour = random.choice(
                list(range(peak_start, 24)) + list(range(0, peak_end + 1))
            )
    else:
        hour = random.randint(0, 23)

    sighting_date = sighting_date.replace(
        hour=hour,
        minute=random.randint(0, 59),
        second=random.randint(0, 59),
    )

    sighting_id = str(uuid.uuid4())

    return {
        "sighting_id": sighting_id,
        "cryptid_slug": profile.slug,
        "latitude": lat,
        "longitude": lon,
        "reporter_name": generate_random_name(),
        "description": generate_description(profile),
        "evidence_level": generate_evidence_level(profile),
        "sighting_date": sighting_date.isoformat(),
        "source": "generator",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }


def run_batch(count: int, cryptid: str | None, days_back: int) -> None:
    """Generate N sightings and publish in batch."""
    logger.info("Batch mode: generating %d sightings (days_back=%d)", count, days_back)
    producer = create_producer()

    for i in range(count):
        sighting = generate_sighting(cryptid_slug=cryptid, days_back=days_back)
        produce_sighting(producer, sighting)
        if (i + 1) % 10 == 0:
            logger.info("Generated %d / %d sightings", i + 1, count)

    remaining = producer.flush(timeout=30)
    if remaining > 0:
        logger.warning("%d messages still in queue after flush", remaining)
    else:
        logger.info("Batch complete: %d sightings produced", count)


def run_stream(
    cryptid: str | None,
    interval_min: float,
    interval_max: float,
) -> None:
    """Stream sightings continuously at random intervals."""
    logger.info(
        "Stream mode: interval %.1f-%.1fs, cryptid=%s",
        interval_min, interval_max, cryptid or "all",
    )
    producer = create_producer()
    count = 0

    signal.signal(signal.SIGINT, _signal_handler)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, _signal_handler)

    while _running:
        sighting = generate_sighting(cryptid_slug=cryptid, days_back=0)
        produce_sighting(producer, sighting)
        count += 1

        logger.info(
            "[%d] %s sighting by %s at (%.4f, %.4f)",
            count,
            sighting["cryptid_slug"],
            sighting["reporter_name"],
            sighting["latitude"],
            sighting["longitude"],
        )

        wait = random.uniform(interval_min, interval_max)
        # Use small sleep increments for responsive shutdown
        elapsed = 0.0
        while elapsed < wait and _running:
            time.sleep(min(0.5, wait - elapsed))
            elapsed += 0.5

    producer.flush(timeout=10)
    logger.info("Stream stopped after %d sightings", count)


def main():
    """CLI entry point for the sighting generator."""
    parser = argparse.ArgumentParser(
        description="Cryptid Tracker KY — Synthetic Sighting Generator"
    )
    parser.add_argument(
        "--mode", choices=["batch", "stream"], default="stream",
        help="Generation mode (default: stream)",
    )
    parser.add_argument(
        "--count", type=int, default=100,
        help="Number of sightings for batch mode (default: 100)",
    )
    parser.add_argument(
        "--days-back", type=int, default=365,
        help="Max days in the past for batch sightings (default: 365)",
    )
    parser.add_argument(
        "--cryptid", type=str, default=None,
        help="Filter to a specific cryptid slug",
    )
    parser.add_argument(
        "--interval-min", type=float, default=5.0,
        help="Min seconds between stream sightings (default: 5)",
    )
    parser.add_argument(
        "--interval-max", type=float, default=30.0,
        help="Max seconds between stream sightings (default: 30)",
    )

    args = parser.parse_args()

    if args.mode == "batch":
        run_batch(args.count, args.cryptid, args.days_back)
    else:
        run_stream(args.cryptid, args.interval_min, args.interval_max)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    main()
