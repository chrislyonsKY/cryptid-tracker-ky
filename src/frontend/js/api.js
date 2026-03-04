/**
 * API client for Cryptid Tracker KY
 * All fetch calls go through here for consistent error handling.
 */
const API = (() => {
    const BASE = window.CONFIG.API_URL;

    async function _fetch(path, options = {}) {
        try {
            const res = await fetch(`${BASE}${path}`, {
                headers: { 'Content-Type': 'application/json', ...options.headers },
                ...options,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail || `HTTP ${res.status}`);
            }
            return await res.json();
        } catch (err) {
            console.error(`[API] ${options.method || 'GET'} ${path} failed:`, err.message);
            throw err;
        }
    }

    return {
        /** Health check */
        health() {
            return _fetch('/health');
        },

        // ── Sightings ──────────────────────────────────────────
        /** Submit a new sighting. Returns 202 with accepted payload. */
        submitSighting(data) {
            return _fetch('/sightings', {
                method: 'POST',
                body: JSON.stringify(data),
            });
        },

        /** Query sightings with optional filters. Returns GeoJSON FeatureCollection. */
        getSightings(params = {}) {
            const qs = new URLSearchParams();
            if (params.bbox) qs.set('bbox', params.bbox);
            if (params.cryptid) qs.set('cryptid', params.cryptid);
            if (params.evidence_min) qs.set('evidence_min', params.evidence_min);
            if (params.after) qs.set('after', params.after);
            if (params.before) qs.set('before', params.before);
            if (params.limit) qs.set('limit', params.limit);
            if (params.offset) qs.set('offset', params.offset);
            const q = qs.toString();
            return _fetch(`/sightings${q ? '?' + q : ''}`);
        },

        /** Get recent sightings from Valkey cache. */
        getRecentSightings() {
            return _fetch('/sightings/recent');
        },

        /** Get single sighting by ID. */
        getSighting(id) {
            return _fetch(`/sightings/${id}`);
        },

        // ── Cryptids ────────────────────────────────────────────
        /** List all cryptid types. */
        getCryptids() {
            return _fetch('/cryptids');
        },

        /** Get single cryptid by slug. */
        getCryptid(slug) {
            return _fetch(`/cryptids/${slug}`);
        },

        // ── Stats ───────────────────────────────────────────────
        /** Get global stats from Valkey. */
        getStats() {
            return _fetch('/stats');
        },

        /** Get reporter leaderboard. */
        getLeaderboard() {
            return _fetch('/stats/leaderboard');
        },

        // ── Counties ────────────────────────────────────────────
        /** Get county boundaries + threat data as GeoJSON FeatureCollection. */
        getCounties() {
            return _fetch('/counties');
        },

        /** Get threat level for a single county. */
        getCountyThreat(fips) {
            return _fetch(`/counties/${fips}/threat`);
        },
    };
})();
