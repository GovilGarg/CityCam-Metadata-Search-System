(function() {
    'use strict';

    const SearchApp = {
        elements: {},
        _searchHistory: [],

        init() {
            this.cacheElements();
            this.bindEvents();
            this.checkApiHealth();
        },

        safeToggle(element, className, add = true) {
            if (element && element.classList) {
                if (add) element.classList.add(className);
                else element.classList.remove(className);
            }
        },

        cacheElements() {
            this.elements = {
                searchInput: document.getElementById('searchInput'),
                searchBtn: document.getElementById('searchBtn'),
                resultsSection: document.getElementById('resultsSection'),
                loadingSection: document.getElementById('loadingSection'),
                errorSection: document.getElementById('errorSection'),
                resultCount: document.getElementById('resultCount'),
                warningsContainer: document.getElementById('warningsContainer'),
                warningsList: document.getElementById('warningsList'),
                pathsContainer: document.getElementById('pathsContainer'),
                pathsList: document.getElementById('pathsList'),
                resultsContainer: document.getElementById('resultsContainer'),
                resultsList: document.getElementById('resultsList'),
                noResults: document.getElementById('noResults'),
                errorMessage: document.getElementById('errorMessage'),
                pathModal: document.getElementById('pathModal'),
                modalPathContent: document.getElementById('modalPathContent'),
                closeModal: document.getElementById('closeModal'),
                visualizationSection: document.getElementById('visualizationSection'),
                typeChart: document.getElementById('typeChart'),
                timeChart: document.getElementById('timeChart'),
                hourlyChart: document.getElementById('hourlyChart'),
                statsContainer: document.getElementById('statsContainer'),
                typeEntriesModal: document.getElementById('typeEntriesModal'),
                typeEntriesContent: document.getElementById('typeEntriesContent'),
                historyBtn: document.getElementById('historyBtn'),
                historyModal: document.getElementById('historyModal'),
                historyList: document.getElementById('historyList'),
                clearHistory: document.getElementById('clearHistory'),
                ollamaBtn: document.getElementById('ollamaBtn')
            };
        },

        bindEvents() {
            this.elements.searchBtn.addEventListener('click', () => this.handleSearch());
            this.elements.searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.handleSearch();
            });

            this.elements.closeModal.addEventListener('click', () => this.closeModal());
            this.elements.pathModal.addEventListener('click', (e) => {
                if (e.target === this.elements.pathModal) this.closeModal();
            });

            this.elements.typeEntriesModal.addEventListener('click', (e) => {
                if (e.target === this.elements.typeEntriesModal) {
                    this.elements.typeEntriesModal.classList.remove('active');
                    document.body.style.overflow = '';
                }
            });

            this.elements.historyBtn.addEventListener('click', () => this.showHistory());
            this.elements.historyModal.addEventListener('click', (e) => {
                if (e.target === this.elements.historyModal) {
                    this.elements.historyModal.classList.remove('active');
                }
            });
            this.elements.clearHistory.addEventListener('click', () => this.clearHistory());
            this.elements.ollamaBtn.addEventListener('click', () => this.toggleOllama());
            this.checkOllamaStatus();

            document.addEventListener('click', (e) => {
                const typesCard = document.getElementById('typesStatCard');
                if (typesCard && !typesCard.contains(e.target)) {
                    const tooltip = typesCard.querySelector('.types-tooltip');
                    if (tooltip) {
                        tooltip.style.visibility = 'hidden';
                        tooltip.style.opacity = '0';
                    }
                }
            });

            document.querySelectorAll('.example-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.elements.searchInput.value = btn.dataset.query;
                    this.handleSearch();
                });
            });
        },

        async checkOllamaStatus() {
            try {
                const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.API_ENDPOINTS.OLLAMA}`, {
                    method: 'GET',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                this.updateOllamaIndicator(data.ollama_active);
            } catch (error) {
                this.updateOllamaIndicator(false);
            }
        },

        async toggleOllama() {
            const isActive = this.elements.ollamaBtn.classList.contains('active');
            try {
                const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.API_ENDPOINTS.OLLAMA_TOGGLE}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ active: !isActive })
                });
                const data = await response.json();
                this.updateOllamaIndicator(data.ollama_active);
            } catch (error) {
                console.warn('Failed to toggle Ollama status');
            }
        },

        updateOllamaIndicator(isActive) {
            if (isActive) {
                this.elements.ollamaBtn.classList.add('active');
                this.elements.ollamaBtn.querySelector('.ollama-indicator').style.background = '#34c759';
            } else {
                this.elements.ollamaBtn.classList.remove('active');
                this.elements.ollamaBtn.querySelector('.ollama-indicator').style.background = '#ff3b30';
            }
        },

        async checkApiHealth() {
            try {
                const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.API_ENDPOINTS.HEALTH}`, {
                    method: 'GET',
                    headers: { 'Content-Type': 'application/json' }
                });
                if (!response.ok) throw new Error('API not available');
            } catch (error) {
                console.warn('API server is not running. Please start api_server.py to enable search functionality.');
            }
        },

        showSection(section) {
            this.safeToggle(this.elements.resultsSection, 'hidden', true);
            this.safeToggle(this.elements.loadingSection, 'hidden', true);
            this.safeToggle(this.elements.errorSection, 'hidden', true);

            if (section) {
                this.safeToggle(section, 'hidden', false);
            }
        },

        async handleSearch() {
            const query = this.elements.searchInput.value.trim();

            if (!query) {
                this.showError('Please enter a search query.');
                return;
            }

            this.showSection(this.elements.loadingSection);

            try {
                const response = await this.fetchSearchResults(query);
                this.displayResults(response);
            } catch (error) {
                this.showError(error.message || 'An error occurred while searching.');
            }
        },

        async fetchSearchResults(query) {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT);

            try {
                const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.API_ENDPOINTS.SEARCH}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query }),
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `HTTP error ${response.status}`);
                }

                return await response.json();
            } catch (error) {
                clearTimeout(timeoutId);
                if (error.name === 'AbortError') {
                    throw new Error('Request timed out. Please try again.');
                }
                throw error;
            }
        },

        displayResults(data) {
            this._lastData = data; // Store data for path lookup
            this.addToHistory(this.elements.searchInput.value.trim());
            this.showSection(this.elements.resultsSection);

            if (!data.success) {
                this.displayNoResults();
                if (data.warnings && data.warnings.length > 0) {
                    this.displayWarnings(data.warnings);
                }
                if (data.error) {
                    this.showError(data.error);
                }
                return;
            }

            this.elements.resultCount.textContent = `${data.result_count || 0} Found`;

            if (data.warnings && data.warnings.length > 0) {
                this.displayWarnings(data.warnings);
            } else {
                this.safeToggle(this.elements.warningsContainer, 'hidden', true);
            }

            if (data.results && data.results.length > 0) {
                this.displayResultsList(data.results);
            } else {
                this.displayNoResults();
            }
        },

        displayWarnings(warnings) {
            this.elements.warningsList.innerHTML = '';
            warnings.forEach(warning => {
                const div = document.createElement('div');
                div.className = 'warning-item';
                div.textContent = warning;
                this.elements.warningsList.appendChild(div);
            });
            this.safeToggle(this.elements.warningsContainer, 'hidden', false);
        },

        displayPaths(paths, velocityFlags) {
            this.elements.pathsList.innerHTML = '';
            this.safeToggle(this.elements.pathsContainer, 'hidden', false);

            paths.filter(path => Array.isArray(path?.stages)).forEach(path => {
                const isFlagged = velocityFlags.includes(path.object_id);
                const card = document.createElement('div');
                card.className = 'path-card';
                card.innerHTML = `
                    <div class="path-header">
                        <span class="path-object-id">${path.object_id}</span>
                        <div class="path-flags">
                            ${isFlagged ? '<span class="flag-badge velocity">High Velocity</span>' : ''}
                        </div>
                    </div>
                    <div class="path-journey">${path.journey}</div>
                    <div class="path-stages">
                        ${(path.stages || []).map(stage => `
                            <div class="stage-item ${stage.flagged ? 'flagged' : ''}">
                                <span class="stage-route">${stage.from} → ${stage.to}</span>
                                <span class="stage-velocity ${stage.flagged ? 'flagged' : ''}">${stage.velocity_kmh.toFixed(2)} km/h</span>
                            </div>
                        `).join('')}
                    </div>
                `;
                this.elements.pathsList.appendChild(card);
            });
        },

        displayResultsList(results) {
            this._lastResults = results;
            this.elements.resultsList.innerHTML = '';
            this.elements.resultsContainer.classList.remove('hidden');
            this.elements.noResults.classList.add('hidden');

            results.forEach(result => {
                const card = document.createElement('div');
                card.className = 'result-card';
                card.innerHTML = `
                    <div class="result-item">
                        <span class="label">Object ID</span>
                        <span class="value mono">${result[0]}</span>
                    </div>
                    <div class="result-item">
                        <span class="label">Time</span>
                        <span class="value">${this.formatDateTime(result[1])}</span>
                    </div>
                    <div class="result-item">
                        <span class="label">Location</span>
                        <span class="value">${result[2]}</span>
                    </div>
                    <div class="result-item">
                        <span class="label">Coordinates</span>
                        <span class="value mono coords-value">${parseFloat(result[3]).toFixed(4)}, ${parseFloat(result[4]).toFixed(4)}</span>
                    </div>
                    <div class="result-item">
                        <span class="label">Color</span>
                        <span class="value">${result[5]}</span>
                    </div>
                    <div class="result-item">
                        <span class="label">Type</span>
                        <span class="value">${result[6]}</span>
                    </div>
                    <div class="result-footer">
                        <button class="show-path-btn" data-id="${result[0]}">Show Path</button>
                    </div>
                `;
                
                const showPathBtn = card.querySelector('.show-path-btn');
                showPathBtn.addEventListener('click', () => this.showPath(result[0]));
                
                this.elements.resultsList.appendChild(card);
            });

            this.displayVisualizations(results);
        },

        displayVisualizations(results) {
            this.elements.visualizationSection.classList.remove('hidden');

            const typeCount = {};
            const timeCount = {};
            const hourlyCount = {};

            results.forEach(result => {
                const type = result[6] || 'Unknown';
                const time = new Date(result[1]).getHours();
                const hourSlot = Math.floor(time / 4);

                typeCount[type] = (typeCount[type] || 0) + 1;
                timeCount[time] = (timeCount[time] || 0) + 1;
                hourlyCount[hourSlot] = (hourlyCount[hourSlot] || 0) + 1;
            });

            this.renderBarChart(this.elements.typeChart, typeCount, 'type');
            this.renderTimeChart(this.elements.timeChart, timeCount);
            this.renderBarChart(this.elements.hourlyChart, hourlyCount, 'hourly');
            this.renderStats(results);
        },

        renderBarChart(container, data, chartType) {
            container.innerHTML = '';
            const entries = Object.entries(data).sort((a, b) => b[1] - a[1]).slice(0, 6);
            const maxValue = Math.max(...entries.map(e => e[1]));

            entries.forEach(([label, value]) => {
                const bar = document.createElement('div');
                bar.className = `chart-bar ${chartType}-bar`;
                bar.style.height = `${(value / maxValue) * 180}px`;
                
                let displayLabel = label;
                if (chartType === 'hourly') {
                    const startHour = parseInt(label) * 4;
                    displayLabel = `${startHour}:00`;
                    bar.setAttribute('data-label', displayLabel);
                    bar.setAttribute('data-hour-start', startHour);
                    bar.setAttribute('data-hour-end', startHour + 4);
                } else {
                    bar.setAttribute('data-label', label);
                }
                
                bar.setAttribute('data-value', value);
                bar.innerHTML = `<span class="bar-value">${value}</span>`;
                
                if (chartType === 'type') {
                    bar.style.cursor = 'pointer';
                    bar.addEventListener('click', () => this.showTypeEntries(label));
                } else if (chartType === 'hourly') {
                    bar.style.cursor = 'pointer';
                    bar.addEventListener('click', () => this.showHourlyEntries(startHour));
                }
                
                container.appendChild(bar);
            });
        },

        renderTimeChart(container, data) {
            container.innerHTML = '';
            const hours = [];
            for (let i = 0; i < 24; i++) hours.push(i);
            const maxValue = Math.max(...hours.map(h => data[h] || 0), 1);

            hours.forEach(hour => {
                const value = data[hour] || 0;
                const bar = document.createElement('div');
                bar.className = 'chart-bar time-bar';
                
                const isMajor = hour % 4 === 0;
                if (!isMajor) {
                    bar.classList.add('hide-label');
                }
                
                if (value === 0) {
                    bar.classList.add('hide-value');
                }

                bar.style.height = `${(value / maxValue) * 180}px`;
                bar.setAttribute('data-label', `${hour}:00`);
                bar.setAttribute('data-hour', hour);
                bar.innerHTML = `<span class="bar-value">${value}</span><span class="time-tooltip">${hour}:00 - ${value} sightings</span>`;
                container.appendChild(bar);
            });
        },

        renderStats(results) {
            const types = {};
            let maxTypeCount = 0;
            let topType = 'N/A';

            results.forEach(result => {
                const type = result[6] || 'Unknown';
                types[type] = (types[type] || 0) + 1;
                if (types[type] > maxTypeCount) {
                    maxTypeCount = types[type];
                    topType = type;
                }
            });

            const sortedTypes = Object.entries(types).sort((a, b) => b[1] - a[1]);

            this.elements.statsContainer.innerHTML = `
                <div class="stat-item">
                    <div class="stat-value">${results.length}</div>
                    <div class="stat-label">Total Sightings</div>
                </div>
                <div class="stat-item interactive" id="typesStatCard">
                    <div class="stat-value">${Object.keys(types).length}</div>
                    <div class="stat-label">Types Found</div>
                    <div class="types-tooltip">
                        <h4>Vehicle Breakdown</h4>
                        <div class="tooltip-list">
                            ${sortedTypes.map(([name, count]) => `
                                <div class="tooltip-item">
                                    <span class="type-name">${name}</span>
                                    <span class="type-count">${count}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" style="font-size: 1.4rem;">${topType}</div>
                    <div class="stat-label">Most Frequent</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${sortedTypes[0] ? sortedTypes[0][1] : 0}</div>
                    <div class="stat-label">Top Count</div>
                </div>
            `;

            // Add click toggle for mobile/click users
            const typesCard = document.getElementById('typesStatCard');
            if (typesCard) {
                typesCard.addEventListener('click', (e) => {
                    const tooltip = typesCard.querySelector('.types-tooltip');
                    if (tooltip) {
                        const isVisible = window.getComputedStyle(tooltip).visibility === 'visible';
                        tooltip.style.visibility = isVisible ? 'hidden' : 'visible';
                        tooltip.style.opacity = isVisible ? '0' : '1';
                    }
                    e.stopPropagation();
                });
            }
        },

        showTypeEntries(typeName) {
            const entries = this._lastResults.filter(r => (r[6] || 'Unknown') === typeName);
            
            const entriesHtml = entries.map(entry => `
                <div class="result-item">
                    <div class="result-row">
                        <span class="label">Object ID:</span>
                        <span class="value">${entry[0] || 'N/A'}</span>
                    </div>
                    <div class="result-row">
                        <span class="label">Time:</span>
                        <span class="value">${entry[1] || 'N/A'}</span>
                    </div>
                    <div class="result-row">
                        <span class="label">Location:</span>
                        <span class="value">${entry[2] || 'N/A'}</span>
                    </div>
                    <div class="result-row">
                        <span class="label">Speed:</span>
                        <span class="value">${entry[3] ? entry[3].toFixed(2) + ' km/h' : 'N/A'}</span>
                    </div>
                    <div class="result-row">
                        <span class="label">Direction:</span>
                        <span class="value">${entry[4] || 'N/A'}</span>
                    </div>
                    <div class="result-row">
                        <span class="label">Color:</span>
                        <span class="value">${entry[5] || 'N/A'}</span>
                    </div>
                    <div class="result-row">
                        <span class="label">Type:</span>
                        <span class="value">${entry[6] || 'N/A'}</span>
                    </div>
                </div>
            `).join('');

            this.elements.typeEntriesContent.innerHTML = `
                <div class="type-entries-header">
                    <h3>${typeName} Entries (${entries.length})</h3>
                    <button class="type-entries-close">&times;</button>
                </div>
                <div class="type-entries-list">
                    ${entriesHtml}
                </div>
            `;

            this.elements.typeEntriesModal.classList.add('active');
            document.body.style.overflow = 'hidden';

            const closeBtn = this.elements.typeEntriesModal.querySelector('.type-entries-close');
            closeBtn.addEventListener('click', () => {
                this.elements.typeEntriesModal.classList.remove('active');
                document.body.style.overflow = '';
            });
        },

        showHourlyEntries(startHour) {
            const endHour = startHour + 4;
            const entries = this._lastResults.filter(r => {
                const hour = new Date(r[1]).getHours();
                return hour >= startHour && hour < endHour;
            });
            
            const entriesHtml = entries.map(entry => `
                <div class="result-item">
                    <div class="result-row">
                        <span class="label">Object ID:</span>
                        <span class="value">${entry[0] || 'N/A'}</span>
                    </div>
                    <div class="result-row">
                        <span class="label">Time:</span>
                        <span class="value">${entry[1] || 'N/A'}</span>
                    </div>
                    <div class="result-row">
                        <span class="label">Location:</span>
                        <span class="value">${entry[2] || 'N/A'}</span>
                    </div>
                    <div class="result-row">
                        <span class="label">Speed:</span>
                        <span class="value">${entry[3] ? entry[3].toFixed(2) + ' km/h' : 'N/A'}</span>
                    </div>
                    <div class="result-row">
                        <span class="label">Direction:</span>
                        <span class="value">${entry[4] || 'N/A'}</span>
                    </div>
                    <div class="result-row">
                        <span class="label">Color:</span>
                        <span class="value">${entry[5] || 'N/A'}</span>
                    </div>
                    <div class="result-row">
                        <span class="label">Type:</span>
                        <span class="value">${entry[6] || 'N/A'}</span>
                    </div>
                </div>
            `).join('');

            this.elements.typeEntriesContent.innerHTML = `
                <div class="type-entries-header">
                    <h3>${startHour}:00 - ${endHour}:00 (${entries.length})</h3>
                    <button class="type-entries-close">&times;</button>
                </div>
                <div class="type-entries-list">
                    ${entriesHtml}
                </div>
            `;

            this.elements.typeEntriesModal.classList.add('active');
            document.body.style.overflow = 'hidden';

            const closeBtn = this.elements.typeEntriesModal.querySelector('.type-entries-close');
            closeBtn.addEventListener('click', () => {
                this.elements.typeEntriesModal.classList.remove('active');
                document.body.style.overflow = '';
            });
        },

        addToHistory(query) {
            if (!query) return;
            this._searchHistory = this._searchHistory.filter(q => q.toLowerCase() !== query.toLowerCase());
            this._searchHistory.unshift(query);
            if (this._searchHistory.length > 20) {
                this._searchHistory = this._searchHistory.slice(0, 20);
            }
        },

        showHistory() {
            const historyHtml = this._searchHistory.length === 0 
                ? '<p class="no-history">No search history yet</p>'
                : this._searchHistory.map((query, index) => `
                    <div class="history-item" data-index="${index}">
                        <span class="history-query">${query}</span>
                        <button class="history-remove" data-index="${index}">&times;</button>
                    </div>
                `).join('');
            
            this.elements.historyList.innerHTML = historyHtml;
            this.elements.historyModal.classList.add('active');

            this.elements.historyList.querySelectorAll('.history-item').forEach(item => {
                item.addEventListener('click', (e) => {
                    if (!e.target.classList.contains('history-remove')) {
                        const query = item.querySelector('.history-query').textContent;
                        this.elements.searchInput.value = query;
                        this.elements.historyModal.classList.remove('active');
                        this.handleSearch();
                    }
                });
            });

            this.elements.historyList.querySelectorAll('.history-remove').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const index = parseInt(btn.dataset.index);
                    this._searchHistory.splice(index, 1);
                    this.showHistory();
                });
            });
        },

        clearHistory() {
            this._searchHistory = [];
            this.elements.historyList.innerHTML = '<p class="no-history">No search history yet</p>';
        },

        showPath(objectId) {
            this.elements.visualizationSection.classList.add('hidden');
            if (!this._lastData || !this._lastData.paths) return;
            
            const path = this._lastData.paths.find(p => p.object_id === objectId);
            const velocityFlags = this._lastData.velocity_flags || [];
            
            if (!path) {
                alert(`No path data found for ${objectId}`);
                return;
            }

            const isFlagged = velocityFlags.includes(path.object_id);
            
            this.elements.modalPathContent.innerHTML = `
                <div class="path-card" style="background: transparent; border: none; padding: 0;">
                    <div class="path-header">
                        <span class="path-object-id" style="font-size: 1.5rem;">${path.object_id}</span>
                        <div class="path-flags">
                            ${isFlagged ? '<span class="flag-badge velocity">High Velocity</span>' : ''}
                        </div>
                    </div>
                    <div class="path-journey" style="font-size: 1.1rem; margin-bottom: 20px;">${path.journey}</div>
                    <div class="path-stages">
                        ${(path.stages || []).map(stage => `
                            <div class="stage-item ${stage.flagged ? 'flagged' : ''}">
                                <span class="stage-route">${stage.from} → ${stage.to}</span>
                                <span class="stage-velocity ${stage.flagged ? 'flagged' : ''}">${stage.velocity_kmh.toFixed(2)} km/h</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            
            this.elements.pathModal.classList.add('active');
            document.body.style.overflow = 'hidden'; // Prevent scroll
        },

        closeModal() {
            this.elements.pathModal.classList.remove('active');
            document.body.style.overflow = ''; // Restore scroll
        },

        formatDateTime(dateValue) {
            if (!dateValue) return 'N/A';
            const date = dateValue instanceof String ? new Date(dateValue) : new Date(dateValue);
            return date.toLocaleString();
        },

        displayNoResults() {
            this.safeToggle(this.elements.resultsContainer, 'hidden', true);
            this.safeToggle(this.elements.pathsContainer, 'hidden', true);
            if (this.elements.noResults) {
                this.safeToggle(this.elements.noResults, 'hidden', false);
                // Ensure it's visible if the parent section is hidden
                this.safeToggle(this.elements.resultsSection, 'hidden', false);
            }
            if (this.elements.resultCount) this.elements.resultCount.textContent = '0 Found';
        },

        showError(message) {
            this.showSection(this.elements.errorSection);
            // Check if this is actually a "no results" case or a real error
            if (message && (message.toLowerCase().includes('no matches') || message.toLowerCase().includes('data not found'))) {
                this.displayNoResults();
                return;
            }
            this.elements.errorMessage.textContent = message;
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        SearchApp.init();
    });

    window.SearchApp = SearchApp;
})();
