"""
Sighting validation logic for the Kafka consumer pipeline.

Validates: bounds, cryptid slug, evidence level, profanity, dedup.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Kentucky bounding box (WGS84)
KY_MIN_LAT = 36.49
KY_MAX_LAT = 39.15
KY_MIN_LON = -89.57
KY_MAX_LON = -81.96

# Basic profanity word list (extend as needed)
_PROFANITY_WORDS = {
    "fuck", "shit", "ass", "damn", "hell", "bitch", "bastard",
    "dick", "crap", "piss", "cunt", "fag",
}
_PROFANITY_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _PROFANITY_WORDS) + r")\b",
    re.IGNORECASE,
)


def validate_bounds(lat: float, lon: float) -> tuple[bool, str]:
    """Check that coordinates fall within Kentucky bounding box."""
    if not (KY_MIN_LAT <= lat <= KY_MAX_LAT):
        return False, f"Latitude {lat} outside Kentucky range ({KY_MIN_LAT}-{KY_MAX_LAT})"
    if not (KY_MIN_LON <= lon <= KY_MAX_LON):
        return False, f"Longitude {lon} outside Kentucky range ({KY_MIN_LON}-{KY_MAX_LON})"
    return True, ""


def validate_required_fields(sighting: dict) -> tuple[bool, str]:
    """Validate required fields are present and non-empty."""
    required = ["sighting_id", "cryptid_slug", "latitude", "longitude", "reporter_name"]
    for field in required:
        if field not in sighting or sighting[field] is None:
            return False, f"Missing required field: {field}"
        if isinstance(sighting[field], str) and not sighting[field].strip():
            return False, f"Empty required field: {field}"
    return True, ""


def validate_evidence_level(level) -> tuple[bool, str]:
    """Validate evidence level is 1-5."""
    try:
        level = int(level)
        if not (1 <= level <= 5):
            return False, f"Evidence level {level} not in range 1-5"
        return True, ""
    except (TypeError, ValueError):
        return False, f"Invalid evidence level: {level}"


def validate_profanity(text: str | None) -> tuple[bool, str]:
    """Check description for profanity."""
    if not text:
        return True, ""
    match = _PROFANITY_PATTERN.search(text)
    if match:
        return False, f"Profanity detected: {match.group()}"
    return True, ""


def validate_sighting(sighting: dict, known_slugs: set[str]) -> tuple[bool, str]:
    """
    Run the full validation pipeline on a sighting message.

    Args:
        sighting: Parsed JSON message from Kafka.
        known_slugs: Set of valid cryptid slugs from the database.

    Returns:
        Tuple of (is_valid, rejection_reason).
    """
    # 1. Required fields
    ok, reason = validate_required_fields(sighting)
    if not ok:
        return False, reason

    # 2. Bounds check
    try:
        lat = float(sighting["latitude"])
        lon = float(sighting["longitude"])
    except (TypeError, ValueError) as exc:
        return False, f"Invalid coordinates: {exc}"

    ok, reason = validate_bounds(lat, lon)
    if not ok:
        return False, reason

    # 3. Cryptid slug validation
    slug = sighting.get("cryptid_slug", "")
    if slug not in known_slugs:
        return False, f"Unknown cryptid slug: {slug}"

    # 4. Evidence level
    ok, reason = validate_evidence_level(sighting.get("evidence_level", 1))
    if not ok:
        return False, reason

    # 5. Profanity filter
    ok, reason = validate_profanity(sighting.get("description"))
    if not ok:
        return False, reason

    return True, ""
