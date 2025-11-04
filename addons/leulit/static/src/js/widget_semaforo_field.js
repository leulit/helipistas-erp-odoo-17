/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { CharField } from "@web/views/fields/char/char_field";
import { formatFloatTime } from "@web/views/fields/formatters";
import { Component } from "@odoo/owl";

// ---------- SEMAFORO BOOLEAN ----------
export class SemaforoBool extends Component {
    static template = "leulit.SemaforoBool";
    static props = standardFieldProps;

    get imageUrl() {
        return this.props.record.data[this.props.name]
            ? "/leulit/static/src/images/semaforo_green.png"
            : "/leulit/static/src/images/semaforo_red.png";
    }
}

registry.category("fields").add("semaforo_bool", {
    component: SemaforoBool,
    supportedTypes: ["boolean"],
});

// ---------- SEMAFORO CHAR ----------
export class SemaforoChar extends Component {
    static template = "leulit.SemaforoChar";
    static props = standardFieldProps;

    get imageUrl() {
        const value = (this.props.record.data[this.props.name] || "").toLowerCase();
        if (value === "green") return "/leulit/static/src/images/semaforo_green.png";
        if (value === "yellow") return "/leulit/static/src/images/semaforo_yellow.png";
        if (value === "red") return "/leulit/static/src/images/semaforo_red.png";
        return null;
    }

    get textValue() {
        return this.imageUrl ? "" : "N.A.";
    }
}

registry.category("fields").add("semaforo_char", {
    component: SemaforoChar,
    supportedTypes: ["char"],
});


// Función utilitaria compartida
function getSemaforoImage(value) {
    if (!value) return null;
    const val = value.toLowerCase();
    if (val === "green") return "/leulit/static/src/images/semaforo_green.png";
    if (val === "yellow") return "/leulit/static/src/images/semaforo_yellow.png";
    if (val === "red") return "/leulit/static/src/images/semaforo_red.png";
    return null;
}

// ---------- SEMAFORO FLOAT TIME ----------
export class SemaforoFloatTimeCell extends Component {
    static template = "leulit.SemaforoFloatTimeCell";
    static props = standardFieldProps;

    get imageUrl() {
        const field = this.props.record.data[this.props.attrs.semafor_field];
        return getSemaforoImage(field);
    }

    get valueDisplay() {
        return formatFloatTime(this.props.record.data[this.props.name]) || "";
    }
}

registry.category("fields").add("semaforo_float_time_cell", {
    component: SemaforoFloatTimeCell,
    supportedTypes: ["float"],
});

// ---------- SEMAFORO INTEGER ----------
export class SemaforoIntegerCell extends Component {
    static template = "leulit.SemaforoIntegerCell";
    static props = standardFieldProps;

    get imageUrl() {
        const field = this.props.record.data[this.props.attrs.semafor_field];
        return getSemaforoImage(field);
    }

    get valueDisplay() {
        return this.props.record.data[this.props.name] ?? "";
    }
}

registry.category("fields").add("semaforo_integer_cell", {
    component: SemaforoIntegerCell,
    supportedTypes: ["integer", "char"],
});