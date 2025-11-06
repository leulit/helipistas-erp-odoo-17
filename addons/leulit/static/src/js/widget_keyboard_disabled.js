/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FloatField } from "@web/views/fields/float/float_field";
import { FloatTimeField } from "@web/views/fields/float_time/float_time_field";
import { onMounted } from "@odoo/owl";

/**
 * Desactiva el teclado en campos float y float_time.
 * Previene cualquier modificación manual en el input.
 */

export class KeyboardDisabledFloat extends FloatField {
    setup() {
        super.setup();
        onMounted(() => this._attachBlocker());
    }

    _attachBlocker() {
        const input = this.el?.querySelector("input");
        if (!input) return;

        const block = ev => {
            ev.stopPropagation();
            ev.preventDefault();
            return false;
        };

        ["keydown", "keypress", "input", "paste"].forEach(e =>
            input.addEventListener(e, block)
        );

        input.readOnly = true;
        input.classList.add("o_keyboard_disabled");
    }
}

registry.category("fields").add("keyboard_disabled", {
    component: KeyboardDisabledFloat,
    supportedTypes: ["float"],
});

export class KeyboardDisabledFloatTime extends FloatTimeField {
    setup() {
        super.setup();
        onMounted(() => this._attachBlocker());
    }

    _attachBlocker() {
        const input = this.el?.querySelector("input");
        if (!input) return;

        const block = ev => {
            ev.stopPropagation();
            ev.preventDefault();
            return false;
        };

        ["keydown", "keypress", "input", "paste"].forEach(e =>
            input.addEventListener(e, block)
        );

        input.readOnly = true;
        input.classList.add("o_keyboard_disabled");
    }
}

registry.category("fields").add("keyboard_disabled_float_time", {
    component: KeyboardDisabledFloatTime,
    supportedTypes: ["float"],
});
