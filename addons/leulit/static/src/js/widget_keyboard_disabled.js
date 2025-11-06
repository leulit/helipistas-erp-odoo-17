/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FloatField } from "@web/views/fields/float/float_field";
import { FloatTimeField } from "@web/views/fields/float_time/float_time_field";
import { onMounted, onWillUnmount } from "@odoo/owl";

/**
 * Campos float/float_time con teclado bloqueado (sin edición manual).
 */

function protectInput(el) {
    const input = el?.querySelector("input");
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

export class KeyboardDisabledFloat extends FloatField {
    setup() {
        super.setup();
        this._observer = null;
        onMounted(() => this._startObserver());
        onWillUnmount(() => this._stopObserver());
    }

    _startObserver() {
        const target = this.el;
        if (!target) return;
        protectInput(target);

        this._observer = new MutationObserver(() => protectInput(target));
        this._observer.observe(target, { childList: true, subtree: true });
    }

    _stopObserver() {
        if (this._observer) {
            this._observer.disconnect();
            this._observer = null;
        }
    }
}

registry.category("fields").add("keyboard_disabled", {
    component: KeyboardDisabledFloat,
    supportedTypes: ["float"],
});

export class KeyboardDisabledFloatTime extends FloatTimeField {
    setup() {
        super.setup();
        this._observer = null;
        onMounted(() => this._startObserver());
        onWillUnmount(() => this._stopObserver());
    }

    _startObserver() {
        const target = this.el;
        if (!target) return;
        protectInput(target);

        this._observer = new MutationObserver(() => protectInput(target));
        this._observer.observe(target, { childList: true, subtree: true });
    }

    _stopObserver() {
        if (this._observer) {
            this._observer.disconnect();
            this._observer = null;
        }
    }
}

registry.category("fields").add("keyboard_disabled_float_time", {
    component: KeyboardDisabledFloatTime,
    supportedTypes: ["float"],
});
