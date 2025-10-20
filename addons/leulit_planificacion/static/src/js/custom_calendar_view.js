/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";

patch(AttendeeCalendarModel.prototype, {
    /**
     * Parcheamos el método 'load'. Este es el punto de entrada principal
     * que el controlador llama para cargar TODOS los datos del calendario.
     * Es el lugar perfecto para modificar el resultado final.
     */
    async load(params) {
        // Primero, dejamos que el método 'load' original se ejecute por completo.
        // Esto cargará los eventos, los filtros, y establecerá el filtro por defecto
        // del usuario actual como activo.
        await super.load(...arguments);

        // Una vez que 'super.load()' ha terminado, podemos estar 100% seguros
        // de que la estructura de datos this.data.filterSections.partner_ids ya existe.
        // Ahora, la modificamos a nuestro gusto.
        const filterSections = this.data.filterSections;
        if (filterSections && filterSections.partner_ids) {
            const partnerFilters = filterSections.partner_ids.filters;
            const allFilter = partnerFilters.find(f => f.type === 'all');
            const userPartnerFilter = partnerFilters.find(f => f.value === this.userPartnerId);

            if (allFilter) {
                allFilter.active = true;
            }
            if (userPartnerFilter) {
                userPartnerFilter.active = false;
            }
        }
    }
});