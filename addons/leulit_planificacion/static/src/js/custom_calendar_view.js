/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";

patch(AttendeeCalendarModel.prototype, {
    /**
     * Sobrescribimos el método que carga específicamente las secciones de filtros.
     * Esto se ejecuta DENTRO de la carga inicial ('load'), justo ANTES de que
     * el modelo pida los registros de eventos al servidor.
     */
    async _loadFilterSections(meta) {
        // Dejamos que el método original cree la estructura de filtros con su defecto (usuario activo).
        await super._loadFilterSections(...arguments);

        // Inmediatamente después, modificamos ese resultado en memoria.
        const partnerFilters = this.data.filterSections.partner_ids.filters;
        const allFilter = partnerFilters.find(f => f.type === 'all');
        const userPartnerFilter = partnerFilters.find(f => f.value === this.userPartnerId);

        if (allFilter) {
            allFilter.active = true;
        }
        if (userPartnerFilter) {
            userPartnerFilter.active = false;
        }
    }
});