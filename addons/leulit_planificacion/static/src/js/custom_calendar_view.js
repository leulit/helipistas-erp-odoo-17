/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller";
import { onMounted } from "@odoo/owl";

patch(AttendeeCalendarController.prototype, {
    setup() {
        super.setup(...arguments);

        onMounted(() => {
            const filterSections = this.model.data.filterSections;

            // La captura confirma que esta estructura existe en 'onMounted'.
            if (filterSections && filterSections.partner_ids) {
                const partnerFilters = filterSections.partner_ids.filters;
                const allFilter = partnerFilters.find(f => f.type === 'all');
                
                // Solo actuamos si el filtro "Todos" no está ya activo para evitar bucles.
                if (allFilter && !allFilter.active) {
                    const userPartnerFilter = partnerFilters.find(f => f.value === this.model.userPartnerId);

                    // 1. Modificamos el estado de los filtros
                    allFilter.active = true;
                    if (userPartnerFilter) {
                        userPartnerFilter.active = false;
                    }
                    
                    // 2. PASO CLAVE: Forzamos una recarga completa del modelo.
                    // Esto volverá a pedir los eventos al servidor, pero esta vez
                    // usando el nuevo estado de los filtros que acabamos de modificar.
                    this.model.load();
                }
            }
        });
    }
});