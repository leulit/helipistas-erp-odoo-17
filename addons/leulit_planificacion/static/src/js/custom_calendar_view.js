/** @odoo-module **/

import { CalendarModel } from "@web/views/calendar/calendar_model";
import { patch } from "@web/core/utils/patch";

const _loadFilter = CalendarModel.prototype._loadFilter;

patch(CalendarModel.prototype, {
    async _loadFilter(filter) {
        if (!filter.not_init) {
            filter.not_init = true;
            filter.all = true;
        }
        if (_loadFilter) {
            return await _loadFilter.apply(this, arguments);
        }
    },
});