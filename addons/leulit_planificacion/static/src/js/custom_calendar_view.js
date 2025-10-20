/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller";
import { onMounted } from "@odoo/owl";

patch(AttendeeCalendarController.prototype, {
    setup() {
        super.setup(...arguments);

        // onMounted se ejecuta DESPUÉS de que todo esté renderizado.
        // Vamos a ver qué contienen los datos del modelo en este punto.
        onMounted(() => {
            console.log("Estructura de datos final del modelo (en onMounted):", this.model.data);
        });
    }
});