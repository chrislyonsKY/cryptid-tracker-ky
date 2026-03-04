/**
 * Main application orchestrator.
 * Initializes all modules, loads data, sets up polling.
 * Cryptid Tracker KY
 */
(function App() {
    'use strict';

    let pollTimer = null;
    let cryptids = [];

    // ── Bootstrap ───────────────────────────────────────────
    window.addEventListener('map:ready', async () => {
        console.log('[App] Map ready, initializing...');
        Sidebar.initTabs();
        Sidebar.initLayerToggles();
        Sidebar.initSubmitForm(submitSighting);

        // Filters
        document.getElementById('apply-filters').addEventListener('click', loadSightings);
        document.getElementById('reset-filters').addEventListener('click', () => {
            document.getElementById('filter-cryptid').value = '';
            document.getElementById('filter-evidence').value = '';
            loadSightings();
        });

        // Initial data load (parallel)
        await Promise.all([
            loadCryptids(),
            loadCounties(),
            loadSightings(),
            loadStats(),
            loadFeed(),
        ]);

        // Start polling
        startPolling();
        console.log('[App] Initialization complete.');
    });

    // Initialize the map immediately
    MapManager.init();

    // ── Data Loaders ────────────────────────────────────────
    async function loadCryptids() {
        try {
            cryptids = await API.getCryptids();
            Sidebar.populateCryptidDropdowns(cryptids);
        } catch (err) {
            console.warn('[App] Failed to load cryptids:', err.message);
        }
    }

    async function loadCounties() {
        try {
            const geojson = await API.getCounties();
            if (geojson && geojson.features) {
                MapManager.setCountyData(geojson);
            }
        } catch (err) {
            console.warn('[App] Failed to load counties:', err.message);
        }
    }

    async function loadSightings() {
        try {
            const filters = Sidebar.getFilters();
            const geojson = await API.getSightings({ ...filters, limit: 500 });
            if (geojson && geojson.features) {
                MapManager.setSightingsData(geojson);
            }
        } catch (err) {
            console.warn('[App] Failed to load sightings:', err.message);
        }
    }

    async function loadStats() {
        try {
            const [stats, leaderboard] = await Promise.all([
                API.getStats(),
                API.getLeaderboard(),
            ]);
            Sidebar.updateStats(stats);
            Sidebar.updateLeaderboard(leaderboard);
        } catch (err) {
            console.warn('[App] Failed to load stats:', err.message);
        }
    }

    async function loadFeed() {
        try {
            const recent = await API.getRecentSightings();
            Sidebar.updateFeed(recent);
        } catch (err) {
            console.warn('[App] Failed to load feed:', err.message);
            // Fallback: use sighting data from map
        }
    }

    // ── Actions ─────────────────────────────────────────────
    async function submitSighting(data) {
        const result = await API.submitSighting(data);
        // Refresh feed and sightings after brief delay (give Kafka time to process)
        setTimeout(() => {
            loadFeed();
            loadSightings();
        }, 2000);
        return result;
    }

    // ── Polling ─────────────────────────────────────────────
    function startPolling() {
        const interval = window.CONFIG.POLL_INTERVAL || 30000;
        pollTimer = setInterval(async () => {
            await Promise.all([loadFeed(), loadStats()]);
        }, interval);
    }

    function stopPolling() {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    }

    // Pause polling when tab is hidden
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            stopPolling();
        } else {
            loadFeed();
            loadStats();
            startPolling();
        }
    });
})();
