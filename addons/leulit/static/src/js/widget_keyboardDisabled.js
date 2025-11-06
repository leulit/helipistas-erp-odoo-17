/** @odoo-module **/

import { registry } from '@web/core/registry';
import { FloatField } from '@web/views/fields/float/float_field';
import { onMounted, onWillUnmount } from '@odoo/owl';

export class KeyboardDisabled extends FloatField {
    setup() {
        super.setup();
        
        // En Odoo 17, usamos hooks del ciclo de vida de OWL
        onMounted(() => {
            // El elemento ya existe aquí
            const input = this.el?.querySelector('input');
            if (input) {
                input.addEventListener('keydown', this._keyboardDisabled);
                input.addEventListener('keypress', this._keyboardDisabled);
                input.addEventListener('input', this._keyboardDisabled);
            }
        });

        onWillUnmount(() => {
            // Limpiar los event listeners al desmontar
            const input = this.el?.querySelector('input');
            if (input) {
                input.removeEventListener('keydown', this._keyboardDisabled);
                input.removeEventListener('keypress', this._keyboardDisabled);
                input.removeEventListener('input', this._keyboardDisabled);
            }
        });
    }

    _keyboardDisabled(ev) {
        // Prevenir cualquier entrada de teclado
        ev.stopPropagation();
        ev.preventDefault();
        return false;
    }
}

registry.category('fields').add('keyboard_disabled', KeyboardDisabled);
