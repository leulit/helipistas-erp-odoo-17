/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

patch(ListRenderer.prototype, {
    _onCellClicked(event) {
        const $target = $(event.target);
        if ($target.closest('.o_field_many2one').length && this.mode === 'edit') {
            event.stopPropagation();
            return;
        }
        // Llama al método original
        return super._onCellClicked(event);
    },
});
