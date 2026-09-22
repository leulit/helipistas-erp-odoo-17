/** @odoo-module **/

import { Component, useState, onWillStart, useRef, onMounted, onPatched, onWillUnmount } from "@odoo/owl";
import { loadBundle, loadJS } from "@web/core/assets";
import { formatFloat } from "@web/views/fields/formatters";
import { cookie } from "@web/core/browser/cookie";

// Direct import of Chart.js - this is a fallback in case loadBundle doesn't work
let Chart;

/**
 * Report Visualization Component
 * Renders charts using Chart.js directly without dependencies on Odoo's GraphRenderer
 */
export class ReportVisualization extends Component {
    static template = "leulit_ai.report_visualization";
    
    static props = {
        report: { type: Object },
        data: { type: Object, optional: true },
    };
    
    setup() {
        this.chartRef = useRef("chartCanvas");
        this.chart = null;
        
        this.state = useState({
            loading: true,
            error: null
        });
        
        onWillStart(async () => {
            try {
                // Try loading Chart.js both ways
                await loadBundle("web.chartjs_lib");
                
                // If global Chart object isn't defined, try to load it directly
                if (typeof Chart === 'undefined') {
                    console.log("Chart not defined after loadBundle, trying alternative load");
                    try {
                        // Try to get Chart from window
                        Chart = window.Chart;
                        if (!Chart) {
                            // As a last resort, load Chart.js from CDN
                            await loadJS("https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js");
                            Chart = window.Chart;
                        }
                    } catch (e) {
                        console.error("Error loading Chart.js from alternative source:", e);
                        throw e;
                    }
                }
                
                console.log("Chart.js loaded successfully, Chart =", Chart);
                
                // Set loading to false after chart library is loaded
                this.state.loading = false;
            } catch (error) {
                console.error("Error loading Chart.js library:", error);
                this.state.error = "Failed to load chart library";
                this.state.loading = false;
            }
        });
        
        onMounted(() => {
            this.renderChart();
        });
        
        onPatched(() => {
            // Re-render chart when component props change
            this.renderChart();
        });
        
        onWillUnmount(() => {
            // Clean up chart instance when component is unmounted
            if (this.chart) {
                this.chart.destroy();
                this.chart = null;
            }
        });
    }
    
    /**
     * Format numbers to display in chart
     * @param {number} value The value to format
     * @returns {string} Formatted value
     */
    formatValue(value) {
        if (Math.abs(value) >= 1000) {
            return formatFloat(value, { humanReadable: true, decimals: 2, minDigits: 1 });
        }
        return value.toString();
    }
    
    /**
     * Get color for a dataset based on index
     * @param {number} index The dataset index
     * @param {number} total Total number of datasets
     * @returns {string} Color string
     */
    getColor(index, total) {
        const colors = [
            'rgba(75, 192, 192, 0.8)',
            'rgba(255, 99, 132, 0.8)',
            'rgba(54, 162, 235, 0.8)',
            'rgba(255, 206, 86, 0.8)',
            'rgba(153, 102, 255, 0.8)',
            'rgba(255, 159, 64, 0.8)',
            'rgba(240, 240, 240, 0.8)',
            'rgba(220, 220, 220, 0.8)',
            'rgba(200, 200, 200, 0.8)',
            'rgba(180, 180, 180, 0.8)',
        ];
        
        // Get color with modulo for case where we have more datasets than colors
        return colors[index % colors.length];
    }
    
