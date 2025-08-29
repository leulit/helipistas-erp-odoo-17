/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { formView } from "@web/views/form/form_view";

function decimalHourToStr(value) {
    let pattern = '%02d:%02d';
    if (value < 0) {
        value = Math.abs(value);
        pattern = '-' + pattern;
    }
    let hour = Math.floor(value);
    let min = Math.round((value % 1) * 60);
    if (min == 60) {
        min = 0;
        hour = hour + 1;
    }
    return sprintf(pattern, hour, min);
}

export class TablaResumenAsignaturasVueloController extends formView.Controller {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async _applyChanges(dataPointID, changes, event) {
        const result = await super._applyChanges(dataPointID, changes, event);
        
        if (this.model.localData[dataPointID].data.rel_curso && this.model.localData[dataPointID].data.rel_curso.data) {
            await this.renderer.getAsignaturas(this.model.localData[dataPointID].data.rel_curso.data.id);
        } else {
            await this.renderer.getAsignaturas(false);
        }
        
        return result;
    }
}

export class TablaResumenAsignaturasVueloRenderer extends formView.Renderer {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.combo_cursos = '#selector_curso_teoricas';
        this.tabla_teoricas = '#tabla_resumen_teoricas';
        this.tabla_practicas = '#tabla_resumen_practicas';
        this.containerteoricas = '#container_tabla_asignaturas_teoricas';
        this.containerpracticas = '#container_tabla_asignaturas_practicas';
    }

    async _renderView() {
        await super._renderView();
        const self = this;
        const QWeb = self.env.qweb;
        self.$el.find(self.containerteoricas).html(QWeb.render('escuela_tabla_resumen_asignaturas', { tipo: "teoricas" }));
        self.$el.find(self.containerpracticas).html(QWeb.render('escuela_tabla_resumen_asignaturas', { tipo: "practicas" }));

        // Get cursos
        const result = await self.orm.call('leulit.alumno', 'xmlrpc_cursos', [self.state.resId]);
        $(self.combo_cursos).empty();
        for (let i = 0; i < result.length; i++) {
            const item = result[i];
            const selected = (i == 0) ? " selected='true' " : "";
            self.$('#selector_curso_teoricas').append('<option ' + selected + 'value="' + item['id'] + '">' + item['name'] + '</option>');
        }
        self.getAsignaturas();
        self.$(self.combo_cursos).change(function() {
            self.getAsignaturas();
        });
    }

    getCursoSelected() {
        return this.$(this.combo_cursos).find('option:selected').val();
    }

    async getAsignaturas() {
        const self = this;
        const idalumno = self.state.resId;
        const idcurso = self.getCursoSelected();
        const r = await self.orm.call('leulit.alumno', 'xmlrpc_asignaturas', [idalumno, idcurso, 'teorica']);
        if (r) {
            self.printTeoricas(r['teoricas']);
            self.printPracticas(r['practicas']);
        }
    }

    printTeoricas(asignaturas) {
        const self = this;
        let row = '';
        $(self.tabla_teoricas + ' tbody').empty();
        for (const key in asignaturas) {
            const item = asignaturas[key];
            const customcss = (item['duracion'] > item['total_real']) ? "redbackg" : "";
            row += '<tr class="' + customcss + '">';
            row += '<td class="' + customcss + '">' + item['id'] + '</td>';
            row += '<td class="' + customcss + '">' + item['name'] + '</td>';
            row += '<td class="' + customcss + ' halign-center">' + item['strduracion'] + '</td>';
            row += '<td class="' + customcss + ' halign-center">' + item['str_total_real'] + '</td>';
            row += '</tr>';
        }
        $(self.tabla_teoricas + ' tbody').append(row);
    }

    printPracticas(sesiones) {
        const self = this;
        $(self.tabla_practicas + ' tbody').empty();
        let row = '';
        const totales_colum = {
            'duracion': 0.0,
            'total_doblemando': 0.0,
            'total_pic': 0.0,
            'total_spic': 0.0,
            'total_otros': 0.0,
            'total': 0.0
        };
        for (const key in sesiones) {
            let total_row = 0.0;
            const item = sesiones[key];
            total_row = item['total_spic'] + item['total_doblemando'] + item['total_pic'] + item['total_otros'];
            const customcss = (item['duracion'] > total_row) ? "redbackg" : "";
            totales_colum['duracion'] += item['duracion'];
            totales_colum['total_doblemando'] += item['total_doblemando'];
            totales_colum['total_pic'] += item['total_pic'];
            totales_colum['total_spic'] += item['total_spic'];
            row += '<tr class="' + customcss + '">';
            row += '<td class="' + customcss + '">' + item['name'] + '</td>';
            row += '<td class="' + customcss + ' halign-center">' + (item['duracion'] > 0 ? decimalHourToStr(item['duracion']) : '') + '</td>';
            row += '<td class="' + customcss + ' halign-center">' + (item['total_doblemando'] > 0 ? decimalHourToStr(item['total_doblemando']) : '') + '</td>';
            row += '<td class="' + customcss + ' halign-center">' + (item['total_pic'] > 0 ? decimalHourToStr(item['total_pic']) : '') + '</td>';
            row += '<td class="' + customcss + ' halign-center">' + (item['total_spic'] > 0 ? decimalHourToStr(item['total_spic']) : '') + '</td>';
            row += '<td class="' + customcss + ' halign-center">' + (item['total_otros'] > 0 ? decimalHourToStr(item['total_otros']) : '') + '</td>';
            totales_colum['total'] += total_row;
            row += '<td class="' + customcss + ' halign-center">' + (total_row > 0 ? decimalHourToStr(total_row) : '') + '</td>';
            row += '</tr>';
        }
        row += "<td>Totales</td>";
        row += '<td class="halign-center">' + (totales_colum['duracion'] > 0 ? decimalHourToStr(totales_colum['duracion']) : '') + '</td>';
        row += '<td class="halign-center">' + (totales_colum['total_doblemando'] > 0 ? decimalHourToStr(totales_colum['total_doblemando']) : '') + '</td>';
        row += '<td class="halign-center">' + (totales_colum['total_pic'] > 0 ? decimalHourToStr(totales_colum['total_pic']) : '') + '</td>';
        row += '<td class="halign-center">' + (totales_colum['total_spic'] > 0 ? decimalHourToStr(totales_colum['total_spic']) : '') + '</td>';
        row += '<td class="halign-center">' + (totales_colum['total_otros'] > 0 ? decimalHourToStr(totales_colum['total_otros']) : '') + '</td>';
        row += '<td class="halign-center">' + decimalHourToStr(totales_colum['total']) + '</td>';
        $(self.tabla_practicas + ' tbody').append(row);
    }
}

export const TablaResumenAsignaturasVueloView = {
    ...formView,
    type: "tabla_resumen_asignaturas_vuelo",
    Controller: TablaResumenAsignaturasVueloController,
    Renderer: TablaResumenAsignaturasVueloRenderer,
};

registry.category("views").add("tabla_resumen_asignaturas_vuelo", TablaResumenAsignaturasVueloView);