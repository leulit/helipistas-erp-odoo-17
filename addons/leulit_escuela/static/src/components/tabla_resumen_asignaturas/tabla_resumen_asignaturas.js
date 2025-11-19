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

export class TablaResumenAsignaturas extends Component {
    static template = "leulit.TablaResumenAsignaturas";

    setup() {
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.state = useState({
            cursos: [],
            cursoId: null,
            teoricas: [],   // [{id,name,strduracion,str_total_real,duracion,total_real}]
            practicas: [],  // [{name,duracion,total_doblemando,total_pic,total_spic,total_otros}]
            alumnoId: null,
            activeTab: 'teoricas',
        });

        onWillStart(async () => {
            // resId del registro actual en la vista
            this.state.alumnoId = this.props.record.resId;
            await this._loadCursos();
            await this._loadAsignaturas();
        });
    }

    setActiveTab(tab) {
        if (this.state.activeTab !== tab) {
            this.state.activeTab = tab;
        }
    }

    async _loadCursos() {
        const res = await this.rpc("/web/dataset/call_kw/leulit.alumno/xmlrpc_cursos", {
            model: "leulit.alumno",
            method: "xmlrpc_cursos",
            args: [[this.state.alumnoId]],
            kwargs: {},
        });
        // Convierte a array si el backend devuelve objeto
        this.state.cursos = Array.isArray(res) ? res : Object.values(res || {});
        this.state.cursoId = this.state.cursos.length ? this.state.cursos[0].id : null;
    }

    async _loadAsignaturas() {
        if (!this.state.cursoId) {
            this.state.teoricas = [];
            this.state.practicas = [];
            return;
        }
        const r = await this.rpc("/web/dataset/call_kw/leulit.alumno/xmlrpc_asignaturas", {
            model: "leulit.alumno",
            method: "xmlrpc_asignaturas",
            args: [this.state.alumnoId, this.state.cursoId, "teorica"],
            kwargs: {},
        });
        // Convierte a array si el backend devuelve objeto
        this.state.teoricas = Array.isArray(r?.teoricas) ? r.teoricas : Object.values(r?.teoricas || {});
        this.state.practicas = Array.isArray(r?.practicas) ? r.practicas : Object.values(r?.practicas || {});
    }

    onCursoChange(ev) {
        this.state.cursoId = Number(ev.target.value);
        this._loadAsignaturas();
    }

    // helpers de plantilla
    rowTeoricasClass(it) {
        return it.duracion > it.total_real ? "redbackg" : "";
    }
    rowPracticasClass(it) {
        const total = (it.total_spic || 0) + (it.total_doblemando || 0) + (it.total_pic || 0) + (it.total_otros || 0);
        return (it.duracion || 0) > total ? "redbackg" : "";
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

registry.category("view_widgets").add("leulit_tabla_resumen_asignaturas", {
    component: TablaResumenAsignaturas,
});
