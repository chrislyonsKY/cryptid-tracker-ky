"""
Sighting generation strategies — folklore-weighted locations, seasonal patterns.

Each cryptid type has weighted hotspot zones within Kentucky.
"""

import random
from dataclasses import dataclass, field

# Kentucky bounding box
KY_MIN_LAT, KY_MAX_LAT = 36.49, 39.15
KY_MIN_LON, KY_MAX_LON = -89.57, -81.96


@dataclass
class Hotspot:
    """A geographic hotspot for a cryptid type."""

    lat: float
    lon: float
    radius_deg: float = 0.15  # ~10 miles
    weight: float = 1.0


@dataclass
class CryptidProfile:
    """Generation profile for a cryptid type."""

    slug: str
    name: str
    danger_rating: int
    hotspots: list[Hotspot] = field(default_factory=list)
    peak_months: list[int] = field(default_factory=lambda: [6, 7, 8, 9, 10])
    peak_hours: tuple[int, int] = (19, 23)  # 7pm - 11pm
    evidence_weights: list[float] = field(
        default_factory=lambda: [0.35, 0.30, 0.20, 0.10, 0.05]
    )
    description_templates: list[str] = field(default_factory=list)


# --- Cryptid profiles with folklore-accurate hotspots ---

CRYPTID_PROFILES: dict[str, CryptidProfile] = {
    "bigfoot": CryptidProfile(
        slug="bigfoot",
        name="Bigfoot",
        danger_rating=3,
        hotspots=[
            Hotspot(37.75, -83.50, 0.3, 3.0),   # Daniel Boone NF
            Hotspot(36.85, -84.50, 0.2, 2.0),   # Cumberland Gap area
            Hotspot(37.20, -86.50, 0.2, 1.5),   # Mammoth Cave
            Hotspot(38.10, -83.80, 0.25, 1.0),  # Eastern KY mountains
        ],
        peak_months=[5, 6, 7, 8, 9, 10],
        description_templates=[
            "Large bipedal figure observed near tree line at dusk",
            "Heard heavy footsteps and branch snapping in dense forest",
            "Strong sulfuric odor detected near creek crossing",
            "Found large footprint (18 inches) in soft mud along trail",
            "Massive dark figure crossed the road ahead of my vehicle",
            "Witnessed tall, hair-covered creature foraging near berry bushes",
            "Howling sounds echoing through hollow, unlike any known animal",
        ],
    ),
    "pope-lick-monster": CryptidProfile(
        slug="pope-lick-monster",
        name="Pope Lick Monster",
        danger_rating=5,
        hotspots=[
            Hotspot(38.19, -85.63, 0.05, 5.0),  # Pope Lick trestle
            Hotspot(38.25, -85.75, 0.1, 1.0),   # Greater Louisville
        ],
        peak_months=[3, 4, 10, 11],
        peak_hours=(21, 3),
        description_templates=[
            "Goat-like creature spotted on the railroad trestle at night",
            "Heard unearthly screaming near the Pope Lick bridge",
            "Distorted figure with horns seen lurking beneath the trestle",
            "Hypnotic voice lured me toward the tracks before I snapped out of it",
            "Half-goat, half-man silhouette on the trestle against moonlight",
        ],
    ),
    "beast-between-the-lakes": CryptidProfile(
        slug="beast-between-the-lakes",
        name="Beast Between the Lakes",
        danger_rating=5,
        hotspots=[
            Hotspot(36.83, -88.07, 0.15, 5.0),  # Land Between the Lakes
            Hotspot(36.95, -88.20, 0.1, 2.0),
        ],
        peak_months=[6, 7, 8, 9],
        peak_hours=(22, 4),
        description_templates=[
            "Massive wolf-like creature standing on hind legs at campsite",
            "Found mutilated deer carcass, claw marks unlike any bear",
            "Red eyes reflecting from flashlight in the woods at LBL",
            "Canine howling mixed with almost human screaming, blood-curdling",
            "Enormous paw prints found with elongated digit marks",
        ],
    ),
    "mothman": CryptidProfile(
        slug="mothman",
        name="Mothman",
        danger_rating=4,
        hotspots=[
            Hotspot(38.06, -83.95, 0.1, 3.0),   # Mount Sterling
            Hotspot(38.20, -84.90, 0.15, 2.0),  # Lexington bridges
            Hotspot(38.25, -85.75, 0.15, 1.5),  # Louisville bridges
        ],
        peak_months=[10, 11, 12, 1],
        peak_hours=(20, 2),
        description_templates=[
            "Large winged creature with glowing red eyes on bridge railing",
            "Enormous dark shape swooped over car on highway",
            "Moth-like creature perched on cell tower, eyes like embers",
            "Felt wave of dread before spotting winged figure above bridge",
            "Witnessed dark shape with 12-foot wingspan near power lines",
        ],
    ),
    "herrington-lake-monster": CryptidProfile(
        slug="herrington-lake-monster",
        name="Herrington Lake Monster",
        danger_rating=3,
        hotspots=[
            Hotspot(37.77, -84.75, 0.1, 5.0),   # Herrington Lake
            Hotspot(37.82, -84.72, 0.08, 2.0),
        ],
        peak_months=[5, 6, 7, 8, 9],
        peak_hours=(6, 10),
        description_templates=[
            "Long serpentine wake in calm water, no boats around",
            "Large dark shape visible beneath surface near the dam",
            "Fishing line snapped by something massive — saw a humped back surface",
            "Multiple witnesses saw large creature swimming near marina",
            "Heard deep splashing sounds at night from dock",
        ],
    ),
    "bearilla": CryptidProfile(
        slug="bearilla",
        name="Bearilla",
        danger_rating=3,
        hotspots=[
            Hotspot(38.30, -84.00, 0.12, 5.0),  # Nicholas County
            Hotspot(38.20, -83.85, 0.1, 2.0),
        ],
        peak_months=[4, 5, 6, 9, 10],
        description_templates=[
            "Creature resembling a gorilla-bear hybrid foraging in field",
            "Massive footprints found — too wide for a bear, too long for a human",
            "Dark shaggy creature walking upright along fence line",
            "Livestock acting terrified, found unknown scat near barn",
        ],
    ),
    "hillbilly-beast": CryptidProfile(
        slug="hillbilly-beast",
        name="Hillbilly Beast",
        danger_rating=4,
        hotspots=[
            Hotspot(37.50, -82.80, 0.2, 3.0),   # Eastern KY mountains
            Hotspot(37.80, -83.30, 0.15, 2.0),
            Hotspot(37.15, -83.50, 0.15, 1.5),
        ],
        peak_months=[5, 6, 7, 8, 9, 10],
        description_templates=[
            "Massive dark figure threw rocks at our campsite from the ridgeline",
            "Found large stick structures and tree breaks in hollow",
            "Heard wood knocking echoing through the mountains after sunset",
            "Aggressive creature stood in road, wouldn't move for the truck",
        ],
    ),
    "sturgis-vampire": CryptidProfile(
        slug="sturgis-vampire",
        name="Sturgis Vampire",
        danger_rating=4,
        hotspots=[
            Hotspot(37.55, -87.98, 0.08, 5.0),  # Union County / Sturgis
        ],
        peak_months=[10, 11, 12, 1, 2],
        peak_hours=(23, 4),
        description_templates=[
            "Pale figure spotted near old cemetery at midnight",
            "Livestock found drained of blood near Sturgis",
            "Shadowy figure with unnatural speed darted between buildings",
            "Cold presence and scratching sounds outside window at night",
        ],
    ),
    "spottsville-monster": CryptidProfile(
        slug="spottsville-monster",
        name="Spottsville Monster",
        danger_rating=2,
        hotspots=[
            Hotspot(37.83, -87.43, 0.1, 5.0),   # Henderson County
        ],
        peak_months=[6, 7, 8, 9],
        description_templates=[
            "Heard strange grunting sounds in the woods near Spottsville",
            "Found unusual tracks too large for local wildlife",
            "Dark shape seen moving through corn field at twilight",
        ],
    ),
    "giraffe-possum": CryptidProfile(
        slug="giraffe-possum",
        name="Giraffe-Possum",
        danger_rating=1,
        hotspots=[
            Hotspot(37.97, -84.18, 0.1, 5.0),   # Clark County
        ],
        peak_months=[3, 4, 5, 6, 7, 8, 9, 10],
        evidence_weights=[0.50, 0.25, 0.15, 0.08, 0.02],
        description_templates=[
            "Odd creature with long neck like a possum on stilts, ran into bushes",
            "I swear I saw a possum with a giraffe neck crossing the road",
            "My dog chased something strange-looking into the field",
        ],
    ),
    "boonesborough-octopus": CryptidProfile(
        slug="boonesborough-octopus",
        name="Boonesborough Octopus",
        danger_rating=3,
        hotspots=[
            Hotspot(37.90, -84.27, 0.08, 5.0),  # Kentucky River / Boonesborough
        ],
        peak_months=[5, 6, 7, 8, 9],
        peak_hours=(5, 11),
        description_templates=[
            "Multiple tentacles broke the surface of the Kentucky River",
            "Fishing net pulled under with tremendous force — saw appendages",
            "Large splash and tentacle-like shapes near the river bank",
            "Something with multiple arms pulled a duck under the water",
        ],
    ),
    "ufo": CryptidProfile(
        slug="ufo",
        name="UFO / UAP",
        danger_rating=2,
        hotspots=[
            Hotspot(38.25, -85.75, 0.2, 2.0),   # Louisville
            Hotspot(38.05, -84.50, 0.2, 2.0),   # Lexington
            Hotspot(37.08, -88.60, 0.15, 1.5),  # Paducah
            Hotspot(37.78, -87.10, 0.15, 1.0),  # Owensboro
            Hotspot(39.08, -84.50, 0.15, 1.5),  # Northern KY
        ],
        peak_months=[6, 7, 8, 9, 10, 11],
        peak_hours=(21, 3),
        evidence_weights=[0.25, 0.25, 0.30, 0.15, 0.05],
        description_templates=[
            "Bright triangular formation of lights hovering silently",
            "Orb of light moving erratically, changed direction at impossible speed",
            "Large disc-shaped object with lights around perimeter, hovered over field",
            "Witnessed fast-moving bright object, left no contrail, silent",
            "Multiple colored lights in formation, disappeared simultaneously",
            "Cigar-shaped metallic object motionless in sky for several minutes",
        ],
    ),
}