    /**
     * Get data for the chart based on the report
     * @returns {Object} Chart data 
     */
    getChartData() {
        const visualizationType = this.props.report.visualization_type;
        
        // Get config from the report
        let config = {};
        try {
            config = typeof this.props.report.config === 'string' ?
                JSON.parse(this.props.report.config || '{}') :
                this.props.report.config || {};
        } catch (e) {
            console.error("Failed to parse report config:", e);
        }
        
        // Try to get data directly from the report
        let reportData = this.props.report.data;
        if (reportData) {
            console.log("Data found directly in report:", reportData);
            // Parse the data if it's a string
            if (typeof reportData === 'string') {
                try {
                    reportData = JSON.parse(reportData);
                } catch (e) {
                    console.error("Failed to parse report data as string:", e);
                    reportData = null;
                }
            }
        }
        
        // Try to extract search results if they exist 
        if (reportData) {
            // The search results might be in various formats - check all possibilities
            const searchResults = reportData.graphData || // Already processed data
                                reportData.data || // Data might be nested
                                reportData; // Direct data
            
            // If we have processed graph data, use it directly
            if (searchResults && searchResults.labels && searchResults.datasets) {
                console.log("Using pre-processed graph data from report");
                return searchResults;
            }
            
            // PRIORITY 1: Check if we have a chartDefinition with user-selected fields
            // This is added by the ReportDialog when the user selects fields
            const chartDefinition = searchResults.chartDefinition;
            
            if (chartDefinition) {
                console.log("Using user-selected fields from chartDefinition:", chartDefinition);
                
                // Get the selected fields
                const dimensionField = chartDefinition.dimensionField;
                const measureField = chartDefinition.measureField;
                const aggregationType = chartDefinition.aggregationType || 'count';
                const seriesField = chartDefinition.seriesField;
                
                // Find the records to visualize
                let records = [];
                
                if (searchResults.multi_model && searchResults.results) {
                    // For multi-model, use the first model with records
                    const modelWithRecords = searchResults.results.find(
                        model => model.records && model.records.length > 0
                    );
                    
                    if (modelWithRecords && modelWithRecords.records) {
                        records = modelWithRecords.records;
                    }
                } else if (searchResults.records) {
                    // Single model search results
                    records = searchResults.records;
                }
                
                // If we have records and the selected fields
                if (records.length > 0 && dimensionField) {
                    // For stacked bar charts, we need to group by the series field
                    if (visualizationType === 'bar' && config.stacked && seriesField) {
                        console.log("Creating stacked bar chart data with series field:", seriesField);
                        
                        // Step 1: Get unique dimension values and series values
                        const dimensionValues = [...new Set(records.map(r => r[dimensionField]))];
                        const seriesValues = [...new Set(records.map(r => r[seriesField]))];
                        
                        // Format dimension values for display
                        const labels = dimensionValues.map(value => 
                            value !== undefined && value !== null ? String(value) : '');
                        
                        // Step 2: Create a dataset for each series value
                        const datasets = seriesValues.map((seriesValue, index) => {
                            // Filter records for this series value
                            const seriesData = dimensionValues.map(dimValue => {
                                // Find records that match both dimension and series values
                                const matchingRecords = records.filter(
                                    r => r[dimensionField] == dimValue && r[seriesField] == seriesValue
                                );
                                
                                // Apply the selected aggregation to the measure values
                                if (matchingRecords.length > 0) {
                                    return this._aggregateValues(matchingRecords, measureField, aggregationType);
                                }
                                return 0; // No matching records
                            });
                            
                            return {
                                label: seriesValue ? String(seriesValue) : `Series ${index + 1}`,
                                data: seriesData,
                                backgroundColor: this.getColor(index, seriesValues.length),
                                borderColor: this.getColor(index, seriesValues.length).replace('0.8', '1'),
                                borderWidth: 1
                            };
                        });
                        
                        return { labels, datasets };
                    }
                        // Regular chart (not stacked or series not provided)
                        else {
                            console.log("Creating regular chart data with user-selected fields");
                            
                            // Step 1: Group records by dimension value
                            const groupedRecords = {};
                            records.forEach(record => {
                                const dimensionValue = record[dimensionField];
                                const key = dimensionValue !== undefined && dimensionValue !== null ? 
                                    String(dimensionValue) : '';
                                
                                if (!groupedRecords[key]) {
                                    groupedRecords[key] = [];
                                }
                                
                                groupedRecords[key].push(record);
                            });
                            
                            // Step 2: Create labels and data arrays
                            const labels = Object.keys(groupedRecords);
                            const values = labels.map(label => 
                                this._aggregateValues(groupedRecords[label], measureField, aggregationType)
                            );
                        
                        // Format field name for display
                        const fieldLabel = measureField.replace(/_/g, ' ')
                                           .replace(/\b\w/g, l => l.toUpperCase());
                        
                        return {
                            labels,
                            datasets: [{
                                label: fieldLabel,
                                data: values,
                                backgroundColor: visualizationType === 'pie' ? 
                                    labels.map((_, i) => this.getColor(i, labels.length)) :
                                    'rgba(75, 192, 192, 0.2)',
                                borderColor: 'rgba(75, 192, 192, 1)',
                                borderWidth: 1
                            }]
                        };
                    }
                }
            }
            
            // PRIORITY 2: Check if we have field selections in the config
            // This is for backward compatibility with reports saved before chartDefinition
            if (!chartDefinition && config.dimensionField && config.measureField) {
                console.log("Using fields from config:", config.dimensionField, config.measureField);
                
                // Find the records to visualize
                let records = [];
                
                if (searchResults.multi_model && searchResults.results) {
                    // For multi-model, use the first model with records
                    const modelWithRecords = searchResults.results.find(
                        model => model.records && model.records.length > 0
                    );
                    
                    if (modelWithRecords && modelWithRecords.records) {
                        records = modelWithRecords.records;
                    }
                } else if (searchResults.records) {
                    // Single model search results
                    records = searchResults.records;
                }
                
                // If we have records and the selected fields
                if (records.length > 0) {
                    const dimensionField = config.dimensionField;
                    const measureField = config.measureField;
                    
                    // For stacked bar charts, we need the series field
                    if (visualizationType === 'bar' && config.stacked && config.seriesField) {
                        const seriesField = config.seriesField;
                        
                        // Step 1: Get unique dimension values and series values
                        const dimensionValues = [...new Set(records.map(r => r[dimensionField]))];
                        const seriesValues = [...new Set(records.map(r => r[seriesField]))];
                        
                        // Format dimension values for display
                        const labels = dimensionValues.map(value => 
                            value !== undefined && value !== null ? String(value) : '');
                        
                        // Step 2: Create a dataset for each series value
                        const datasets = seriesValues.map((seriesValue, index) => {
                            // Filter records for this series value
                            const seriesData = dimensionValues.map(dimValue => {
                                // Find records that match both dimension and series values
                                const matchingRecords = records.filter(
                                    r => r[dimensionField] == dimValue && r[seriesField] == seriesValue
                                );
                                
                                // Sum up the measure values for these records
                                if (matchingRecords.length > 0) {
                                    return matchingRecords.reduce((sum, record) => {
                                        const value = record[measureField];
                                        const numValue = typeof value === 'number' ? 
                                            value : parseFloat(value) || 0;
                                        return sum + numValue;
                                    }, 0);
                                }
                                return 0; // No matching records
                            });
                            
                            return {
                                label: seriesValue ? String(seriesValue) : `Series ${index + 1}`,
                                data: seriesData,
                                backgroundColor: this.getColor(index, seriesValues.length),
                                borderColor: this.getColor(index, seriesValues.length).replace('0.8', '1'),
                                borderWidth: 1
                            };
                        });
                        
                        return { labels, datasets };
                    }
                    // Regular chart (not stacked or series not provided)
                    else {
                        // Extract labels and data using selected fields
                        const labels = records.map(record => {
                            const value = record[dimensionField];
                            return value !== undefined ? String(value) : '';
                        });
                        
                        const values = records.map(record => {
                            const value = record[measureField];
                            if (typeof value === 'number') {
                                return value;
                            } else if (Array.isArray(value) && value.length > 0) {
                                return parseFloat(value[0]) || 0;
                            }
                            return parseFloat(value) || 0;
                        });
                        
                        // Format field name for display
                        const fieldLabel = measureField.replace(/_/g, ' ')
                                           .replace(/\b\w/g, l => l.toUpperCase());
                        
                        return {
                            labels,
                            datasets: [{
                                label: fieldLabel,
                                data: values,
                                backgroundColor: visualizationType === 'pie' ? 
                                    labels.map((_, i) => this.getColor(i, labels.length)) :
                                    'rgba(75, 192, 192, 0.2)',
                                borderColor: 'rgba(75, 192, 192, 1)',
                                borderWidth: 1
                            }]
                        };
                    }
                }
            }
            
            // Check if this is an aggregation result
            if (searchResults && searchResults.aggregation === true) {
                console.log("Processing aggregation results");
                
                // Extract dimension and measure fields from the aggregation result
                const dimensionField = searchResults.dimension;
                const measureField = searchResults.measure;
                
                if (dimensionField && measureField && searchResults.records && searchResults.records.length > 0) {
                    // Extract labels and values for the chart
                    const labels = searchResults.records.map(record => {
                        // Handle potential date formatting here
                        const value = record[dimensionField];
                        return value !== undefined ? String(value) : '';
                    });
                    
                    const values = searchResults.records.map(record => {
                        return record[measureField] || 0;
                    });
                    
                    // Determine a good label based on field descriptions if available
                    let datasetLabel = measureField;
                    if (searchResults.field_descriptions && searchResults.field_descriptions[dimensionField]) {
                        datasetLabel = searchResults.field_descriptions[dimensionField];
                    }
                    
                    return {
                        labels,
                        datasets: [{
                            label: datasetLabel,
                            data: values,
                            backgroundColor: visualizationType === 'pie' ? 
                                labels.map((_, i) => this.getColor(i, labels.length)) :
                                'rgba(75, 192, 192, 0.2)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 1
                        }]
                    };
                }
            }
            
            // Check if this is a multi-model result
            if (searchResults && searchResults.multi_model === true && searchResults.results) {
                console.log("Processing multi-model results");
                
                // Get all model results
                const modelResults = searchResults.results;
                if (!Array.isArray(modelResults) || modelResults.length === 0) {
                    console.error("Invalid multi-model results structure");
                    return this.getSampleData(visualizationType);
                }
                
                // First check if we have preprocessed date aggregation data
                const preprocessedModel = modelResults.find(model => model._dateAggregation);
                if (preprocessedModel && preprocessedModel._dateAggregation) {
                    console.log("Using preprocessed date aggregation data", preprocessedModel._dateAggregation);
                    
                    const aggregation = preprocessedModel._dateAggregation;
                    const dates = aggregation.dates;
                    const counts = aggregation.counts;
                    
                    if (dates.length > 0) {
                        return {
                            labels: dates,
                            datasets: [{
                                label: `${preprocessedModel.model_label} by Date`,
                                data: counts,
                                backgroundColor: visualizationType === 'pie' ? 
                                    dates.map((_, i) => this.getColor(i, dates.length)) :
                                    'rgba(75, 192, 192, 0.2)',
                                borderColor: 'rgba(75, 192, 192, 1)',
                                borderWidth: 1
                            }]
                        };
                    }
                }
                
                console.log("Multi-model contains", modelResults.length, "models:", 
                    modelResults.map(m => m.model_label || m.model).join(", "));
                
                // Select the model with more records (likely the detail model with login data)
                const sortedModels = [...modelResults].sort((a, b) => {
                    const countA = Array.isArray(a.records) ? a.records.length : 0;
                    const countB = Array.isArray(b.records) ? b.records.length : 0;
                    return countB - countA; // Sort by record count in descending order
                });
                
                const primaryModelResult = sortedModels[0];
                
                if (!primaryModelResult || !primaryModelResult.records || !primaryModelResult.records.length) {
                    console.error("Selected model has no records");
                    return this.getSampleData(visualizationType);
                }
                
                console.log("Selected primary model:", primaryModelResult.model_label || primaryModelResult.model);
                
                // Find suitable date field for visualization
                const records = primaryModelResult.records;
                const first_record = records[0];
                let dateField = null;
                let countField = 'id'; // We'll count occurrences by default
                
                // Look for date fields first - they make the best x-axis for time-based data
                for (const field in first_record) {
                    const value = first_record[field];
                    const valueStr = String(value);
                    
                    // Skip relationship info fields
                    if (!['id', 'has_linked_data'].includes(field) && !field.endsWith('_info')) {
                        // Check for ISO date format or date objects
                        if (/^\d{4}-\d{2}-\d{2}/.test(valueStr) || 
                            (value instanceof Date) || 
                            (typeof value === 'object' && value !== null && typeof value.getFullYear === 'function')) {
                            dateField = field;
                            break;
                        }
                    }
                }
                
                if (dateField) {
                    console.log(`Found date field '${dateField}' for multi-model visualization`);
                    
                    // Group by date and count occurrences
                    const dateCounts = {};
                    records.forEach(record => {
                        let dateValue = record[dateField];
                        
                        // Ensure we have a string representation of the date (just the date part, no time)
                        if (dateValue instanceof Date) {
                            dateValue = dateValue.toISOString().split('T')[0];
                        } else if (typeof dateValue === 'string') {
                            // For ISO strings, just take the date part
                            dateValue = dateValue.split('T')[0].split(' ')[0];
                        } else if (typeof dateValue === 'object' && dateValue !== null) {
                            // Try to extract date from object
                            dateValue = String(dateValue).split('T')[0].split(' ')[0];
                        }
                        
                        // Count occurrences
                        if (dateValue) {
                            if (!dateCounts[dateValue]) {
                                dateCounts[dateValue] = 0;
                            }
                            dateCounts[dateValue]++;
                        }
                    });
                    
                    // Convert to arrays for chart
                    const dates = Object.keys(dateCounts).sort();
                    const counts = dates.map(date => dateCounts[date]);
                    
                    if (dates.length > 0) {
                        // Create a descriptive label based on model names
                        const modelName = primaryModelResult.model_label || primaryModelResult.model || '';
                        const datasetLabel = modelName.includes('log') ? 
                            `User Login Count` : `${modelName} Count`;
                        
                        return {
                            labels: dates,
                            datasets: [{
                                label: datasetLabel,
                                data: counts,
                                backgroundColor: visualizationType === 'pie' ? 
                                    dates.map((_, i) => this.getColor(i, dates.length)) :
                                    'rgba(75, 192, 192, 0.2)',
                                borderColor: 'rgba(75, 192, 192, 1)',
                                borderWidth: 1
                            }]
                        };
                    }
                }
                
                // If we couldn't find a date field, try to find any field that could be used as labels
                if (!dateField) {
                    console.log("No date field found, trying to find another field for visualization");
                    
                    // Find a suitable string field for labels and count occurrences
                    let labelField = null;
                    
                    for (const field in first_record) {
                        if (!['id', 'has_linked_data'].includes(field) && !field.endsWith('_info')) {
                            const value = first_record[field];
                            
                            // Look for a string field that could be used for grouping
                            if (typeof value === 'string') {
                                labelField = field;
                                break;
                            }
                        }
                    }
                    
                    if (labelField) {
                        console.log(`Using '${labelField}' as label field for multi-model visualization`);
                        
                        // Group by label field and count occurrences
                        const labelCounts = {};
                        records.forEach(record => {
                            const labelValue = record[labelField];
                            
                            if (labelValue) {
                                if (!labelCounts[labelValue]) {
                                    labelCounts[labelValue] = 0;
                                }
                                labelCounts[labelValue]++;
                            }
                        });
                        
                        // Convert to arrays for chart
                        const labels = Object.keys(labelCounts);
                        const counts = labels.map(label => labelCounts[label]);
                        
                        if (labels.length > 0) {
                            const modelName = primaryModelResult.model_label || primaryModelResult.model || '';
                            
                            return {
                                labels,
                                datasets: [{
                                    label: `${modelName} by ${labelField}`,
                                    data: counts,
                                    backgroundColor: visualizationType === 'pie' ? 
                                        labels.map((_, i) => this.getColor(i, labels.length)) :
                                        'rgba(75, 192, 192, 0.2)',
                                    borderColor: 'rgba(75, 192, 192, 1)',
                                    borderWidth: 1
                                }]
                            };
                        }
                    }
                }
            }
            
            // Try to extract records from standard search results
            if (searchResults && searchResults.records && searchResults.records.length > 0) {
                console.log("Processing records from search results");
                
                const records = searchResults.records;
                const first_record = records[0];
                let label_field = null;
                let value_field = null;
                
                // Find suitable fields for chart with improved detection
                for (const field in first_record) {
                    if (!['id', 'has_linked_data'].includes(field) && !field.endsWith('_info')) {
                        const value = first_record[field];
                        
                        // Improved detection for date-based fields to use as labels
                        if (label_field === null && 
                            (typeof value === 'string' || 
                             (typeof value === 'object' && value !== null && 
                              (value instanceof Date || 
                               (typeof value.getFullYear === 'function') || 
                               /^\d{4}-\d{2}-\d{2}/.test(String(value)))))) {
                            label_field = field;
                        }
                        // Find a numeric field for values - also check for string numbers
                        else if (value_field === null && 
                               (typeof value === 'number' || 
                                !isNaN(parseFloat(value)) ||
                                (Array.isArray(value) && value.length > 0 && 
                                 (typeof value[0] === 'number' || !isNaN(parseFloat(value[0])))))) {
                            value_field = field;
                        }
                    }
                }
                
                if (label_field && value_field) {
                    // Generate chart data from the records
                    const labels = records.map(record => {
                        const val = record[label_field]; 
                        return val !== undefined ? String(val) : '';
                    });
                    
                    const values = records.map(record => {
                        const val = record[value_field];
                        if (Array.isArray(val) && val.length > 0) {
                            return parseFloat(val[0]);
                        }
                        return typeof val === 'number' ? val : parseFloat(val);
                    });
                    
                    return {
                        labels,
                        datasets: [{
                            label: value_field,
                            data: values,
                            backgroundColor: visualizationType === 'pie' ? 
                                labels.map((_, i) => this.getColor(i, labels.length)) :
                                'rgba(75, 192, 192, 0.2)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 1
                        }]
                    };
                }
                
                // If we get here, we couldn't find suitable fields - try client-side aggregation for dates
                if (!value_field && records.length > 0) {
                    // Check if we have any date fields that could be grouped
                    let dateField = null;
                    for (const field in first_record) {
                        const value = first_record[field];
                        const valueStr = String(value);
                        
                        // Check for ISO date format or date objects
                        if (/^\d{4}-\d{2}-\d{2}/.test(valueStr) || 
                            (value instanceof Date) || 
                            (typeof value === 'object' && value !== null && typeof value.getFullYear === 'function')) {
                            dateField = field;
                            break;
                        }
                    }
                    
                    if (dateField) {
                        console.log(`Found date field '${dateField}', attempting client-side aggregation`);
                        
                        // Group by date and count occurrences
                        const dateCounts = {};
                        records.forEach(record => {
                            let dateValue = record[dateField];
                            
                            // Ensure we have a string representation of the date (just the date part, no time)
                            if (dateValue instanceof Date) {
                                dateValue = dateValue.toISOString().split('T')[0];
                            } else if (typeof dateValue === 'string') {
                                // For ISO strings, just take the date part
                                dateValue = dateValue.split('T')[0].split(' ')[0];
                            } else if (typeof dateValue === 'object' && dateValue !== null) {
                                // Try to extract date from object
                                dateValue = String(dateValue).split('T')[0].split(' ')[0];
                            }
                            
                            // Count occurrences
                            if (dateValue) {
                                if (!dateCounts[dateValue]) {
                                    dateCounts[dateValue] = 0;
                                }
                                dateCounts[dateValue]++;
                            }
                        });
                        
                        // Convert to arrays for chart
                        const dates = Object.keys(dateCounts).sort();
                        const counts = dates.map(date => dateCounts[date]);
                        
                        if (dates.length > 0) {
                            return {
                                labels: dates,
                                datasets: [{
                                    label: `Count by ${dateField}`,
                                    data: counts,
                                    backgroundColor: visualizationType === 'pie' ? 
                                        dates.map((_, i) => this.getColor(i, dates.length)) :
                                        'rgba(75, 192, 192, 0.2)',
                                    borderColor: 'rgba(75, 192, 192, 1)',
                                    borderWidth: 1
                                }]
                            };
                        }
                    }
                }
            }
        }
        
        console.log("No valid data found in report, using sample data");
        return this.getSampleData(visualizationType);
    }
    
