/** @odoo-module **/

import { CharField } from '@web/views/fields/char/char_field';
import { registry } from '@web/core/registry';
import { BooleanField } from '@web/views/fields/boolean/boolean_field'

export class SemaforoBool extends BooleanField {
    _render() {
        const value = this.props.value;
        this.el.innerHTML = value
            ? '<img src="/leulit/static/src/images/semaforo_green.png"/>'
            : '<img src="/leulit/static/src/images/semaforo_red.png"/>';
    }
}
registry.category('fields').add('semaforo_bool', SemaforoBool);

export class SemaforoChar extends CharField {
    _render() {
        if (!this.props.value) {
            this.el.innerHTML = 'N.A.';
            return;
        }
        const value = this.props.value.toLowerCase();
        let img = 'semaforo_red.png';
        if (value === 'green') img = 'semaforo_green.png';
        else if (value === 'yellow') img = 'semaforo_yellow.png';
        else if (value !== 'red') {
            this.el.innerHTML = 'N.A.';
            return;
        }
        this.el.innerHTML = `<img src="/leulit/static/src/images/${img}"/>`;
    }
}
registry.category('fields').add('semaforo_char', SemaforoChar);
