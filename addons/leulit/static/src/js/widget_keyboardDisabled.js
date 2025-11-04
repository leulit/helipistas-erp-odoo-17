/** @odoo-module **/

// import { FieldFloat, FieldFloatTime } from '@web/views/fields/basic_fields';
import { registry } from '@web/core/registry';
import { FloatField } from '@web/views/fields/float/float_field';

export class KeyboardDisabled extends FloatField {
    setup() {
        super.setup();
        this.el?.addEventListener('keypress', this._keyboardDisabled);
    }

    _keyboardDisabled(ev) {
        ev.stopPropagation();
        ev.preventDefault();
    }
}


registry.category('fields').add('keyboard_disabled', KeyboardDisabled);
