/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FloatField } from "@web/views/fields/float/float_field";
import { FloatTimeField } from "@web/views/fields/float_time/float_time_field";

/**
 * Bloquea edición en campos float y float_time.
 * Anula directamente los controladores internos de Odoo.
 */

export class KeyboardDisabledFloat extends FloatField {
    setup() {
        super.setup();
    }

    // Odoo usa onInput / onChange / onKeydown para actualizar el valor.
    // Los anulamos para bloquear toda interacción del usuario.
    onInput(ev) {
        ev.stopPropagation();
        ev.preventDefault();
    }

    onKeydown(ev) {
        ev.stopPropagation();
        ev.preventDefault();
    }

    onChange(ev) {
        ev.stopPropagation();
        ev.preventDefault();
    }

    // Si se enfoca, quitamos focus inmediatamente.
    onFocus(ev) {
        ev.target.blur();
    }
}

registry.category("fields").add("keyboard_disabled", {
    component: KeyboardDisabledFloat,
    supportedTypes: ["float"],
});

export class KeyboardDisabledFloatTime extends FloatTimeField {
    setup() {
        super.setup();
    }

    onInput(ev) {
        ev.stopPropagation();
        ev.preventDefault();
    }

    onKeydown(ev) {
        ev.stopPropagation();
        ev.preventDefault();
    }

    onChange(ev) {
        ev.stopPropagation();
        ev.preventDefault();
    }

    onFocus(ev) {
        ev.target.blur();
    }
}

registry.category("fields").add("keyboard_disabled_float_time", {
    component: KeyboardDisabledFloatTime,
    supportedTypes: ["float"],
});
