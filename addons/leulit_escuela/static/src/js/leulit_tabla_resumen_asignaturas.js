/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { formView } from "@web/views/form/form_view";

function decimalHourToStr(value) {
    var pattern = '%02d:%02d';
    if (value < 0) {
        value = Math.abs(value);
        pattern = '-' + pattern;
    }
    var hour = Math.floor(value);
    var min = Math.round((value % 1) * 60);
    if (min == 60) {
        min = 0;
        hour = hour + 1;
    }
    return sprintf(pattern, hour, min);
}

export class TablaResumenAsignaturasController extends formView.Controller {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }
}

export class TablaResumenAsignaturasRenderer extends formView.Renderer {
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
        
        // Render templates
        const QWeb = self.env.qweb;
        self.$el.find(self.containerteoricas).html(QWeb.render('escuela_tabla_resumen_asignaturas', {
            tipo: "teoricas",
        }));
        self.$el.find(self.containerpracticas).html(QWeb.render('escuela_tabla_resumen_asignaturas', {
            tipo: "practicas",
        }));

        // Get cursos
        try {
            const result = await self.orm.call('leulit.alumno', 'xmlrpc_cursos', [self.state.resId]);
            $(self.combo_cursos).empty();
            for (var i = 0; i < result.length; i++) {
                var item = result[i];
                var selected = (i == 0) ? " selected='true' " : "";
                self.$('#selector_curso_teoricas').append('<option ' + selected + 'value="' + item['id'] + '">' + item['name'] + '</option>');
            }
            self.getAsignaturas();
        } catch (error) {
            console.error('Error loading cursos:', error);
        }

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
        
        try {
            const r = await self.orm.call('leulit.alumno', 'xmlrpc_asignaturas', [idalumno, idcurso, 'teorica']);
            if (r) {
                self.printTeoricas(r['teoricas']);
                self.printPracticas(r['practicas']);
            }
        } catch (error) {
            console.error('Error loading asignaturas:', error);
        }
    }

    printTeoricas(asignaturas) {
        var self = this;
        var row = '';
        $(self.tabla_teoricas + ' tbody').empty();
        for (var key in asignaturas) {
            var item = asignaturas[key];
            var customcss = (item['duracion'] > item['total_real']) ? "redbackg" : "";
            row += '<tr class="' + customcss + '">';
            row += '<td class="' + customcss + '">';
            row += item['id'];
            row += '</td>';
            row += '<td class="' + customcss + '">';
            row += item['name'];
            row += '</td>';
            row += '<td class="' + customcss + ' halign-center">';
            row += item['strduracion'];
            row += '</td>';
            row += '<td class="' + customcss + ' halign-center">';
            row += item['str_total_real'];
            row += '</td>';
            row += '</tr>';
        }
        $(self.tabla_teoricas + ' tbody').append(row);
    }

    printPracticas(sesiones) {
        var self = this;
        $(self.tabla_practicas + ' tbody').empty();
        var row = '';
        var totales_colum = {
            'duracion': 0.0,
            'total_doblemando': 0.0,
            'total_pic': 0.0,
            'total_spic': 0.0,
            'total_otros': 0.0,
            'total': 0.0
        };
        for (var key in sesiones) {
            var total_row = 0.0
            var item = sesiones[key];
            total_row = item['total_spic'] + item['total_doblemando'] + item['total_pic'] + item['total_otros'];

            var customcss = (item['duracion'] > total_row) ? "redbackg" : "";
            totales_colum['duracion'] += item['duracion'];
            totales_colum['total_doblemando'] += item['total_doblemando'];
            totales_colum['total_pic'] += item['total_pic'];
            totales_colum['total_spic'] += item['total_spic'];
            row += '<tr class="' + customcss + '">';
            row += '<td class="' + customcss + '">';
            row += item['name'];
            row += '</td>';
            row += '<td class="' + customcss + ' halign-center">';
            if (item['duracion'] > 0) {
                row += decimalHourToStr(item['duracion']);
            }
            row += '</td>';
            row += '<td class="' + customcss + ' halign-center">';
            if (item['total_doblemando'] > 0) {
                row += decimalHourToStr(item['total_doblemando']);
            }
            row += '</td>';
            row += '<td class="' + customcss + ' halign-center">';
            if (item['total_pic'] > 0) {
                row += decimalHourToStr(item['total_pic']);
            }
            row += '</td>';
            row += '<td class="' + customcss + ' halign-center">';
            if (item['total_spic'] > 0) {
                row += decimalHourToStr(item['total_spic']);
            }
            row += '</td>';
            row += '<td class="' + customcss + ' halign-center">';
            if (item['total_otros'] > 0) {
                row += decimalHourToStr(item['total_otros']);
            }
            row += '</td>';
            totales_colum['total'] += total_row;
            row += '<td class="' + customcss + ' halign-center">';
            if (total_row > 0) {
                row += decimalHourToStr(total_row);
            }
            row += '</td>';
            row += '</tr>';
        }
        row += "<td>Totales</td>";
        row += '<td class="halign-center">';
        if (totales_colum['duracion'] > 0) {
            row += decimalHourToStr(totales_colum['duracion']);
        }
        row += '</td>';
        row += '<td class="halign-center">';
        if (totales_colum['total_doblemando'] > 0) {
            row += decimalHourToStr(totales_colum['total_doblemando']);
        }
        row += '</td>';
        row += '<td class="halign-center">';
        if (totales_colum['total_pic'] > 0) {
            row += decimalHourToStr(totales_colum['total_pic']);
        }
        row += '</td>';
        row += '<td class="halign-center">';
        if (totales_colum['total_spic'] > 0) {
            row += decimalHourToStr(totales_colum['total_spic']);
        }
        row += '</td>';
        row += '<td class="halign-center">';
        if (totales_colum['total_otros'] > 0) {
            row += decimalHourToStr(totales_colum['total_otros']);
        }
        row += '</td>';
        row += '<td class="halign-center">';
        row += decimalHourToStr(totales_colum['total']);
        row += '</td>';
        $(self.tabla_practicas + ' tbody').append(row);
    }
}

export const TablaResumenAsignaturasView = {
    ...formView,
    type: "tabla_resumen_asignaturas",
    Controller: TablaResumenAsignaturasController,
    Renderer: TablaResumenAsignaturasRenderer,
};

registry.category("views").add("tabla_resumen_asignaturas", TablaResumenAsignaturasView);