# Reporter name pools
FIRST_NAMES = [
    "Daniel", "Sarah", "Billy", "Mary", "James", "Emma", "John", "Elizabeth",
    "Robert", "Anna", "Thomas", "Martha", "William", "Patricia", "David",
    "Jennifer", "Michael", "Linda", "Harlan", "Cletus", "Earl", "Dolly",
    "Loretta", "Patsy", "Buck", "Dale", "Waylon", "Tammy", "Reba", "Conway",
]

LAST_NAMES = [
    "Boone", "Clay", "Breckinridge", "Shelby", "Morgan", "Combs", "Perkins",
    "Howard", "Hatfield", "McCoy", "Calloway", "Winchester", "Henderson",
    "Hardin", "McCreary", "Sloan", "Webb", "Stanton", "Wolfe", "Breathitt",
    "Whitley", "Knott", "Letcher", "Floyd", "Pike", "Martin", "Elliott",
]


def generate_random_name() -> str:
    """Generate a random Kentucky-flavored reporter name."""
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def generate_location(profile: CryptidProfile) -> tuple[float, float]:
    """
    Generate a weighted random location for a cryptid sighting.

    Selects a hotspot based on weights, then adds gaussian noise.
    Falls back to random KY coordinate if no hotspots defined.
    """
    if not profile.hotspots:
        lat = random.uniform(KY_MIN_LAT, KY_MAX_LAT)
        lon = random.uniform(KY_MIN_LON, KY_MAX_LON)
        return lat, lon

    # Weighted random hotspot selection
    weights = [h.weight for h in profile.hotspots]
    hotspot = random.choices(profile.hotspots, weights=weights, k=1)[0]

    # Add gaussian noise within radius
    lat = hotspot.lat + random.gauss(0, hotspot.radius_deg / 3)
    lon = hotspot.lon + random.gauss(0, hotspot.radius_deg / 3)

    # Clamp to KY bounds
    lat = max(KY_MIN_LAT, min(KY_MAX_LAT, lat))
    lon = max(KY_MIN_LON, min(KY_MAX_LON, lon))

    return round(lat, 6), round(lon, 6)


def generate_evidence_level(profile: CryptidProfile) -> int:
    """Generate weighted random evidence level (1-5)."""
    return random.choices([1, 2, 3, 4, 5], weights=profile.evidence_weights, k=1)[0]


def generate_description(profile: CryptidProfile) -> str:
    """Select a random description template for the cryptid."""
    if profile.description_templates:
        return random.choice(profile.description_templates)
    return f"Possible {profile.name} sighting reported."


def get_seasonal_weight(profile: CryptidProfile, month: int) -> float:
    """Return a weight multiplier based on month (for seasonal patterns)."""
    if month in profile.peak_months:
        return 1.0
    return 0.3  # Off-season sightings still happen, just less frequently
