/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { FloatField } from "@web/views/fields/float/float_field";
import { FloatTimeField } from "@web/views/fields/float_time/float_time_field";
import { Component, onMounted } from "@odoo/owl";

// ---------- FLOAT ----------
export class KeyboardDisabledFloat extends Component {
    static template = "leulit.KeyboardDisabledFloat";
    static props = standardFieldProps;

    setup() {
        super.setup();
        onMounted(() => {
            this.el.addEventListener("keypress", this._disableKeyboard);
        });
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

// ---------- FLOAT TIME ----------
export class KeyboardDisabledFloatTime extends Component {
    static template = "leulit.KeyboardDisabledFloatTime";
    static props = standardFieldProps;

    setup() {
        super.setup();
        onMounted(() => {
            this.el.addEventListener("keypress", this._disableKeyboard);
        });
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
