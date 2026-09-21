/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useChildSubEnv } from "@odoo/owl";

/**
 * Report creation dialog component
 * Allows creating a visualization from search results
 */
export class ReportDialog extends Component {
    static template = "leulit_ia.report_dialog";
    static components = { Dialog };

    static props = {
        queryText: { type: String },
        searchResults: { type: Object },
        close: { type: Function },
        onConfirm: { type: Function, optional: true },
    };

    setup() {
        useChildSubEnv({ inDialog: true });

        // Extract available fields from search results
        const availableFields = this._extractAvailableFields();

        // Initialize state with default values
        this.state = useState({
            name: this.props.queryText.substring(0, 50),
            visualizationType: "bar",
            validationError: null,
            availableFields: availableFields,
            dimensionField: this._getDefaultDimensionField(availableFields),
            measureField: this._getDefaultMeasureField(availableFields),
            aggregationType: "none", // Default aggregation type - no aggregation
            seriesField: this._getDefaultSeriesField(availableFields),
            config: {
                // Visualization type specific default settings
                stacked: false,
                cumulated: false
            }
        });

        // Debug log props
        console.log("ReportDialog props:", {
            queryText: this.props.queryText,
            searchResults: this.props.searchResults
        });

        console.log("Available fields:", availableFields);
    }

    /**
     * Extract available fields from search results for visualization
     * @returns {Array} List of field objects with name, type, and label
     */
    _extractAvailableFields() {
        const searchResults = this.props.searchResults || {};
        const availableFields = [];

        // Process different result formats (single model, multi-model, etc.)
        if (searchResults.multi_model && searchResults.results) {
            // Use first model with records
            const modelWithRecords = searchResults.results.find(
                model => model.records && model.records.length > 0
            );

            if (modelWithRecords && modelWithRecords.records[0]) {
                const firstRecord = modelWithRecords.records[0];
                this._addFieldsFromRecord(firstRecord, availableFields);
            }
        } else if (searchResults.records && searchResults.records.length > 0) {
            // Single model results
            this._addFieldsFromRecord(searchResults.records[0], availableFields);
        }

        return availableFields;
    }

