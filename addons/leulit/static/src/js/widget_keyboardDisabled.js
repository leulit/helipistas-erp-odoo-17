/** @odoo-module **/

import { registry } from '@web/core/registry';
import { CharField } from '@web/views/fields/char/char_field';
import { FloatField } from '@web/views/fields/float/float_field';
import { onMounted, onWillUnmount } from '@odoo/owl';

// Mixin para añadir funcionalidad de teclado deshabilitado
const keyboardDisabledMixin = {
    setup() {
        super.setup();
        
        onMounted(() => {
            const input = this.el?.querySelector('input');
            if (input) {
                this._boundHandler = this._keyboardDisabled.bind(this);
                input.addEventListener('keydown', this._boundHandler);
                input.addEventListener('keypress', this._boundHandler);
                input.addEventListener('input', this._boundHandler);
                input.addEventListener('paste', this._boundHandler);
                // Añadir estilo visual
                input.style.backgroundColor = '#f9f9f9';
                input.style.cursor = 'not-allowed';
            }
        });

        onWillUnmount(() => {
            const input = this.el?.querySelector('input');
            if (input && this._boundHandler) {
                input.removeEventListener('keydown', this._boundHandler);
                input.removeEventListener('keypress', this._boundHandler);
                input.removeEventListener('input', this._boundHandler);
                input.removeEventListener('paste', this._boundHandler);
            }
        });
    },

    _keyboardDisabled(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        return false;
    }
};

// Widget para campos Float
export class KeyboardDisabledFloat extends FloatField {
    setup() {
        keyboardDisabledMixin.setup.call(this);
    }
    _keyboardDisabled(ev) {
        keyboardDisabledMixin._keyboardDisabled.call(this, ev);
    }
}

// Widget para campos Char
export class KeyboardDisabledChar extends CharField {
    setup() {
        keyboardDisabledMixin.setup.call(this);
    }
    _keyboardDisabled(ev) {
        keyboardDisabledMixin._keyboardDisabled.call(this, ev);
    }
}

// Registrar el widget para Float por defecto (usado en la mayoría de casos)
registry.category('fields').add('keyboard_disabled', KeyboardDisabledFloat);
registry.category('fields').add('keyboard_disabled_char', KeyboardDisabledChar);
