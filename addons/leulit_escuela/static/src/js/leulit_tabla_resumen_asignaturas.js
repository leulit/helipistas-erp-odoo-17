/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { formView } from "@web/views/form/form_view";
import { FormRenderer } from "@web/views/form/form_renderer";
import { onMounted, onWillStart, useRef, useState } from "@odoo/owl";

/**
 * Convierte horas decimales a formato HH:MM
 * @param {number} value - Valor en horas decimales
 * @returns {string} Formato HH:MM
 */
function decimalHourToStr(value) {
    let pattern = '%02d:%02d';
    if (value < 0) {
        value = Math.abs(value);
        pattern = '-' + pattern;
    }
    let hour = Math.floor(value);
    let min = Math.round((value % 1) * 60);
    if (min === 60) {
        min = 0;
        hour = hour + 1;
    }
    return sprintf(pattern, hour, min);
}

export class TablaResumenAsignaturasRenderer extends FormRenderer {
    static template = "leulit_escuela.TablaResumenAsignaturas";

    setup() {
        super.setup();
        this.orm = useService("orm");
        
        // Referencias a elementos del DOM
        this.selectorCurso = useRef("selectorCurso");
        this.tablaTeoricasBody = useRef("tablaTeoricasBody");
        this.tablaPracticasBody = useRef("tablaPracticasBody");
        
        // Estado local
        this.state = useState({
            cursos: [],
            cursoSeleccionado: null,
        });

        onWillStart(async () => {
            await this.loadCursos();
        });

        onMounted(() => {
            this.setupEventListeners();
        });
    }

    /**
     * Carga la lista de cursos del alumno
     */
    async loadCursos() {
        const resId = this.props.record.resId;
        if (!resId) {
            return;
        }

        try {
            const result = await this.orm.call('leulit.alumno', 'xmlrpc_cursos', [resId]);
            this.state.cursos = result || [];
            if (this.state.cursos.length > 0) {
                this.state.cursoSeleccionado = this.state.cursos[0].id;
                await this.loadAsignaturas();
            }
        } catch (error) {
            console.error('Error loading cursos:', error);
        }
    }

    /**
     * Configura los event listeners
     */
    setupEventListeners() {
        if (this.selectorCurso.el) {
            this.selectorCurso.el.addEventListener('change', () => {
                this.onCursoChange();
            });
        }
    }

    /**
     * Maneja el cambio de curso seleccionado
     */
    async onCursoChange() {
        if (this.selectorCurso.el) {
            this.state.cursoSeleccionado = parseInt(this.selectorCurso.el.value);
            await this.loadAsignaturas();
        }
    }

    /**
     * Carga las asignaturas del curso seleccionado
     */
    async loadAsignaturas() {
        const resId = this.props.record.resId;
        const idCurso = this.state.cursoSeleccionado;
        
        if (!resId || !idCurso) {
            return;
        }

        try {
            const result = await this.orm.call(
                'leulit.alumno', 
                'xmlrpc_asignaturas', 
                [resId, idCurso, 'teorica']
            );
            
            if (result) {
                this.renderTeoricas(result.teoricas || []);
                this.renderPracticas(result.practicas || []);
            }
        } catch (error) {
            console.error('Error loading asignaturas:', error);
        }
    }

    /**
     * Renderiza la tabla de asignaturas teóricas
     * @param {Array} asignaturas - Lista de asignaturas teóricas
     */
    renderTeoricas(asignaturas) {
        if (!this.tablaTeoricasBody.el) {
            return;
        }

        let html = '';
        for (const item of asignaturas) {
            const customCss = (item.duracion > item.total_real) ? "redbackg" : "";
            html += `
                <tr class="${customCss}">
                    <td class="${customCss}">${item.id}</td>
                    <td class="${customCss}">${item.name}</td>
                    <td class="${customCss} halign-center">${item.strduracion}</td>
                    <td class="${customCss} halign-center">${item.str_total_real}</td>
                </tr>
            `;
        }
        
        this.tablaTeoricasBody.el.innerHTML = html;
    }

    /**
     * Renderiza la tabla de sesiones prácticas
     * @param {Array} sesiones - Lista de sesiones prácticas
     */
    renderPracticas(sesiones) {
        if (!this.tablaPracticasBody.el) {
            return;
        }

        let html = '';
        const totales = {
            duracion: 0.0,
            total_doblemando: 0.0,
            total_pic: 0.0,
            total_spic: 0.0,
            total_otros: 0.0,
            total: 0.0
        };

        for (const item of sesiones) {
            const totalRow = item.total_spic + item.total_doblemando + 
                           item.total_pic + item.total_otros;
            const customCss = (item.duracion > totalRow) ? "redbackg" : "";

            // Acumular totales
            totales.duracion += item.duracion;
            totales.total_doblemando += item.total_doblemando;
            totales.total_pic += item.total_pic;
            totales.total_spic += item.total_spic;
            totales.total_otros += item.total_otros;
            totales.total += totalRow;

            html += `
                <tr class="${customCss}">
                    <td class="${customCss}">${item.name}</td>
                    <td class="${customCss} halign-center">
                        ${item.duracion > 0 ? decimalHourToStr(item.duracion) : ''}
                    </td>
                    <td class="${customCss} halign-center">
                        ${item.total_doblemando > 0 ? decimalHourToStr(item.total_doblemando) : ''}
                    </td>
                    <td class="${customCss} halign-center">
                        ${item.total_pic > 0 ? decimalHourToStr(item.total_pic) : ''}
                    </td>
                    <td class="${customCss} halign-center">
                        ${item.total_spic > 0 ? decimalHourToStr(item.total_spic) : ''}
                    </td>
                    <td class="${customCss} halign-center">
                        ${item.total_otros > 0 ? decimalHourToStr(item.total_otros) : ''}
                    </td>
                    <td class="${customCss} halign-center">
                        ${totalRow > 0 ? decimalHourToStr(totalRow) : ''}
                    </td>
                </tr>
            `;
        }

        // Fila de totales
        html += `
            <tr class="font-weight-bold">
                <td>Totales</td>
                <td class="halign-center">
                    ${totales.duracion > 0 ? decimalHourToStr(totales.duracion) : ''}
                </td>
                <td class="halign-center">
                    ${totales.total_doblemando > 0 ? decimalHourToStr(totales.total_doblemando) : ''}
                </td>
                <td class="halign-center">
                    ${totales.total_pic > 0 ? decimalHourToStr(totales.total_pic) : ''}
                </td>
                <td class="halign-center">
                    ${totales.total_spic > 0 ? decimalHourToStr(totales.total_spic) : ''}
                </td>
                <td class="halign-center">
                    ${totales.total_otros > 0 ? decimalHourToStr(totales.total_otros) : ''}
                </td>
                <td class="halign-center">
                    ${decimalHourToStr(totales.total)}
                </td>
            </tr>
        `;

        this.tablaPracticasBody.el.innerHTML = html;
    }
}

export const TablaResumenAsignaturasView = {
    ...formView,
    Renderer: TablaResumenAsignaturasRenderer,
};

registry.category("views").add("tabla_resumen_asignaturas", TablaResumenAsignaturasView);