    /**
     * Aggregate values using the specified aggregation type
     * @param {Array} records Array of record objects
     * @param {String} field Field name to aggregate
     * @param {String} aggregationType Type of aggregation (none, count, sum, average, min, max)
     * @returns {Number} Aggregated value
     */
    _aggregateValues(records, field, aggregationType) {
        if (!records || !records.length) {
            return 0;
        }
        
        // For no aggregation, return the field value of the first record
        if (aggregationType === 'none') {
            const value = records[0][field];
            if (typeof value === 'number') {
                return value;
            } else if (Array.isArray(value) && value.length > 0) {
                return parseFloat(value[0]) || 0;
            }
            return parseFloat(value) || 0;
        }
        
        // Count is handled specially since it doesn't depend on field values
        if (aggregationType === 'count') {
            return records.length;
        }
        
        // Extract numeric values from records for other aggregation types
        const numericValues = records.map(record => {
            const value = record[field];
            if (typeof value === 'number') {
                return value;
            } else if (Array.isArray(value) && value.length > 0) {
                return parseFloat(value[0]) || 0;
            }
            return parseFloat(value) || 0;
        }).filter(v => !isNaN(v));
        
        if (!numericValues.length) {
            return 0; // No numeric values found
        }
        
        // Apply the specified aggregation
        switch (aggregationType) {
            case 'sum':
                return numericValues.reduce((sum, val) => sum + val, 0);
                
            case 'average':
                return numericValues.reduce((sum, val) => sum + val, 0) / numericValues.length;
                
            case 'min':
                return Math.min(...numericValues);
                
            case 'max':
                return Math.max(...numericValues);
                
            default:
                // Default to count if aggregation type is unrecognized
                return records.length;
        }
    }
    
