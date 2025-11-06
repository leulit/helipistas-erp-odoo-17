/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FloatField } from "@web/views/fields/float/float_field";
import { FloatTimeField } from "@web/views/fields/float_time/float_time_field";
import { onMounted } from "@odoo/owl";

/**
 * Función helper para deshabilitar el evento keypress.
 * Previene la propagación y la acción por defecto (escribir).
 */
const _keyboardDisabled = (ev) => {
    ev.stopPropagation();
    ev.preventDefault();
};

/**
 * Componente que extiende FloatField y deshabilita la entrada por teclado.
 */
export class KeyboardDisabledFloatField extends FloatField {
    setup() {
        super.setup();
        
        onMounted(() => {
            // this.input es el 't-ref' al elemento <input> en la plantilla original
            if (this.input && this.input.el) {
                this.input.el.addEventListener('keypress', _keyboardDisabled);
            }
        });
    }
}
// Forzamos al componente a usar la plantilla (template) del padre
KeyboardDisabledFloatField.template = "web.FloatField";

/**
 * Componente que extiende FloatTimeField y deshabilita la entrada por teclado.
 */
export class KeyboardDisabledFloatTimeField extends FloatTimeField {
    setup() {
        super.setup();

        onMounted(() => {
            // this.input es el 't-ref' al elemento <input> en la plantilla original
            if (this.input && this.input.el) {
                this.input.el.addEventListener('keypress', _keyboardDisabled);
            }
        });
    }
}
// Forzamos al componente a usar la plantilla (template) del padre
KeyboardDisabledFloatTimeField.template = "web.FloatTimeField";

/**
 * Registro de los nuevos componentes de campo
 */
registry.category("fields").add("keyboard_disabled", KeyboardDisabledFloatField);
registry.category("fields").add("keyboard_disabled_float_time", KeyboardDisabledFloatTimeField);