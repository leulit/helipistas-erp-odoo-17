/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ReportDialog } from "../report_dialog/report_dialog";
import { ReportVisualization } from "../report_visualization/report_visualization";

/**
 * AI Universal Search Page Component
 */
export class SearchPage extends Component {
    static props = {};
    static components = { ReportVisualization };

    setup() {
        this.state = useState({
            query: '',
            loading: false,
            results: null,
            vertexAnswer: null,
            error: null,
            activeTab: 'search', // search, reports, saved
            favorites: [],
            favoritesLoading: false,
            savingFavorite: false,
            currentSearchSaved: false,
            reports: [],
            reportsLoading: false,
            creatingReport: false,
            selectedReport: null
        });

        // Initialize services
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");

        // Load favorites when component is initialized
        this.loadFavorites();

        console.log("AI Universal Search Page initialized");
    }

    onKeyup(ev) {
        if (ev.key === "Enter") {
            this.onSearch();
        }
    }

    onSearch() {
        console.log("Search initiated");
        const query = this.state.query.trim();

        if (!query || this.state.loading) {
            return;
        }

        // Reset state
        this.state.loading = true;
        this.state.results = null;
        this.state.vertexAnswer = null;
        this.state.error = null;

        // Reset "saved" flag when doing a new search
        this.state.currentSearchSaved = false;

        // Call the API
        fetch('/leulit_ia/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': odoo.csrf_token,
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    query_text: query
                },
                id: Math.floor(Math.random() * 1000000)
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                this._displayError(data.error.data?.message || data.error.message || "Error processing search");
                return;
            }

            if (!data.result) {
                this._displayError("No valid response received from the server");
                return;
            }

            // Extract the actual result data
            let resultData;
            if (data.result.status === 'success' && data.result.result) {
                resultData = data.result.result;
            } else {
                resultData = data.result;
            }

