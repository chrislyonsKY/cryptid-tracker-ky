# DL-002: Real Data + Synthetic Augmentation Strategy

**Date:** 2026-03-04
**Status:** Accepted
**Author:** Chris Lyons

## Context

The project needs sighting data to populate the map and demonstrate the streaming architecture. We could generate entirely synthetic data, but real data adds credibility and demonstrates actual ETL skills.

## Decision

Use a hybrid approach:

1. **BFRO Bigfoot sightings** (real, geocoded) — filtered to Kentucky. ~100-200 records with lat/lon, dates, descriptions. Loaded via seed ETL script.
2. **NUFORC UFO sightings** (real, geocoded) — filtered to Kentucky. ~500-1000 records. Mapped to a "UFO/UAP" cryptid type.
3. **Hand-curated cryptid reference** (~12 Kentucky cryptids) — original content based on documented folklore.
4. **Synthetic sightings** (generated) — for the ~10 non-Bigfoot/non-UFO cryptid types. Weighted toward folklore-documented locations. Used for seed data AND real-time generator demo.

All sightings carry a `source` field (`bfro`, `nuforc`, `generator`, `user`) for transparency.

## Alternatives Considered

- **100% synthetic** — Simpler but less compelling. Doesn't demonstrate real data ETL, which is a core skill. Rejected.
- **100% real data** — Only Bigfoot and UFOs have structured datasets. The other ~10 cryptids have folklore references but no geocoded sighting databases. Rejected as too limited.
- **Web scraping for more data** — Could scrape kentuckybigfoot.com or other sources, but adds complexity and potential legal/ethical issues. Rejected as not worth the risk for a competition.

## Consequences

- Need to handle two different CSV schemas (BFRO, NUFORC) in ETL scripts
- NUFORC copyright notice means we should paraphrase descriptions, not reproduce verbatim
- Generator must produce realistic-looking data (folklore-weighted locations, seasonal patterns)
- The hybrid approach is itself a good story element for the write-up
