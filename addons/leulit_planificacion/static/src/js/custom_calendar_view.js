/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";

patch(AttendeeCalendarModel.prototype, {
    /**
     * Parcheamos 'loadFilters'. Como hemos descubierto en el código fuente,
     * este es el método correcto que orquesta la creación de los filtros.
     * Intervenimos aquí para modificar el resultado antes de que se use para
     * pedir los eventos al servidor.
     */
    async loadFilters(data) {
        // Dejamos que el método original de Odoo haga todo el trabajo de cargar los filtros.
        // Esto nos devolverá la estructura de datos completa con el filtro del usuario
        // activo por defecto.
        const { sections, dynamicFiltersInfo } = await super.loadFilters(...arguments);

        // Ahora que tenemos el resultado, lo modificamos en memoria antes de devolverlo.
        if (sections && sections.partner_ids) {
            const partnerFilters = sections.partner_ids.filters;
            const allFilter = partnerFilters.find(f => f.type === 'all');
            const userPartnerFilter = partnerFilters.find(f => f.value === this.userPartnerId);

            if (allFilter) {
                allFilter.active = true;
            }
            if (userPartnerFilter) {
                userPartnerFilter.active = false;
            }
        }
        
        // Devolvemos el objeto de filtros ya modificado para que el resto del
        // proceso de carga ('load') continúe con los datos correctos.
        return { sections, dynamicFiltersInfo };
    }
});