/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FloatField } from "@web/views/fields/float/float_field";
import { FloatTimeField } from "@web/views/fields/float_time/float_time_field";
import { onRendered } from "@odoo/owl";

/**
 * Bloquea teclado y entrada en campos float o float_time.
 */

export class KeyboardDisabledFloat extends FloatField {
    setup() {
        super.setup();
        onRendered(() => this._disableInput());
    }

    _disableInput() {
        const input = this.el.querySelector("input");
        if (!input) return;

        input.addEventListener("keydown", ev => ev.preventDefault());
        input.addEventListener("keypress", ev => ev.preventDefault());
        input.addEventListener("input", ev => ev.preventDefault());
        input.readOnly = true; // impide edición manual
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
        onRendered(() => this._disableInput());
    }

    _disableInput() {
        const input = this.el.querySelector("input");
        if (!input) return;

        input.addEventListener("keydown", ev => ev.preventDefault());
        input.addEventListener("keypress", ev => ev.preventDefault());
        input.addEventListener("input", ev => ev.preventDefault());
        input.readOnly = true;
        input.classList.add("o_keyboard_disabled");
    }
}

registry.category("fields").add("keyboard_disabled_float_time", {
    component: KeyboardDisabledFloatTime,
    supportedTypes: ["float"],
});
