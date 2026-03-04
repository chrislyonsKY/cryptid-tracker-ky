# DL-001: Four-Service Architecture with Justified Roles

**Date:** 2026-03-04
**Status:** Accepted
**Author:** Chris Lyons

## Context

The Aiven Free Tier Competition offers four managed services: PostgreSQL, Apache Kafka, MySQL, and Valkey. Using multiple services earns bonus consideration from judges, but each service must have a genuine architectural role — judges will see through shoehorned usage.

## Decision

We will use all four services with the following clearly distinct responsibilities:

- **PostgreSQL + PostGIS** — Spatial data store. The authoritative source for sighting geometry, cryptid references, and county boundaries. Handles all spatial operations (indexing, joins, clustering). This is the system of record.
- **Apache Kafka** — Event streaming ingest layer. Decouples sighting submission from processing. Enables the consumer validation pipeline and demonstrates real streaming architecture. Also enables the live demo generator.
- **Valkey** — Computed cache layer. Stores pre-computed threat levels, live stats, recent sightings list, and reporter leaderboard. Eliminates repeated expensive PostGIS spatial joins on every API request.
- **MySQL** — Community features (user accounts, comments, votes on sightings). Separates transactional user-interaction data from analytical spatial data. Reasonable microservice boundary even if this were a larger system.

## Alternatives Considered

- **Skip MySQL** — Use only PG for everything. Rejected because using only 3 services is weaker for judging, and the community/analytical separation is architecturally defensible.
- **Skip Valkey** — Query PostGIS directly for stats/threat levels. Rejected because repeated spatial joins are expensive on shared free tier, and Valkey demonstrates proper caching architecture.
- **Skip Kafka** — Direct API → DB writes. Rejected because this is the most interesting architectural component and enables the generator demo.

## Consequences

- Four services means four connection configurations and more operational surface area
- MySQL usage is the weakest justification — keep the community features lightweight but functional
- The story/write-up must clearly explain each service's role to satisfy the 50% narrative criterion
