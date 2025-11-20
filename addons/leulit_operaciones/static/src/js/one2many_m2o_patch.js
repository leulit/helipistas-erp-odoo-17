/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

patch(ListRenderer.prototype, {
    onGlobalClick(ev) {
        if (!this.editedRecord) {
            return;
        }
        this.tableRef.el.querySelector("tbody").classList.remove("o_keyboard_navigation");
        const target = ev.target;
        if (this.tableRef.el.contains(target) && target.closest(".o_data_row")) {
            return;
        }
        if (this.activeElement !== this.uiService.activeElement) {
            return;
        }
        // DateTime picker
        if (target.closest(".o_datetime_picker")) {
            return;
        }
        // Legacy autocomplete
        if (ev.target.closest(".ui-autocomplete")) {
            return;
        }
        // Many2one widget: evita cerrar la línea editable
        if (target.closest('.o_field_many2one')) {
            return;
        }
        this.props.list.leaveEditMode();
    },
});
