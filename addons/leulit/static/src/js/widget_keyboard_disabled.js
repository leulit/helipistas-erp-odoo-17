/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FloatField } from "@web/views/fields/float/float_field";
import { FloatTimeField } from "@web/views/fields/float_time/float_time_field";

export class KeyboardDisabledFloat extends FloatField {
    setup() {
        super.setup();
        // anula el comportamiento de teclado
        this.el?.addEventListener("keypress", this._disableKeyboard.bind(this));
    }

    _disableKeyboard(ev) {
        ev.stopPropagation();
        ev.preventDefault();
    }
}

registry.category("fields").add("keyboard_disabled", {
    component: KeyboardDisabledFloat,
    supportedTypes: ["float"],
});

export class KeyboardDisabledFloatTime extends FloatTimeField {
    setup() {
        super.setup();
        this.el?.addEventListener("keypress", this._disableKeyboard.bind(this));
    }

    _disableKeyboard(ev) {
        ev.stopPropagation();
        ev.preventDefault();
    }
}

registry.category("fields").add("keyboard_disabled_float_time", {
    component: KeyboardDisabledFloatTime,
    supportedTypes: ["float"],
});