    /**
     * Add fields from a record object to available fields array
     * @param {Object} record Record object to extract fields from
     * @param {Array} availableFields Array to add fields to
     */
    _addFieldsFromRecord(record, availableFields) {
        for (const [field, value] of Object.entries(record)) {
            // Skip technical fields
            if (['id', 'has_linked_data'].includes(field) || field.endsWith('_info')) {
                continue;
            }

            let fieldType = 'string';

            if (typeof value === 'number') {
                fieldType = 'number';
            } else if (value instanceof Date ||
                      (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}/.test(value))) {
                fieldType = 'date';
            }

            availableFields.push({
                name: field,
                type: fieldType,
                label: field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
            });
        }
    }

    /**
     * Get default dimension field (prefer date/string fields)
     * @param {Array} fields Available fields
     * @returns {String} Default dimension field name
     */
    _getDefaultDimensionField(fields) {
        // First try to find a date field
        const dateField = fields.find(f => f.type === 'date');
        if (dateField) return dateField.name;

        // Then try to find a string field
        const stringField = fields.find(f => f.type === 'string');
        if (stringField) return stringField.name;

        return fields.length > 0 ? fields[0].name : null;
    }

    /**
     * Get default measure field (prefer numeric fields)
     * @param {Array} fields Available fields
     * @returns {String} Default measure field name
     */
    _getDefaultMeasureField(fields) {
        // Try to find a numeric field
        const numField = fields.find(f => f.type === 'number');
        if (numField) return numField.name;

        // If no numeric field, try to find a field that's not the dimension field
        const dimensionField = this._getDefaultDimensionField(fields);
        const alternateField = fields.find(f => f.name !== dimensionField);

        return alternateField ? alternateField.name : (fields.length > 0 ? fields[0].name : null);
    }

    /**
     * Get available aggregation types based on field type
     * @returns {Array} Array of aggregation type objects
     */
    _getAggregationTypes() {
        return [
            { id: 'none', name: 'None', applicableToAll: true },
            { id: 'count', name: 'Count', applicableToAll: true },
            { id: 'sum', name: 'Sum', numericOnly: true },
            { id: 'average', name: 'Average', numericOnly: true },
            { id: 'min', name: 'Minimum', numericOnly: true },
            { id: 'max', name: 'Maximum', numericOnly: true }
        ];
    }

    /**
     * Get aggregation types applicable to the current measure field
     * @returns {Array} Filtered array of aggregation types
     */
    _getApplicableAggregationTypes() {
        const aggregationTypes = this._getAggregationTypes();
        const measureField = this.state.measureField;
        const fieldObj = this.state.availableFields.find(f => f.name === measureField);
        const isNumeric = fieldObj && fieldObj.type === 'number';

        return aggregationTypes.filter(type => type.applicableToAll || (isNumeric && type.numericOnly));
    }

    /**
     * Get default series field (for stacked charts, prefer string fields)
     * @param {Array} fields Available fields
     * @returns {String} Default series field name
     */
    _getDefaultSeriesField(fields) {
        // Find a string field different from dimension field
        const dimensionField = this._getDefaultDimensionField(fields);
        const stringFields = fields.filter(f => f.type === 'string');

        // If we have multiple string fields, use a different one from dimension
        if (stringFields.length > 1) {
            const alternateField = stringFields.find(f => f.name !== dimensionField);
            if (alternateField) return alternateField.name;
        } else if (stringFields.length === 1 && stringFields[0].name !== dimensionField) {
            return stringFields[0].name;
        }

        // Fallback to any field different from dimension and measure
        const measureField = this._getDefaultMeasureField(fields);
        const alternateField = fields.find(f => f.name !== dimensionField && f.name !== measureField);

        return alternateField ? alternateField.name : (fields.length > 0 ? fields[0].name : null);
    }

    /**
     * Handle visualization type change
     * @param {Event} ev Change event from select element
     */
    onVisualizationTypeChanged(ev) {
        const previousType = this.state.visualizationType;
        this.state.visualizationType = ev.target.value;

        // Preserve existing field selections
        const dimensionField = this.state.dimensionField;
        const measureField = this.state.measureField;
        const seriesField = this.state.seriesField;

        // Update config based on visualization type but keep field selections
        switch(this.state.visualizationType) {
            case 'bar':
                this.state.config = {
                    stacked: previousType === 'bar' ? this.state.config.stacked : false,
                    dimensionField: dimensionField,
                    measureField: measureField,
                    seriesField: seriesField
                };
                break;
            case 'line':
                this.state.config = {
                    cumulated: previousType === 'line' ? this.state.config.cumulated : false,
                    dimensionField: dimensionField,
                    measureField: measureField
                };
                break;
            case 'pie':
                this.state.config = {
                    dimensionField: dimensionField,
                    measureField: measureField
                };
                break;
        }
    }

    /**
     * Handle dimension field change
     * @param {Event} ev Change event from select element
     */
    onDimensionFieldChanged(ev) {
        this.state.dimensionField = ev.target.value;
    }

    /**
     * Handle measure field change
     * @param {Event} ev Change event from select element
     */
    onMeasureFieldChanged(ev) {
        this.state.measureField = ev.target.value;

        // Reset aggregation type if the new field doesn't support the current type
        const fieldObj = this.state.availableFields.find(f => f.name === ev.target.value);
        const isNumeric = fieldObj && fieldObj.type === 'number';
        const currentAggType = this.state.aggregationType;

        // If current aggregation is numeric only and the field is not numeric, reset to count
        const aggregationTypes = this._getAggregationTypes();
        const currentAggTypeObj = aggregationTypes.find(t => t.id === currentAggType);

        if (currentAggTypeObj && currentAggTypeObj.numericOnly && !isNumeric) {
            this.state.aggregationType = 'count';
        }
    }

    /**
     * Handle aggregation type change
     * @param {Event} ev Change event from select element
     */
    onAggregationTypeChanged(ev) {
        this.state.aggregationType = ev.target.value;
    }

    /**
     * Handle series field change (for stacked bar charts)
     * @param {Event} ev Change event from select element
     */
    onSeriesFieldChanged(ev) {
        this.state.seriesField = ev.target.value;
    }

    /**
     * Validate inputs before submission
     * @returns {boolean} Whether inputs are valid
     */
    validateInputs() {
        // Clear previous validation error
        this.state.validationError = null;

        // Check required fields
        if (!this.state.name || this.state.name.trim() === '') {
            this.state.validationError = "Report name is required";
            return false;
        }

        // Query text should be present from props
        if (!this.props.queryText) {
            this.state.validationError = "No search query provided";
            return false;
        }

        // Check field selections
        if (!this.state.dimensionField) {
            this.state.validationError = "Please select a dimension field";
            return false;
        }

        if (!this.state.measureField) {
            this.state.validationError = "Please select a measure field";
            return false;
        }

        // Check series field if stacked bar chart is selected
        if (this.state.visualizationType === 'bar' && this.state.config.stacked && !this.state.seriesField) {
            this.state.validationError = "Please select a series field for stacked bar chart";
            return false;
        }

        return true;
    }

    /**
     * Confirm dialog and pass data back to parent
     */
    onConfirm() {
        // Validate inputs first
        if (!this.validateInputs()) {
            return; // Don't proceed if validation fails
        }

        if (this.props.onConfirm) {
            // Create the data payload
            const name = String(this.state.name).trim();
            const query_text = this.props.queryText ? String(this.props.queryText).trim() : "";

            // Get search results and ensure it's structured properly
            let rawData = this.props.searchResults || {};

            // Update config with selected fields
            this.state.config.dimensionField = this.state.dimensionField;
            this.state.config.measureField = this.state.measureField;

            // Add series field for stacked bar charts
            if (this.state.visualizationType === 'bar' && this.state.config.stacked) {
                this.state.config.seriesField = this.state.seriesField;
            }

            // Create chart definition used by visualization component
            const chartDefinition = {
                // Field selections that tell the visualization component which fields to use
                dimensionField: this.state.dimensionField,
                measureField: this.state.measureField,
                aggregationType: this.state.aggregationType,
                seriesField: this.state.visualizationType === 'bar' && this.state.config.stacked ?
                    this.state.seriesField : null,
                // Pre-calculated field metadata
                fieldTypes: this.state.availableFields.reduce((acc, field) => {
                    acc[field.name] = field.type;
                    return acc;
                }, {}),
            };

            // Add chart definition to data for visualization component
            rawData.chartDefinition = chartDefinition;

            // Deep clone and convert to simple objects to prevent Proxy issues
            const reportData = {
                name: name, // Trim whitespace
                query_text: query_text, // Use snake_case to match backend expectation
                visualization_type: String(this.state.visualizationType), // Use snake_case for backend
                config: JSON.parse(JSON.stringify(this.state.config || {})),
                data: JSON.parse(JSON.stringify(rawData))
            };

            // Perform local validation
            if (!name || !query_text) {
                const errorMsg = [];
                if (!name) errorMsg.push("Name is required");
                if (!query_text) errorMsg.push("Query text is required");

                this.state.validationError = errorMsg.join(". ");
                return;
            }

            // Debug log
            console.log("Sending report data:", reportData);

            // Send data to parent
            this.props.onConfirm(reportData);
            // Close dialog after confirmation
            this.props.close();
        }
    }

    /**
     * Preprocess data to prepare it for visualization
     * @param {Object} data The search results data
     */
    _preprocessDataForVisualization(data) {
        // Don't modify if data is empty
        if (!data || Object.keys(data).length === 0) {
            return;
        }

        console.log("Preprocessing data for visualization:", data);

        // If this is a multi-model result with date fields, preprocess for better visualization
        if (data.multi_model && data.results && Array.isArray(data.results)) {
            console.log("Preprocessing multi-model data");

            // Mark the data as processed to avoid re-processing
            data._preprocessed = true;

            // For each model result, see if we can preprocess
            data.results.forEach(modelResult => {
                if (!modelResult.records || !Array.isArray(modelResult.records) || modelResult.records.length === 0) {
                    return;
                }

                // Check if this is a log-type model with date fields
                const isLogModel = modelResult.model.includes('log') || modelResult.model_label.includes('Log');

                if (isLogModel) {
                    console.log("Preprocessing log model data:", modelResult.model);

                    // Find date fields
                    const firstRecord = modelResult.records[0];
                    const dateFields = [];

                    for (const field in firstRecord) {
                        const value = firstRecord[field];
                        // Skip relationship info fields
                        if (!['id', 'has_linked_data'].includes(field) && !field.endsWith('_info')) {
                            // Check if it looks like a date field
                            if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}/.test(value)) {
                                dateFields.push(field);
                            }
                        }
                    }

                    // If we found date fields, add precalculated frequency data
                    if (dateFields.length > 0) {
                        const dateField = dateFields[0]; // Use the first date field
                        console.log(`Found date field '${dateField}' for preprocessing`);

                        // Group by date and count occurrences
                        const dateCounts = {};
                        modelResult.records.forEach(record => {
                            let dateValue = record[dateField];

                            // Ensure we have just the date part
                            if (dateValue) {
                                dateValue = dateValue.split('T')[0].split(' ')[0];

                                if (!dateCounts[dateValue]) {
                                    dateCounts[dateValue] = 0;
                                }
                                dateCounts[dateValue]++;
                            }
                        });

                        // Add the aggregated data to the model result
                        modelResult._dateAggregation = {
                            dateField: dateField,
                            dates: Object.keys(dateCounts).sort(),
                            counts: Object.keys(dateCounts).sort().map(date => dateCounts[date])
                        };

                        console.log("Preprocessed date aggregation:", modelResult._dateAggregation);
                    }
                }
            });
        }
    }

    /**
     * Cancel and close dialog
     */
    onCancel() {
        this.props.close();
    }
}

export default ReportDialog;
