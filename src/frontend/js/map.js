/**
 * MapLibre GL JS map initialization and layer management.
 * Cryptid Tracker KY — Dark-themed Kentucky sighting map.
 */
const MapManager = (() => {
    let map = null;
    let popup = null;
    let locationPickerActive = false;
    let locationPickerCallback = null;

    // Cryptid color palette
    const CRYPTID_COLORS = {
        'bigfoot': '#8B4513',
        'mothman': '#DC143C',
        'hopkinsville-goblin': '#00FF41',
        'pope-lick-monster': '#9932CC',
        'hillbilly-beast': '#FF8C00',
        'tailypo': '#FFD700',
        'wampus-cat': '#FF69B4',
        'herrington-lake-monster': '#1E90FF',
        'blue-woman-of-pikeville': '#87CEEB',
        'kentucky-thunderbird': '#800000',
        'spottsville-monster': '#556B2F',
        'mud-mermaids': '#2E8B57',
    };

    // Threat level colors
    const THREAT_COLORS = {
        'none': '#238636',
        'low': '#3fb950',
        'moderate': '#d29922',
        'high': '#db6d28',
        'critical': '#f85149',
        'apocalyptic': '#bc3ddc',
    };

    function _announce(message) {
        const announcer = document.getElementById('a11y-announcer');
        if (!announcer) return;
        announcer.textContent = '';
        window.setTimeout(() => {
            announcer.textContent = message;
        }, 20);
    }

    function init() {
        const mapElement = document.getElementById('map');
        if (mapElement) {
            mapElement.setAttribute('tabindex', '0');
            mapElement.addEventListener('keydown', (e) => {
                if (!map) return;
                const center = map.getCenter();
                const step = 0.15;
                if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    map.easeTo({ center: [center.lng, center.lat + step], duration: 120 });
                } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    map.easeTo({ center: [center.lng, center.lat - step], duration: 120 });
                } else if (e.key === 'ArrowLeft') {
                    e.preventDefault();
                    map.easeTo({ center: [center.lng - step, center.lat], duration: 120 });
                } else if (e.key === 'ArrowRight') {
                    e.preventDefault();
                    map.easeTo({ center: [center.lng + step, center.lat], duration: 120 });
                }
            });
        }

        map = new maplibregl.Map({
            container: 'map',
            style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
            center: [-85.75, 37.85],
            zoom: 7,
            minZoom: 6,
            maxZoom: 16,
            maxBounds: [[-91, 35.5], [-80.5, 40.5]],
        });

        map.addControl(new maplibregl.NavigationControl(), 'top-right');

        popup = new maplibregl.Popup({
            closeButton: true,
            closeOnClick: false,
            maxWidth: '300px',
        });

        map.on('load', () => {
            _addSources();
            _addLayers();
            _addInteractions();
            _announce('Map loaded and ready');
            // Emit custom event so app.js knows the map is ready
            window.dispatchEvent(new Event('map:ready'));
        });

        // Location picker click
        map.on('click', (e) => {
            if (locationPickerActive && locationPickerCallback) {
                locationPickerCallback(e.lngLat);
                stopLocationPicker();
            }
        });

        return map;
    }

    function _addSources() {
        // County boundaries source (empty, loaded later)
        map.addSource('counties', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] },
        });

        // Sightings source with clustering
        map.addSource('sightings', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] },
            cluster: true,
            clusterMaxZoom: 12,
            clusterRadius: 50,
        });

        // Unclustered sightings for heatmap
        map.addSource('sightings-heat', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] },
        });
    }

    function _addLayers() {
        // ── County threat choropleth ──
        map.addLayer({
            id: 'county-fills',
            type: 'fill',
            source: 'counties',
            paint: {
                'fill-color': [
                    'match', ['get', 'threat_level'],
                    'none', THREAT_COLORS.none,
                    'low', THREAT_COLORS.low,
                    'moderate', THREAT_COLORS.moderate,
                    'high', THREAT_COLORS.high,
                    'critical', THREAT_COLORS.critical,
                    'apocalyptic', THREAT_COLORS.apocalyptic,
                    '#161b22', // default / unknown
                ],
                'fill-opacity': 0.2,
            },
        });

        map.addLayer({
            id: 'county-borders',
            type: 'line',
            source: 'counties',
            paint: {
                'line-color': '#30363d',
                'line-width': 0.5,
            },
        });

        // ── Heatmap layer (hidden by default) ──
        map.addLayer({
            id: 'sightings-heatmap',
            type: 'heatmap',
            source: 'sightings-heat',
            layout: { visibility: 'none' },
            paint: {
                'heatmap-weight': ['interpolate', ['linear'], ['get', 'evidence_level'], 1, 0.3, 5, 1],
                'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 6, 1.2, 10, 2.5, 14, 4],
                'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 6, 25, 10, 35, 14, 50],
                'heatmap-color': [
                    'interpolate', ['linear'], ['heatmap-density'],
                    0, 'rgba(0,0,0,0)',
                    0.1, 'rgba(35,134,54,0.4)',
                    0.25, '#238636',
                    0.45, '#3fb950',
                    0.65, '#d29922',
                    0.8, '#db6d28',
                    1.0, '#f85149',
                ],
                'heatmap-opacity': ['interpolate', ['linear'], ['zoom'], 6, 0.8, 14, 0.6],
            },
        });

        // ── Cluster circles ──
        map.addLayer({
            id: 'clusters',
            type: 'circle',
            source: 'sightings',
            filter: ['has', 'point_count'],
            paint: {
                'circle-color': [
                    'step', ['get', 'point_count'],
                    '#3fb950', 10,
                    '#d29922', 30,
                    '#db6d28', 75,
                    '#f85149',
                ],
                'circle-radius': [
                    'step', ['get', 'point_count'],
                    16, 10,
                    22, 30,
                    28, 75,
                    34,
                ],
                'circle-stroke-width': 2,
                'circle-stroke-color': 'rgba(255,255,255,0.15)',
            },
        });

        // ── Cluster count labels ──
        map.addLayer({
            id: 'cluster-count',
            type: 'symbol',
            source: 'sightings',
            filter: ['has', 'point_count'],
            layout: {
                'text-field': '{point_count_abbreviated}',
                'text-font': ['Open Sans Bold'],
                'text-size': 12,
            },
            paint: {
                'text-color': '#0d1117',
            },
        });

        // ── Individual sighting markers ──
        map.addLayer({
            id: 'sighting-points',
            type: 'circle',
            source: 'sightings',
            filter: ['!', ['has', 'point_count']],
            paint: {
                'circle-color': [
                    'match', ['get', 'cryptid_slug'],
                    ...Object.entries(CRYPTID_COLORS).flat(),
                    '#58a6ff', // default
                ],
                'circle-radius': [
                    'interpolate', ['linear'], ['zoom'],
                    6, 4,
                    12, 7,
                    16, 10,
                ],
                'circle-stroke-width': 1.5,
                'circle-stroke-color': 'rgba(255,255,255,0.3)',
            },
        });
    }

    function _addInteractions() {
        // Click on cluster → zoom in
        map.on('click', 'clusters', (e) => {
            const features = map.queryRenderedFeatures(e.point, { layers: ['clusters'] });
            if (!features.length) return;
            const clusterId = features[0].properties.cluster_id;
            map.getSource('sightings').getClusterExpansionZoom(clusterId, (err, zoom) => {
                if (err) return;
                map.easeTo({
                    center: features[0].geometry.coordinates,
                    zoom: zoom,
                });
            });
        });

        // Click on sighting point → show popup
        map.on('click', 'sighting-points', (e) => {
            if (locationPickerActive) return;
            const feature = e.features[0];
            const props = feature.properties;
            const coords = feature.geometry.coordinates.slice();

            const evidenceLabels = {
                1: 'Rustling Bushes',
                2: 'Strange Sound',
                3: 'Blurry Photo',
                4: 'Clear Photo',
                5: 'Physical Evidence',
            };

            const html = `
                <div class="popup-content">
                    <h3>${_escapeHtml(props.cryptid_name || props.cryptid_slug)}</h3>
                    <div class="popup-meta">
                        <span class="feed-evidence evidence-${props.evidence_level}">${evidenceLabels[props.evidence_level] || 'Unknown'}</span>
                        · ${_formatDate(props.sighting_date || props.sighted_at)}
                    </div>
                    <p class="popup-description">${_escapeHtml(props.description || 'No description provided.')}</p>
                    <div class="popup-meta" style="margin-top:0.3rem">Reported by ${_escapeHtml(props.reporter_name || 'Anonymous')}</div>
                </div>
            `;

            popup.setLngLat(coords).setHTML(html).addTo(map);
            _announce(`${props.cryptid_name || props.cryptid_slug || 'Cryptid'} sighting details opened`);
        });

        // Hover cursors
        map.on('mouseenter', 'clusters', () => { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', 'clusters', () => { map.getCanvas().style.cursor = ''; });
        map.on('mouseenter', 'sighting-points', () => {
            if (!locationPickerActive) map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'sighting-points', () => {
            if (!locationPickerActive) map.getCanvas().style.cursor = '';
        });

        // County hover for tooltip
        map.on('mousemove', 'county-fills', (e) => {
            if (!e.features.length) return;
            const props = e.features[0].properties;
            const threat = props.threat_level || 'none';
            const name = props.name || 'Unknown';
            popup.setLngLat(e.lngLat).setHTML(`
                <div class="popup-content">
                    <h3>${_escapeHtml(name)} County</h3>
                    <div class="popup-meta">Threat: <strong style="color:${THREAT_COLORS[threat] || '#8b949e'}">${threat.toUpperCase()}</strong></div>
                </div>
            `).addTo(map);
        });
        map.on('mouseleave', 'county-fills', () => { popup.remove(); });
    }

    function _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function _formatDate(iso) {
        if (!iso) return '';
        const d = new Date(iso);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }

    // ── Public API ──────────────────────────────────────────

    function setSightingsData(geojson) {
        if (!map || !map.getSource('sightings')) return;
        map.getSource('sightings').setData(geojson);
        const heatSrc = map.getSource('sightings-heat');
        if (heatSrc) heatSrc.setData(geojson);
        _announce(`Map updated with ${geojson.features ? geojson.features.length : 0} sightings`);
    }

    function setCountyData(geojson) {
        if (!map || !map.getSource('counties')) return;
        map.getSource('counties').setData(geojson);
        _announce(`County threat layer updated with ${geojson.features ? geojson.features.length : 0} counties`);
    }

    function toggleLayer(layerName, visible) {
        const layerMap = {
            'threat': ['county-fills', 'county-borders'],
            'markers': ['clusters', 'cluster-count', 'sighting-points'],
            'heatmap': ['sightings-heatmap'],
        };
        const layers = layerMap[layerName] || [];
        layers.forEach((id) => {
            if (map.getLayer(id)) {
                map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none');
            }
        });
    }

    function startLocationPicker(callback) {
        locationPickerActive = true;
        locationPickerCallback = callback;
        document.getElementById('map').classList.add('picking-location');
        _announce('Location picker enabled. Click map to choose sighting location');
    }

    function stopLocationPicker() {
        locationPickerActive = false;
        locationPickerCallback = null;
        document.getElementById('map').classList.remove('picking-location');
    }

    function flyTo(lng, lat, zoom = 13) {
        if (!map) return;
        map.flyTo({ center: [lng, lat], zoom });
    }

    function getMap() {
        return map;
    }

    return {
        init,
        setSightingsData,
        setCountyData,
        toggleLayer,
        startLocationPicker,
        stopLocationPicker,
        flyTo,
        getMap,
        CRYPTID_COLORS,
        THREAT_COLORS,
    };
})();
