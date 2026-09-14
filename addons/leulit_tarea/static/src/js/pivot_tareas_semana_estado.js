/** @odoo-module **/

import { registry } from "@web/core/registry";
import { onMounted, onPatched } from "@odoo/owl";
import { pivotView } from "@web/views/pivot/pivot_view";
import { PivotModel } from "@web/views/pivot/pivot_model";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";

// ponytail: Odoo agrupa fechas siempre ascendente y no hay atributo de arch
// para invertirlo. `_getTableRows` usa tree.sortedKeys si existe (si no,
// el orden natural del Map). Fijamos ese array invertido solo en el nivel
// raíz (semana) tras cada carga, sin tocar el nivel anidado (usuario).
class TareasSemanaEstadoPivotModel extends PivotModel {
    async load(searchParams) {
        await super.load(searchParams);
        if (this.metaData.rowGroupBys[0] === "create_date:week") {
            const tree = this.data.rowGroupTree;
            if (tree && tree.directSubTrees.size) {
                tree.sortedKeys = [...tree.directSubTrees.keys()].reverse();
            }
        }
    }
}

// ponytail: t-ref="table" apunta directo al <table>; le añadimos una clase
// propia para poder acotar el CSS de cabecera fija solo a esta pantalla.
class TareasSemanaEstadoPivotRenderer extends PivotRenderer {
    setup() {
        super.setup();
        const addScopeClass = () => this.tableRef.el?.classList.add("o_leulit_tareas_semana_pivot");
        onMounted(addScopeClass);
        onPatched(addScopeClass);
    }
}

registry.category("views").add("leulit_tareas_semana_pivot", {
    ...pivotView,
    Model: TareasSemanaEstadoPivotModel,
    Renderer: TareasSemanaEstadoPivotRenderer,
});
