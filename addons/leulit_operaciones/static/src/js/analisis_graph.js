/** @odoo-module **/

import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";

// ponytail: la vista graph estandar, solo con otra plantilla de botones (sin
// selector de tipo de grafico ni apilado). Si algun dia hacen falta mas
// personalizaciones, extender aqui Model/Renderer.
registry.category("views").add("leulit_analisis_graph", {
    ...graphView,
    buttonTemplate: "leulit_operaciones.AnalisisGraphButtons",
});
