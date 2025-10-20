/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller";
import { onWillStart } from "@odoo/owl";

patch(AttendeeCalendarController.prototype, {
    setup() {
        super.setup(...arguments);

        // onWillStart se ejecuta ANTES de la primera carga.
        onWillStart(async () => {
            // Esperamos a que el modelo se cargue por primera vez con sus datos por defecto.
            await this.model.load();
            
            // Justo después de la carga inicial, y ANTES del primer renderizado,
            // modificamos los filtros en memoria.
            const filterSections = this.model.data.filterSections;
            if (filterSections && filterSections.partner_ids) {
                const partnerFilters = filterSections.partner_ids.filters;
                const allFilter = partnerFilters.find(f => f.type === 'all');
                const userPartnerFilter = partnerFilters.find(f => f.value === this.model.userPartnerId);

                if (allFilter) {
                    allFilter.active = true;
                }
                if (userPartnerFilter) {
                    userPartnerFilter.active = false;
                }
            }
        });
    }
});