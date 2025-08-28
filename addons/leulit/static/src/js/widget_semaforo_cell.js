/** @odoo-module **/

import { CharField } from '@web/views/fields/char/char_field';
import { registry } from '@web/core/registry';
import { formatFloatTime } from '@web/views/fields/formatters';

export class SemaforoFloatTimeCell extends CharField {
    _render() {
        const semaforValue = this.props.record.data[this.props.attrs.semafor_field];
        const valor = formatFloatTime(this.props.value);
        let img = '';
        if (semaforValue === 'green') img = 'semaforo_green.png';
        else if (semaforValue === 'red') img = 'semaforo_red.png';
        else if (semaforValue === 'yellow') img = 'semaforo_yellow.png';

        this.el.innerHTML = `
            <span style="display: block;width:100%; text-align:right;vertical-align:middle; padding: 2px">
                <span style="margin-right:10px"><img src="/leulit/static/src/images/${img}"/></span>
                <span style="display:inline-block;width:40px">${valor}</span>
            </span>`;
    }
}
registry.category('fields').add('semaforo_float_time_cell', SemaforoFloatTimeCell);

export class SemaforoIntegerCell extends CharField {
    _render() {
        const semaforValue = this.props.record.data[this.props.attrs.semafor_field];
        let img = '';
        if (semaforValue === 'green') img = 'semaforo_green.png';
        else if (semaforValue === 'red') img = 'semaforo_red.png';
        else if (semaforValue === 'yellow') img = 'semaforo_yellow.png';

        this.el.innerHTML = `
            <span style="display: block;width:100%; text-align:right;vertical-align:middle; padding: 2px">
                <span style="margin-right:10px"><img src="/leulit/static/src/images/${img}"/></span>
                <span style="display:inline-block;width:40px">${this.props.value}</span>
            </span>`;
    }
}
registry.category('fields').add('semaforo_integer_cell', SemaforoIntegerCell);
