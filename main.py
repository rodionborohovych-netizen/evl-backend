<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EVL v10.1 - Professional Site Analysis with Data Quality Tracking</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 min-h-screen">
    <div class="container mx-auto px-4 py-6">
        <!-- Header -->
        <div class="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg shadow-xl p-6 mb-6 text-white">
            <h1 class="text-4xl font-bold mb-2">⚡ EVL v10.1 Professional</h1>
            <p class="text-blue-100">Production-Grade Data Quality • Real API Tracking • 15+ Data Sources • Real-Time Intelligence</p>
        </div>

        <!-- Input Form -->
        <div class="bg-white rounded-lg shadow-xl p-6 mb-6">
            <h2 class="text-2xl font-bold text-gray-800 mb-4">🎯 Analysis Configuration</h2>
            
            <div class="grid md:grid-cols-2 gap-6">
                <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-2">📍 Location</label>
                    <input type="text" id="address" placeholder="London, Manchester, Birmingham..." value="London"
                        class="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none" />
                </div>
                <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-2">🌍 Country</label>
                    <select id="country" class="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none">
                        <option value="UK">United Kingdom</option>
                        <option value="DE">Germany</option>
                        <option value="FR">France</option>
                        <option value="PL">Poland</option>
                        <option value="NL">Netherlands</option>
                        <option value="NO">Norway</option>
                        <option value="UA">Ukraine</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-2">📏 Radius (km)</label>
                    <input type="number" id="radius" value="5" min="1" max="20"
                        class="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none" />
                </div>
                <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-2">⚡ Power per Plug (kW)</label>
                    <select id="power" class="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none">
                        <option value="7">7 kW - Home/Workplace AC</option>
                        <option value="22">22 kW - Fast AC</option>
                        <option value="50" selected>50 kW - DC Fast</option>
                        <option value="150">150 kW - Ultra-Rapid DC</option>
                        <option value="350">350 kW - Ultra-Fast DC</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-2">🔌 Number of Plugs</label>
                    <input type="number" id="plugs" value="2" min="1" max="20"
                        class="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none" />
                </div>
            </div>

            <!-- Facility Selection -->
            <div class="mt-6">
                <label class="block text-sm font-semibold text-gray-700 mb-3">🏪 Site Facilities</label>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <label class="flex items-center space-x-2 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-400 transition">
                        <input type="checkbox" class="facility-checkbox w-5 h-5" value="grocery" />
                        <span class="text-sm font-medium">🛒 Grocery</span>
                    </label>
                    <label class="flex items-center space-x-2 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-400 transition">
                        <input type="checkbox" class="facility-checkbox w-5 h-5" value="restaurant" />
                        <span class="text-sm font-medium">🍽️ Restaurant</span>
                    </label>
                    <label class="flex items-center space-x-2 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-400 transition">
                        <input type="checkbox" class="facility-checkbox w-5 h-5" value="shopping_mall" />
                        <span class="text-sm font-medium">🏬 Mall</span>
                    </label>
                    <label class="flex items-center space-x-2 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-400 transition">
                        <input type="checkbox" class="facility-checkbox w-5 h-5" value="coffee" />
                        <span class="text-sm font-medium">☕ Coffee</span>
                    </label>
                    <label class="flex items-center space-x-2 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-400 transition">
                        <input type="checkbox" class="facility-checkbox w-5 h-5" value="gym" />
                        <span class="text-sm font-medium">💪 Gym</span>
                    </label>
                    <label class="flex items-center space-x-2 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-400 transition">
                        <input type="checkbox" class="facility-checkbox w-5 h-5" value="hotel" />
                        <span class="text-sm font-medium">🏨 Hotel</span>
                    </label>
                    <label class="flex items-center space-x-2 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-400 transition">
                        <input type="checkbox" class="facility-checkbox w-5 h-5" value="workplace" />
                        <span class="text-sm font-medium">🏢 Office</span>
                    </label>
                    <label class="flex items-center space-x-2 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-400 transition">
                        <input type="checkbox" class="facility-checkbox w-5 h-5" value="cinema" />
                        <span class="text-sm font-medium">🎬 Cinema</span>
                    </label>
                </div>
            </div>

            <button onclick="analyzeLocation()"
                class="mt-6 w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-4 rounded-lg font-bold text-lg hover:from-blue-700 hover:to-indigo-700 transition shadow-lg">
                🚀 Run Comprehensive Analysis
            </button>
        </div>

        <div id="loading" class="hidden bg-white rounded-lg shadow-xl p-8 text-center">
            <div class="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-4"></div>
            <p class="text-gray-600 text-lg font-semibold">Analyzing 15+ Data Sources...</p>
            <p class="text-sm text-gray-500 mt-2">OSM • Traffic • Grid • EV Market • Competition • Demographics</p>
        </div>

        <div id="results" class="hidden">
            <!-- Data Quality Indicator -->
            <div id="data-quality" class="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200 rounded-lg p-4 mb-6">
                <div class="flex items-center justify-between">
                    <div>
                        <h3 class="font-bold text-green-800">📊 Data Quality</h3>
                        <p class="text-sm text-green-700" id="data-quality-text">Loading...</p>
                    </div>
                    <div class="text-3xl font-bold text-green-600" id="data-quality-score">-</div>
                </div>
            </div>

            <!-- NEW: Data Quality Monitor (v10.1) -->
            <div class="bg-white rounded-lg shadow-xl p-6 mb-6">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-xl font-bold text-gray-800">🎯 Data Quality Monitor</h3>
                    <span class="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-semibold">v10.1 NEW</span>
                </div>
                <p class="text-sm text-gray-600 mb-4">Real-time quality tracking for all data sources</p>
                <div id="quality-monitor" class="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <!-- Quality cards will be inserted here -->
                </div>
            </div>

            <!-- Comprehensive Scores -->
            <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 mb-6">
                <div class="bg-white rounded-lg shadow-lg p-4 text-center">
                    <p class="text-xs text-gray-600 mb-1">Overall</p>
                    <p class="text-3xl font-bold" id="score-overall">-</p>
                </div>
                <div class="bg-white rounded-lg shadow-lg p-4 text-center">
                    <p class="text-xs text-gray-600 mb-1">Traffic</p>
                    <p class="text-3xl font-bold" id="score-traffic">-</p>
                </div>
                <div class="bg-white rounded-lg shadow-lg p-4 text-center">
                    <p class="text-xs text-gray-600 mb-1">Demand</p>
                    <p class="text-3xl font-bold" id="score-demand">-</p>
                </div>
                <div class="bg-white rounded-lg shadow-lg p-4 text-center">
                    <p class="text-xs text-gray-600 mb-1">EV Market</p>
                    <p class="text-3xl font-bold" id="score-ev-market">-</p>
                </div>
                <div class="bg-white rounded-lg shadow-lg p-4 text-center">
                    <p class="text-xs text-gray-600 mb-1">Grid</p>
                    <p class="text-3xl font-bold" id="score-grid">-</p>
                </div>
                <div class="bg-white rounded-lg shadow-lg p-4 text-center">
                    <p class="text-xs text-gray-600 mb-1">Competition</p>
                    <p class="text-3xl font-bold" id="score-competition">-</p>
                </div>
                <div class="bg-white rounded-lg shadow-lg p-4 text-center">
                    <p class="text-xs text-gray-600 mb-1">Parking</p>
                    <p class="text-3xl font-bold" id="score-parking">-</p>
                </div>
                <div class="bg-white rounded-lg shadow-lg p-4 text-center">
                    <p class="text-xs text-gray-600 mb-1">Facility</p>
                    <p class="text-3xl font-bold" id="score-facility">-</p>
                </div>
            </div>

            <!-- Key Insights Grid -->
            <div class="grid md:grid-cols-3 gap-6 mb-6">
                <!-- Traffic & Accessibility -->
                <div class="bg-white rounded-lg shadow-xl p-6">
                    <h3 class="text-xl font-bold text-gray-800 mb-4">🚗 Traffic & Access</h3>
                    <div id="traffic-insights" class="space-y-3"></div>
                </div>

                <!-- Grid & Infrastructure -->
                <div class="bg-white rounded-lg shadow-xl p-6">
                    <h3 class="text-xl font-bold text-gray-800 mb-4">⚡ Grid & Power</h3>
                    <div id="grid-insights" class="space-y-3"></div>
                </div>

                <!-- Competition -->
                <div class="bg-white rounded-lg shadow-xl p-6">
                    <h3 class="text-xl font-bold text-gray-800 mb-4">🔍 Competition</h3>
                    <div id="competition-insights" class="space-y-3"></div>
                </div>
            </div>

            <!-- Recommendations -->
            <div class="bg-white rounded-lg shadow-xl p-6 mb-6">
                <h2 class="text-2xl font-bold text-gray-800 mb-4">💡 Professional Recommendations</h2>
                <div id="recommendations" class="space-y-3"></div>
            </div>

            <!-- Data Sources Used -->
            <div class="bg-gray-50 rounded-lg shadow-lg p-6 mb-6">
                <h3 class="text-xl font-bold text-gray-800 mb-4">📡 Data Sources</h3>
                <div id="data-sources" class="grid md:grid-cols-3 gap-4"></div>
            </div>

            <!-- Nearby Chargers -->
            <div class="bg-white rounded-lg shadow-xl p-6">
                <h2 class="text-2xl font-bold text-gray-800 mb-4">🗺️ Competition Map (Smart Sorted)</h2>
                <div id="chargers" class="grid md:grid-cols-3 gap-4"></div>
            </div>
        </div>
    </div>

    <script>
        // ✅ FIXED: Configurable API URL - connected to Railway backend
        const API_URL = window.location.hostname === 'localhost' 
            ? 'http://localhost:8000'
            : 'https://web-production-e0c85.up.railway.app'; // Your Railway backend

        function getScoreColor(score) {
            if (score >= 0.8) return 'text-green-600';
            if (score >= 0.6) return 'text-yellow-600';
            return 'text-red-600';
        }

        function getQualityColor(score) {
            if (score >= 0.9) return 'bg-green-50 border-green-300 text-green-800';
            if (score >= 0.7) return 'bg-blue-50 border-blue-300 text-blue-800';
            if (score >= 0.5) return 'bg-yellow-50 border-yellow-300 text-yellow-800';
            return 'bg-red-50 border-red-300 text-red-800';
        }

        function getQualityBadge(score) {
            if (score >= 0.9) return '🟢 Excellent';
            if (score >= 0.7) return '🟡 Good';
            if (score >= 0.5) return '🟠 Fair';
            return '🔴 Poor';
        }

        function displayQualityMonitor(comprehensiveData) {
            const monitorDiv = document.getElementById('quality-monitor');
            monitorDiv.innerHTML = '';

            // Sources to track (matching backend decorators)
            const sources = [
                { key: 'entsoe_grid', name: 'ENTSO-E Grid', icon: '⚡' },
                { key: 'national_grid_eso', name: 'National Grid ESO', icon: '🔌' },
                { key: 'vehicle_licensing', name: 'DfT Vehicle Licensing', icon: '🚗' },
                { key: 'ons_demographics', name: 'ONS Demographics', icon: '👥' },
                { key: 'competition', name: 'OpenChargeMap', icon: '🔍' },
                { key: 'traffic', name: 'DfT Traffic', icon: '🚦' }
            ];

            sources.forEach(source => {
                const data = comprehensiveData[source.key];
                
                if (data && data._metadata && data._validation) {
                    const metadata = data._metadata;
                    const validation = data._validation;
                    const qualityScore = validation.quality_score || 0;
                    
                    const card = document.createElement('div');
                    card.className = `border-2 rounded-lg p-4 ${getQualityColor(qualityScore)}`;
                    card.innerHTML = `
                        <div class="flex items-start justify-between mb-2">
                            <div>
                                <p class="font-bold text-sm">${source.icon} ${source.name}</p>
                                <p class="text-xs opacity-75">${metadata.source_id || 'N/A'}</p>
                            </div>
                            <div class="text-right">
                                <p class="text-2xl font-bold">${(qualityScore * 100).toFixed(0)}%</p>
                                <p class="text-xs">${getQualityBadge(qualityScore)}</p>
                            </div>
                        </div>
                        <div class="space-y-1 text-xs">
                            <div class="flex justify-between">
                                <span class="opacity-75">Response Time:</span>
                                <span class="font-semibold">${metadata.response_time_ms ? metadata.response_time_ms.toFixed(0) : 'N/A'}ms</span>
                            </div>
                            <div class="flex justify-between">
                                <span class="opacity-75">Status:</span>
                                <span class="font-semibold">${validation.is_valid ? '✅ Valid' : '❌ Issues'}</span>
                            </div>
                            ${validation.error_count > 0 ? `
                            <div class="flex justify-between">
                                <span class="opacity-75">Errors:</span>
                                <span class="font-semibold text-red-600">${validation.error_count}</span>
                            </div>
                            ` : ''}
                            ${metadata.fetched_at ? `
                            <div class="mt-2 pt-2 border-t border-current opacity-50">
                                <span class="text-xs">Updated: ${new Date(metadata.fetched_at).toLocaleTimeString()}</span>
                            </div>
                            ` : ''}
                        </div>
                    `;
                    monitorDiv.appendChild(card);
                } else if (data && data.available) {
                    // Show basic card for sources without quality tracking
                    const card = document.createElement('div');
                    card.className = 'border-2 rounded-lg p-4 bg-gray-50 border-gray-300 text-gray-700';
                    card.innerHTML = `
                        <div class="flex items-start justify-between mb-2">
                            <div>
                                <p class="font-bold text-sm">${source.icon} ${source.name}</p>
                                <p class="text-xs opacity-75">Legacy tracking</p>
                            </div>
                            <p class="text-xs bg-gray-200 px-2 py-1 rounded">No metrics</p>
                        </div>
                        <p class="text-xs">✓ Available</p>
                    `;
                    monitorDiv.appendChild(card);
                }
            });

            // If no sources with quality data found, show message
            if (monitorDiv.children.length === 0) {
                monitorDiv.innerHTML = `
                    <div class="col-span-full text-center py-8 text-gray-500">
                        <p class="text-sm">No quality tracking data available yet.</p>
                        <p class="text-xs mt-1">Make sure backend v10.1 with foundation package is running.</p>
                    </div>
                `;
            }
        }

        function getSelectedFacilities() {
            const checkboxes = document.querySelectorAll('.facility-checkbox:checked');
            return Array.from(checkboxes).map(cb => cb.value);
        }

        async function analyzeLocation() {
            const address = document.getElementById('address').value;
            const country = document.getElementById('country').value;
            const radius = document.getElementById('radius').value;
            const power = document.getElementById('power').value;
            const plugs = document.getElementById('plugs').value;
            const facilities = getSelectedFacilities().join(',');

            document.getElementById('results').classList.add('hidden');
            document.getElementById('loading').classList.remove('hidden');

            try {
                const response = await fetch(
                    `${API_URL}/api/analyze?address=${encodeURIComponent(address)}&country_code=${country}&radius=${radius}&power_per_plug=${power}&num_plugs=${plugs}&facilities=${encodeURIComponent(facilities)}`
                );
                
                if (!response.ok) {
                    throw new Error(`API error: ${response.status}`);
                }
                
                const data = await response.json();
                displayResults(data);
            } catch (error) {
                alert('Error: ' + error.message + '\n\nMake sure your backend is running and the API_URL is correct!');
                console.error(error);
            }
            
            document.getElementById('loading').classList.add('hidden');
        }

        function displayResults(data) {
            document.getElementById('results').classList.remove('hidden');

            // Data Quality - ✅ FIXED: matches v9.0 structure
            const quality = data.data_quality;
            document.getElementById('data-quality-score').textContent = quality.data_coverage + '%';
            document.getElementById('data-quality-text').textContent = 
                `${quality.sources_active}/${quality.sources_available} data sources active`;

            // NEW: Display Quality Monitor (v10.1)
            if (data.comprehensive_data) {
                displayQualityMonitor(data.comprehensive_data);
            }

            // Scores - ✅ FIXED: matches v9.0 structure
            const scores = data.scores;
            document.getElementById('score-overall').textContent = scores.overall.toFixed(2);
            document.getElementById('score-overall').className = `text-3xl font-bold ${getScoreColor(scores.overall)}`;
            document.getElementById('score-traffic').textContent = scores.traffic_accessibility.toFixed(2);
            document.getElementById('score-traffic').className = `text-3xl font-bold ${getScoreColor(scores.traffic_accessibility)}`;
            document.getElementById('score-demand').textContent = scores.demand.toFixed(2);
            document.getElementById('score-demand').className = `text-3xl font-bold ${getScoreColor(scores.demand)}`;
            document.getElementById('score-ev-market').textContent = scores.ev_market_maturity.toFixed(2);
            document.getElementById('score-ev-market').className = `text-3xl font-bold ${getScoreColor(scores.ev_market_maturity)}`;
            document.getElementById('score-grid').textContent = scores.grid_readiness.toFixed(2);
            document.getElementById('score-grid').className = `text-3xl font-bold ${getScoreColor(scores.grid_readiness)}`;
            document.getElementById('score-competition').textContent = scores.competition.toFixed(2);
            document.getElementById('score-competition').className = `text-3xl font-bold ${getScoreColor(scores.competition)}`;
            document.getElementById('score-parking').textContent = scores.parking_access.toFixed(2);
            document.getElementById('score-parking').className = `text-3xl font-bold ${getScoreColor(scores.parking_access)}`;
            document.getElementById('score-facility').textContent = scores.facility_popularity.toFixed(2);
            document.getElementById('score-facility').className = `text-3xl font-bold ${getScoreColor(scores.facility_popularity)}`;

            // Traffic Insights - ✅ FIXED: matches v9.0 structure
            const trafficDiv = document.getElementById('traffic-insights');
            trafficDiv.innerHTML = '';
            
            const traffic = data.comprehensive_data.traffic; // ✅ Changed from traffic_accessibility
            if (traffic && traffic.available) {
                trafficDiv.innerHTML += `
                    <div class="bg-blue-50 p-3 rounded">
                        <p class="font-bold text-blue-800">Real Traffic Data</p>
                        <p class="text-sm">${traffic.aadt.toLocaleString()} vehicles/day</p>
                        <p class="text-xs text-gray-600">${traffic.road_name}</p>
                    </div>
                `;
            }
            
            const osm = data.comprehensive_data.osm_comprehensive;
            if (osm && osm.roads) {
                trafficDiv.innerHTML += `
                    <div class="bg-gray-50 p-3 rounded">
                        <p class="font-bold">Road Type</p>
                        <p class="text-sm">${osm.roads.type}</p>
                        <p class="text-xs text-gray-600">${osm.roads.nearest.name}</p>
                    </div>
                `;
            }

            // Grid Insights - ✅ FIXED: matches v9.0 structure
            const gridDiv = document.getElementById('grid-insights');
            gridDiv.innerHTML = '';
            
            if (osm && osm.grid) {
                const grid = osm.grid; // ✅ Changed path
                if (grid.nearest) {
                    gridDiv.innerHTML = `
                        <div class="bg-yellow-50 p-3 rounded">
                            <p class="font-bold text-yellow-800">Nearest Substation</p>
                            <p class="text-sm">${grid.nearest.distance_km.toFixed(1)} km away</p>
                            <p class="text-xs text-gray-600">${grid.nearest.voltage}</p>
                        </div>
                        <div class="bg-green-50 p-3 rounded">
                            <p class="font-bold text-green-800">Est. Connection Cost</p>
                            <p class="text-sm">£${grid.estimated_connection_cost.toLocaleString()}</p>
                        </div>
                    `;
                }
            }

            // Competition Insights - ✅ FIXED: matches v9.0 structure
            const compDiv = document.getElementById('competition-insights');
            compDiv.innerHTML = '';
            
            const comp = data.comprehensive_data.competition; // ✅ Changed path
            if (comp) {
                compDiv.innerHTML = `
                    <div class="bg-purple-50 p-3 rounded">
                        <p class="font-bold text-purple-800">Total Chargers</p>
                        <p class="text-sm">${comp.total_chargers} stations</p>
                    </div>
                    <div class="bg-indigo-50 p-3 rounded">
                        <p class="font-bold text-indigo-800">Networks</p>
                        <p class="text-sm">${comp.network_diversity} operators</p>
                    </div>
                    <div class="bg-pink-50 p-3 rounded">
                        <p class="font-bold text-pink-800">Operational</p>
                        <p class="text-sm">${comp.operational_chargers} active</p>
                    </div>
                `;
            }

            // Recommendations
            const recsDiv = document.getElementById('recommendations');
            recsDiv.innerHTML = '';
            data.recommendations.forEach(rec => {
                const div = document.createElement('div');
                const isWarning = rec.type === 'warning';
                const isInfo = rec.type === 'info';
                div.className = isWarning 
                    ? 'bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded'
                    : isInfo
                    ? 'bg-blue-50 border-l-4 border-blue-500 p-4 rounded'
                    : 'bg-green-50 border-l-4 border-green-500 p-4 rounded';
                div.textContent = rec.text;
                recsDiv.appendChild(div);
            });

            // Data Sources - ✅ FIXED: uses actual data from API
            const sourcesDiv = document.getElementById('data-sources');
            sourcesDiv.innerHTML = '';
            
            quality.all_sources.forEach(sourceName => {
                const div = document.createElement('div');
                div.className = 'bg-green-100 border border-green-300 rounded-lg p-3';
                div.innerHTML = `
                    <p class="font-semibold text-sm text-green-800">
                        ✓ ${sourceName}
                    </p>
                `;
                sourcesDiv.appendChild(div);
            });

            // Chargers
            const chargersDiv = document.getElementById('chargers');
            chargersDiv.innerHTML = '';
            data.chargers.slice(0, 12).forEach((charger, index) => {
                const div = document.createElement('div');
                div.className = 'border-2 border-gray-200 rounded-lg p-4 hover:border-blue-400 transition';
                div.innerHTML = `
                    <h4 class="font-bold text-sm mb-2">${charger.name}</h4>
                    <div class="space-y-1 text-xs">
                        <p>📍 ${charger.distance_km} km away</p>
                        <p>⚡ ${charger.power_kw} kW • ${charger.connectors} plugs</p>
                        <p>🏢 ${charger.network}</p>
                        ${index < 3 ? '<span class="inline-block bg-green-100 text-green-800 px-2 py-1 rounded text-xs font-semibold mt-2">Top Match</span>' : ''}
                    </div>
                `;
                chargersDiv.appendChild(div);
            });
        }
    </script>
</body>
</html>
