/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FloatField } from "@web/views/fields/float/float_field";
import { FloatTimeField } from "@web/views/fields/float_time/float_time_field";

/**
 * Widget que fuerza modo readonly real en campos float y float_time.
 * Anula la lógica interna de edición.
 */

export class KeyboardDisabledFloat extends FloatField {
    _isReadonly() {
        return true;
    }
}

registry.category("fields").add("keyboard_disabled", {
    component: KeyboardDisabledFloat,
    supportedTypes: ["float"],
});

export class KeyboardDisabledFloatTime extends FloatTimeField {
    _isReadonly() {
        return true;
    }
}

registry.category("fields").add("keyboard_disabled_float_time", {
    component: KeyboardDisabledFloatTime,
    supportedTypes: ["float"],
});
