/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

function applyEstado(ctrl) {
    const root = ctrl.model?.root;
    if (!root) return;

    const data = root.data || {};
    const estado = data.estado || data.state || data.status;
    const targets = {
        postvuelo: "vista-postvuelo",
        cerrado: "vista-cerrado",
        cancelado: "vista-cancelado",
    };
    const targetId = targets[estado];
    if (!targetId) return;

    const btn = document.getElementById(targetId);
    if (!btn) return;

    setTimeout(() => btn?.click(), 0);
}

const _fcMounted = FormController.prototype.mounted;
const _fcOnSaved = FormController.prototype.onRecordSaved;
const _fcOnWillSave = FormController.prototype.onWillSave;

patch(FormController.prototype, {
    name: "leulit_operaciones.pag_cargada",

    mounted() {
        if (_fcMounted) _fcMounted.apply(this, arguments);
        applyEstado(this);
    },

    async onRecordSaved() {
        const r = _fcOnSaved ? await _fcOnSaved.apply(this, arguments) : undefined;
        applyEstado(this);
        return r;
    },

    async onWillSave() {
        return _fcOnWillSave ? _fcOnWillSave.apply(this, arguments) : undefined;
    },
});