            // Store results for display
            this.state.vertexAnswer = resultData.answer || null;
            this.state.results = resultData;
        })
        .catch(error => {
            this._displayError(error.toString ? error.toString() : "Unknown error occurred");
        })
        .finally(() => {
            this.state.loading = false;
        });
    }

    saveCurrentSearch() {
        if (!this.state.query || this.state.savingFavorite) {
            return;
        }

        this.state.savingFavorite = true;

        fetch('/leulit_ia/save_favorite', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': odoo.csrf_token,
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    query_text: this.state.query
                },
                id: Math.floor(Math.random() * 1000000)
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error("Error saving favorite:", data.error);
                return;
            }

            // Mark current search as saved
            this.state.currentSearchSaved = true;

            // Refresh favorites list
            this.loadFavorites();
        })
        .catch(error => {
            console.error("Error saving favorite:", error);
        })
        .finally(() => {
            this.state.savingFavorite = false;
        });
    }

    loadFavorites() {
        this.state.favoritesLoading = true;

        fetch('/leulit_ia/get_favorites', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': odoo.csrf_token,
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {},
                id: Math.floor(Math.random() * 1000000)
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error("Error loading favorites:", data.error);
                return;
            }

            if (data.result && data.result.status === 'success' && data.result.result) {
                this.state.favorites = data.result.result;
            } else {
                this.state.favorites = [];
            }
        })
        .catch(error => {
            console.error("Error loading favorites:", error);
            this.state.favorites = [];
        })
        .finally(() => {
            this.state.favoritesLoading = false;
        });
    }

    executeFavorite(queryText) {
        this.state.query = queryText;
        this.onSearch();
        this.setActiveTab('search'); // Switch to search tab
    }

    deleteFavorite(favoriteId) {
        // No need for event handling now

        fetch('/leulit_ia/delete_favorite', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': odoo.csrf_token,
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    favorite_id: favoriteId
                },
                id: Math.floor(Math.random() * 1000000)
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error("Error deleting favorite:", data.error);
                return;
            }

            // Refresh favorites list
            this.loadFavorites();
        })
        .catch(error => {
            console.error("Error deleting favorite:", error);
        });
    }

    _displayError(error) {
        const errorMsg = typeof error === 'string' ? error : "An error occurred while processing your search.";
        this.state.error = errorMsg;
    }

    /**
     * Generate a mailto link for error reporting
     * @returns {string} mailto link URL
     */
    generateMailtoLink() {
        if (!this.state.error) return '';

        // Get current date and time for the report
        const timestamp = new Date().toISOString();

        // Create subject line
        const subject = encodeURIComponent("AI Universal Search Error Report");

        // Compose email body with error details, query, and timestamp
        let body = "Error Details:\n";
        body += `${this.state.error}\n\n`;
        body += "Query:\n";
        body += `${this.state.query || "No query"}\n\n`;
        body += "Timestamp:\n";
        body += timestamp;

        // URL encode the body text
        const encodedBody = encodeURIComponent(body);

        // Create the mailto link
        return `mailto:tuki@hdsoft.fi?subject=${subject}&body=${encodedBody}`;
    }

    setActiveTab(tab) {
        this.state.activeTab = tab;

        // Load favorites when switching to saved tab
        if (tab === 'saved') {
            this.loadFavorites();
        }

        // Load reports when switching to reports tab
        if (tab === 'reports') {
            this.loadReports();
        }

        // Reset selected report when switching away from reports
        if (tab !== 'reports') {
            this.state.selectedReport = null;
        }
    }

    get isSearchTabActive() {
        return this.state.activeTab === 'search';
    }

    get isReportsTabActive() {
        return this.state.activeTab === 'reports';
    }

    get isSavedTabActive() {
        return this.state.activeTab === 'saved';
    }

    /**
     * Open the report creation dialog
     */
    createReport() {
        if (!this.state.results) {
            return;
        }

        // Open dialog - dialogService passes the close function to the dialog component
        this.dialogService.add(ReportDialog, {
            queryText: this.state.query,
            searchResults: this.state.results,
            onConfirm: this.saveReport.bind(this)
        });
    }

    /**
     * Save a new report
     * @param {Object} reportData Data from the report dialog
     */
    saveReport(reportData) {
        this.state.creatingReport = true;

        // Verify data before sending
        if (!reportData.name || !reportData.query_text) {
            this.notificationService.add("Missing required fields in report data", {
                type: 'danger',
                title: 'Error Creating Report',
                sticky: true
            });
            this.state.creatingReport = false;
            return;
        }

        console.log("Report data being sent:", reportData);

        // Convert to simple values to avoid Proxy objects
        const dataToSend = {
            name: String(reportData.name), // Convert to string explicitly
            query_text: String(reportData.query_text), // Convert to string explicitly
            visualization_type: String(reportData.visualization_type || 'bar'),
            config: JSON.parse(JSON.stringify(reportData.config || {})), // Deep clone to remove proxies
            data: JSON.parse(JSON.stringify(reportData.data || {}))  // Deep clone to remove proxies
        };

        console.log("Final data being sent:", dataToSend);

        // Create a simple string-based JSONRPC payload to avoid any issues with proxy objects
        const payload = JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            params: dataToSend,
            id: Math.floor(Math.random() * 1000000)
        });

        console.log("Raw payload:", payload);

        fetch('/leulit_ia/create_report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': odoo.csrf_token,
            },
            body: payload
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error("Error saving report:", data.error);
                return;
            }

            // Check result status for errors
            if (data.result && data.result.status === 'error') {
                console.error("Error saving report:", data.result.error);
                // Show an error notification to the user
                this.notificationService.add(data.result.error, {
                    type: 'danger',
                    title: 'Error Creating Report',
                    sticky: true
                });
                return;
            }

            console.log("Report created successfully:", data.result);

            // If the reports tab is active, refresh the list
            if (this.isReportsTabActive) {
                this.loadReports();
            } else {
                // Otherwise, switch to the reports tab which will load reports
                this.setActiveTab('reports');
            }

            // Show success notification
            this.notificationService.add('Report created successfully', {
                type: 'success',
                title: 'Success',
                sticky: false
            });
        })
        .catch(error => {
            console.error("Error saving report:", error);
        })
        .finally(() => {
            this.state.creatingReport = false;
        });
    }

    /**
     * Load saved reports
     */
    loadReports() {
        this.state.reportsLoading = true;

        fetch('/leulit_ia/get_reports', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': odoo.csrf_token,
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {},
                id: Math.floor(Math.random() * 1000000)
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error("Error loading reports:", data.error);
                return;
            }

            if (data.result && data.result.status === 'success' && data.result.result) {
                this.state.reports = data.result.result;
            } else {
                this.state.reports = [];
            }
        })
        .catch(error => {
            console.error("Error loading reports:", error);
            this.state.reports = [];
        })
        .finally(() => {
            this.state.reportsLoading = false;
        });
    }

    /**
     * Delete a report
     * @param {number} reportId The ID of the report to delete
     * @param {Event} event The click event (optional)
     */
    deleteReport(reportId, event) {
        // Prevent event propagation to avoid triggering parent click handlers if event is provided
        if (event && event.stopPropagation) {
            event.stopPropagation();
        }

        fetch('/leulit_ia/delete_report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': odoo.csrf_token,
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    report_id: reportId
                },
                id: Math.floor(Math.random() * 1000000)
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error("Error deleting report:", data.error);
                return;
            }

            // Refresh reports list
            this.loadReports();

            // If the deleted report was selected, clear the selection
            if (this.state.selectedReport && this.state.selectedReport.id === reportId) {
                this.state.selectedReport = null;
            }
        })
        .catch(error => {
            console.error("Error deleting report:", error);
        });
    }

    /**
     * Select a report to view
     * @param {Object} report The report to view
     */
    selectReport(report) {
        this.state.selectedReport = report;
    }
}

// Define the template name
SearchPage.template = 'leulit_ia.search_page';

// Registration in action_registry.js

export default SearchPage;
