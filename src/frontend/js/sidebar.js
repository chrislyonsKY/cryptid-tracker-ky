/**
 * Sidebar panel management — live feed, stats, filters, submit form.
 * Cryptid Tracker KY
 */
const Sidebar = (() => {
    const EVIDENCE_LABELS = {
        1: 'Rustling Bushes',
        2: 'Strange Sound',
        3: 'Blurry Photo',
        4: 'Clear Photo',
        5: 'Physical Evidence',
    };

    function _announce(message) {
        const announcer = document.getElementById('a11y-announcer');
        if (!announcer) return;
        announcer.textContent = '';
        window.setTimeout(() => {
            announcer.textContent = message;
        }, 20);
    }

    function _activateTab(tab, moveFocus = false) {
        const tabs = Array.from(document.querySelectorAll('.tab'));
        const panels = Array.from(document.querySelectorAll('.tab-panel'));
        tabs.forEach((t) => {
            const selected = t === tab;
            t.classList.toggle('active', selected);
            t.setAttribute('aria-selected', String(selected));
            t.setAttribute('tabindex', selected ? '0' : '-1');
        });

        panels.forEach((panel) => {
            const isActive = panel.id === `panel-${tab.dataset.tab}`;
            panel.classList.toggle('active', isActive);
            panel.hidden = !isActive;
        });

        if (moveFocus) {
            tab.focus();
        }

        if (tab.dataset.tab === 'submit') {
            MapManager.startLocationPicker(_onLocationPicked);
        } else {
            MapManager.stopLocationPicker();
        }

        _announce(`${tab.textContent.trim()} panel active`);
    }

    // ── Tab switching ───────────────────────────────────────
    function initTabs() {
        const tabs = Array.from(document.querySelectorAll('.tab'));
        tabs.forEach((tab, index) => {
            tab.addEventListener('click', () => _activateTab(tab));
            tab.addEventListener('keydown', (event) => {
                let nextIndex = null;
                if (event.key === 'ArrowRight') {
                    nextIndex = (index + 1) % tabs.length;
                } else if (event.key === 'ArrowLeft') {
                    nextIndex = (index - 1 + tabs.length) % tabs.length;
                } else if (event.key === 'Home') {
                    nextIndex = 0;
                } else if (event.key === 'End') {
                    nextIndex = tabs.length - 1;
                }

                if (nextIndex !== null) {
                    event.preventDefault();
                    _activateTab(tabs[nextIndex], true);
                }
            });
        });

        const activeTab = document.querySelector('.tab.active') || tabs[0];
        if (activeTab) _activateTab(activeTab);
    }

    // ── Live Feed ───────────────────────────────────────────
    function updateFeed(sightings) {
        const container = document.getElementById('live-feed');
        if (!sightings || sightings.length === 0) {
            container.innerHTML = '<p class="loading">No recent sightings.</p>';
            return;
        }
        container.innerHTML = sightings.map((s, i) => _feedItemHtml(s, i === 0)).join('');
        _announce(`Live feed updated with ${sightings.length} sightings`);

        // Click handler — fly to location
        container.querySelectorAll('.feed-item').forEach((el) => {
            el.setAttribute('tabindex', '0');
            el.setAttribute('role', 'button');
            el.setAttribute('aria-label', 'Fly map to sighting location');
            el.addEventListener('click', () => {
                const lng = parseFloat(el.dataset.lng);
                const lat = parseFloat(el.dataset.lat);
                if (lng && lat) MapManager.flyTo(lng, lat);
            });
            el.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    const lng = parseFloat(el.dataset.lng);
                    const lat = parseFloat(el.dataset.lat);
                    if (lng && lat) MapManager.flyTo(lng, lat);
                }
            });
        });
    }

    function _feedItemHtml(sighting, isNew) {
        // Handle both GeoJSON feature and flat object formats
        const props = sighting.properties || sighting;
        const coords = sighting.geometry
            ? sighting.geometry.coordinates
            : [props.longitude, props.latitude];

        const ago = _timeAgo(props.sighted_at || props.timestamp);
        const name = props.cryptid_name || props.cryptid_slug || props.cryptid || 'Unknown';
        const evidence = props.evidence_level || 3;
        const reporter = props.reporter_name || 'Anonymous';

        return `
            <div class="feed-item${isNew ? ' new' : ''}" 
                 data-lng="${coords[0]}" data-lat="${coords[1]}">
                <div class="feed-item-header">
                    <span class="feed-creature">${_escapeHtml(name)}</span>
                    <span class="feed-time">${ago}</span>
                </div>
                <div class="feed-meta">
                    ${_escapeHtml(reporter)}
                    <span class="feed-evidence evidence-${evidence}">${EVIDENCE_LABELS[evidence] || '?'}</span>
                </div>
            </div>
        `;
    }

    // ── Stats ───────────────────────────────────────────────
    function updateStats(stats) {
        document.getElementById('stat-total').textContent =
            _formatNumber(stats.total_sightings || 0);
        document.getElementById('stat-30d').textContent =
            _formatNumber(stats.last_30_days || stats.sightings_30d || 0);
        
        // most_sighted is an object {slug, count} or null
        const mostSighted = stats.most_sighted;
        document.getElementById('stat-most-sighted').textContent =
            mostSighted ? `${mostSighted.slug} (${mostSighted.count})` : '—';
    }

    function updateLeaderboard(entries) {
        const container = document.getElementById('leaderboard');
        if (!entries || entries.length === 0) {
            container.innerHTML = '<p class="loading">No reporters yet.</p>';
            return;
        }
        container.innerHTML = entries
            .map((entry, i) => {
                const name = entry.reporter || entry.name || 'Anonymous';
                const count = entry.count || entry.score || 0;
                const rankClass = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : '';
                return `
                    <div class="leaderboard-row">
                        <span class="leaderboard-rank ${rankClass}">${i + 1}</span>
                        <span class="leaderboard-name">${_escapeHtml(name)}</span>
                        <span class="leaderboard-count">${count}</span>
                    </div>
                `;
            })
            .join('');
    }

    // ── Filters ─────────────────────────────────────────────
    function populateCryptidDropdowns(cryptids) {
        const options = cryptids
            .map(c => `<option value="${c.slug}">${_escapeHtml(c.name)}</option>`)
            .join('');

        // Filter dropdown
        const filterSelect = document.getElementById('filter-cryptid');
        filterSelect.innerHTML = '<option value="">All Cryptids</option>' + options;

        // Submit dropdown
        const submitSelect = document.getElementById('submit-cryptid');
        submitSelect.innerHTML = '<option value="">Select cryptid...</option>' + options;
    }

    function getFilters() {
        return {
            cryptid: document.getElementById('filter-cryptid').value || undefined,
            evidence_min: document.getElementById('filter-evidence').value || undefined,
        };
    }

    function initLayerToggles() {
        document.getElementById('toggle-threat').addEventListener('change', (e) => {
            MapManager.toggleLayer('threat', e.target.checked);
        });
        document.getElementById('toggle-markers').addEventListener('change', (e) => {
            MapManager.toggleLayer('markers', e.target.checked);
        });
        document.getElementById('toggle-heatmap').addEventListener('change', (e) => {
            MapManager.toggleLayer('heatmap', e.target.checked);
        });
    }

    // ── Submit Form ─────────────────────────────────────────
    function _onLocationPicked(lngLat) {
        document.getElementById('submit-lat').value = lngLat.lat.toFixed(6);
        document.getElementById('submit-lon').value = lngLat.lng.toFixed(6);
        document.getElementById('submit-location').value =
            `${lngLat.lat.toFixed(4)}°N, ${Math.abs(lngLat.lng).toFixed(4)}°W`;
    }

    function initSubmitForm(onSubmit) {
        const form = document.getElementById('sighting-form');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const lat = parseFloat(document.getElementById('submit-lat').value);
            const lon = parseFloat(document.getElementById('submit-lon').value);

            if (!lat || !lon) {
                _showSubmitResult('Click the map to set the sighting location first.', false);
                return;
            }

            const data = {
                cryptid_slug: document.getElementById('submit-cryptid').value,
                latitude: lat,
                longitude: lon,
                reporter_name: document.getElementById('submit-name').value.trim(),
                description: document.getElementById('submit-description').value.trim() || undefined,
                evidence_level: parseInt(document.getElementById('submit-evidence').value, 10),
            };

            try {
                const result = await onSubmit(data);
                _showSubmitResult(`Sighting accepted! ID: ${result.sighting_id || 'processing'}`, true);
                form.reset();
                document.getElementById('submit-location').value = '';
            } catch (err) {
                _showSubmitResult(`Error: ${err.message}`, false);
            }
        });
    }

    function _showSubmitResult(message, success) {
        const el = document.getElementById('submit-result');
        el.textContent = message;
        el.className = success ? 'success' : 'error';
        el.classList.remove('hidden');
        _announce(message);
        setTimeout(() => el.classList.add('hidden'), 5000);
    }

    // ── Utilities ───────────────────────────────────────────
    function _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function _timeAgo(iso) {
        if (!iso) return '';
        const diff = (Date.now() - new Date(iso).getTime()) / 1000;
        if (diff < 60) return 'just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
        return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }

    function _formatNumber(n) {
        return n.toLocaleString('en-US');
    }

    return {
        initTabs,
        updateFeed,
        updateStats,
        updateLeaderboard,
        populateCryptidDropdowns,
        getFilters,
        initLayerToggles,
        initSubmitForm,
    };
})();
