/** @odoo-module **/

import { CharField } from '@web/views/fields/char/char_field';
import { registry } from '@web/core/registry';
import { BooleanField } from '@web/views/fields/boolean/boolean_field'

export class SemaforoBool extends BooleanField {}
// Vinculamos el componente a su plantilla QWeb
SemaforoChar.template = "leulit.SemaforoBooleanField";

registry.category('fields').add('semaforo_bool', SemaforoBool);


export class SemaforoChar extends CharField {}

// Vinculamos el componente a su plantilla QWeb
SemaforoChar.template = "leulit.SemaforoCharField";

registry.category("fields").add("semaforo_char", SemaforoChar);