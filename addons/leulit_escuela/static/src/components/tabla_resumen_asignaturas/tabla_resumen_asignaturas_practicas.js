/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

function decimalHourToStr(value) {
    let negative = false;
    if (typeof value !== "number" || isNaN(value)) {
        return "";
    }
    if (value < 0) {
        value = Math.abs(value);
        negative = true;
    }
    const hour = Math.floor(value);
    let min = Math.round((value % 1) * 60);
    const h = min === 60 ? hour + 1 : hour;
    const m = min === 60 ? 0 : min;
    const str = `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
    return negative ? `-${str}` : str;
}

export class TablaResumenAsignaturasPracticas extends Component {
    static template = "leulit.TablaResumenAsignaturasPracticas";

    setup() {
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        // Extraer el ID real del alumno desde el campo rel_alumnos (relacional)
        const alumnoId = this.props.record.rel_alumnos?.records?.[0]?.res_id || null;
        this.state = useState({
            practicas: [],  // [{name,duracion,total_doblemando,total_pic,total_spic,total_otros}]
            cursoId: this.props.record.data.rel_curso, // El curso viene del formulario
            alumnoId: alumnoId, // El alumno viene del formulario (ID real)
        });

        onWillStart(async () => {
            await this._loadAsignaturasPracticas();
        });
    }

    async onWillUpdateProps(nextProps) {
        const nextCursoId = nextProps.record.data.rel_curso;
        if (nextCursoId !== this.state.cursoId) {
            this.state.cursoId = nextCursoId;
            await this._loadAsignaturasPracticas();
        }
    }

    async _loadAsignaturasPracticas() {
        if (!this.state.cursoId) {
            this.state.practicas = [];
            return;
        }
        const r = await this.rpc("/web/dataset/call_kw/leulit.alumno/xmlrpc_asignaturas", {
            model: "leulit.alumno",
            method: "xmlrpc_asignaturas",
            args: [this.state.alumnoId, this.state.cursoId, "practica"],
            kwargs: {},
        });
        this.state.practicas = Array.isArray(r?.practicas) ? r.practicas : Object.values(r?.practicas || {});
    }

    rowPracticasClass(it) {
        const total = (it.total_spic || 0) + (it.total_doblemando || 0) + (it.total_pic || 0) + (it.total_otros || 0);
        if (total < (it.duracion || 0)) {
            return "redbackg";
        } else if (total >= (it.duracion || 0)) {
            return "greenbackg";
        }
        return "";
    }
    fmtHour(v) {
        return v > 0 ? decimalHourToStr(v) : "";
    }
    totalesPracticas() {
        const t = { duracion: 0, total_doblemando: 0, total_pic: 0, total_spic: 0, total_otros: 0 };
        for (const it of this.state.practicas) {
            t.duracion += it.duracion || 0;
            t.total_doblemando += it.total_doblemando || 0;
            t.total_pic += it.total_pic || 0;
            t.total_spic += it.total_spic || 0;
            t.total_otros += it.total_otros || 0;
        }
        const total = t.total_doblemando + t.total_pic + t.total_spic + t.total_otros;
        return { ...t, total };
    }
}

registry.category("view_widgets").add("leulit_tabla_resumen_asignaturas_practicas", {
    component: TablaResumenAsignaturasPracticas,
});