    /**
     * Generate sample data for preview
     * @param {string} visualizationType Chart type
     * @returns {Object} Sample chart data
     */
    getSampleData(visualizationType) {
        const labels = ['Sample A', 'Sample B', 'Sample C', 'Sample D', 'Sample E'];
        
        if (visualizationType === 'pie') {
            return {
                labels,
                datasets: [{
                    label: 'Sample Data',
                    data: [30, 20, 25, 15, 10],
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 206, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)'
                    ],
                    borderWidth: 1,
                    borderColor: cookie.get("color_scheme") === "dark" ? '#222' : '#fff'
                }]
            };
        } else {
            // Bar or line
            return {
                labels,
                datasets: [{
                    label: 'Sample Dataset',
                    data: [30, 20, 25, 15, 10],
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1,
                    fill: visualizationType === 'line' ? false : undefined,
                    tension: visualizationType === 'line' ? 0.1 : undefined
                }]
            };
        }
    }
    
    /**
     * Get chart configuration
     * @returns {Object} Chart config
     */
    getChartConfig() {
        const visualizationType = this.props.report.visualization_type;
        let config = {};
        
        try {
            config = typeof this.props.report.config === 'string' ?
                JSON.parse(this.props.report.config || '{}') :
                this.props.report.config || {};
        } catch (e) {
            console.error("Failed to parse report config:", e);
        }
        
        // Base configuration
        const chartConfig = {
            type: visualizationType,
            data: this.getChartData(),
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: cookie.get("color_scheme") === "dark" ? '#eee' : '#222'
                        },
                        title: {
                            display: true,
                            text: this.props.report.name || 'Chart'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += this.formatValue(context.raw);
                                return label;
                            }
                        }
                    },
                },
                animation: {
                    duration: 1000
                }
            }
        };
        
        // Add specific options based on chart type
        if (visualizationType === 'bar') {
            chartConfig.options.scales = {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: cookie.get("color_scheme") === "dark" ? '#ccc' : '#666'
                    },
                    title: {
                        display: true,
                        text: 'Value'
                    },
                    grid: {
                        color: cookie.get("color_scheme") === "dark" ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'
                    }
                },
                x: {
                    ticks: {
                        color: cookie.get("color_scheme") === "dark" ? '#ccc' : '#666'
                    },
                    grid: {
                        display: false
                    }
                }
            };
            
            if (config.stacked) {
                chartConfig.options.scales.x.stacked = true;
                chartConfig.options.scales.y.stacked = true;
            }
        } else if (visualizationType === 'line') {
            chartConfig.options.scales = {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: cookie.get("color_scheme") === "dark" ? '#ccc' : '#666'
                    },
                    title: {
                        display: true,
                        text: 'Value'
                    },
                    grid: {
                        color: cookie.get("color_scheme") === "dark" ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'
                    }
                },
                x: {
                    ticks: {
                        color: cookie.get("color_scheme") === "dark" ? '#ccc' : '#666'
                    }
                }
            };
            
            // Handle cumulative option
            if (config.cumulated) {
                const datasets = chartConfig.data.datasets;
                for (const dataset of datasets) {
                    let sum = 0;
                    dataset.data = dataset.data.map(value => {
                        sum += value;
                        return sum;
                    });
                }
            }
        } else if (visualizationType === 'pie') {
            chartConfig.options.radius = '90%';
        }
        
        return chartConfig;
    }
    
    /**
     * Render the chart
     */
    renderChart() {
        // Don't attempt to render if component is in loading state or if we've already encountered an error
        if (this.state.loading || this.state.error) {
            return;
        }
        
        // Cleanup previous chart if it exists
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
        
        // Ensure canvas element is available
        if (!this.chartRef.el) {
            console.error("Chart canvas element not found");
            this.state.error = "Canvas element not available";
            return;
        }
        
        try {
            console.log("Rendering chart with report:", this.props.report);
            
            // Debug log for report data
            try {
                let reportData = this.props.report.data;
                if (typeof reportData === 'string') {
                    reportData = JSON.parse(reportData);
                }
                console.log("Report data:", reportData);
            } catch (e) {
                console.warn("Could not parse report data for logging:", e);
            }
            
            const ctx = this.chartRef.el.getContext('2d');
            const config = this.getChartConfig();
            console.log("Chart configuration:", config);
            
            // Check if Chart is defined
            if (typeof Chart === 'undefined') {
                console.error("Chart.js not loaded properly!");
                this.state.error = "Chart.js library not available";
                return;
            }
            
            // Create chart using Chart.js
            // eslint-disable-next-line no-undef
            this.chart = new Chart(ctx, config);
            console.log("Chart successfully rendered");
        } catch (error) {
            console.error("Error rendering chart:", error);
            this.state.error = `Error rendering chart: ${error.message || error.toString()}`;
        }
    }
}

export default ReportVisualization;
