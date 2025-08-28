/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormController } from "@web/views/form/form_controller";

/* ---- Constantes y utilidades de dibujo ---- */
const CanvasWidth = 400;
const CanvasHeight = 200;

const Polygons = {
    "R22": {
        long: [
            { y: 417, x: 242.6 }, { y: 417, x: 259.08 }, { y: 532.9, x: 259.08 },
            { y: 621.4, x: 254.0 }, { y: 621.4, x: 245.1 }, { y: 578.33, x: 242.6 },
        ],
        lat: [
            { y: -5.58, x: 246.38 }, { y: -5.58, x: 248.92 }, { y: -1.27, x: 259.08 },
            { y: 3.04, x: 259.08 }, { y: 6.6, x: 248.92 }, { y: 2.54, x: 242.57 },
            { y: -2.32, x: 242.57 },
        ],
    },
    "R44": {
        long: [
            { y: 703, x: 233.68 }, { y: 703, x: 260.0 }, { y: 907, x: 260.0 },
            { y: 1089, x: 248.92 }, { y: 1089, x: 236.22 }, { y: 998, x: 233.68 },
        ],
        lat: [
            { y: -7.62, x: 233.68 }, { y: -7.62, x: 254.0 }, { y: -4.0, x: 260.0 },
            { y: 4.0, x: 260.0 }, { y: 7.62, x: 254.0 }, { y: 7.62, x: 233.68 },
        ],
    },
    "R44 Raven I": {
        long: [
            { y: 703, x: 233.68 }, { y: 703, x: 260.0 }, { y: 907, x: 260.0 },
            { y: 1089, x: 248.92 }, { y: 1089, x: 236.22 }, { y: 998, x: 233.68 },
        ],
        lat: [
            { y: -7.62, x: 233.68 }, { y: -7.62, x: 254.0 }, { y: -4.0, x: 260.0 },
            { y: 4.0, x: 260.0 }, { y: 7.62, x: 254.0 }, { y: 7.62, x: 233.68 },
        ],
    },
    "R44 Clipper I": {
        long: [
            { y: 703, x: 233.68 }, { y: 703, x: 260.0 }, { y: 907, x: 260.0 },
            { y: 1089, x: 248.92 }, { y: 1089, x: 236.22 }, { y: 998, x: 233.68 },
        ],
        lat: [
            { y: -7.62, x: 233.68 }, { y: -7.62, x: 254.0 }, { y: -4.0, x: 260.0 },
            { y: 4.0, x: 260.0 }, { y: 7.62, x: 254.0 }, { y: 7.62, x: 233.68 },
        ],
    },
    "R44 Astro": {
        long: [
            { y: 703, x: 233.68 }, { y: 703, x: 260.0 }, { y: 907, x: 260.0 },
            { y: 1089, x: 248.92 }, { y: 1089, x: 236.22 }, { y: 998, x: 233.68 },
        ],
        lat: [
            { y: -7.62, x: 233.68 }, { y: -7.62, x: 254.0 }, { y: -4.0, x: 260.0 },
            { y: 4.0, x: 260.0 }, { y: 7.62, x: 254.0 }, { y: 7.62, x: 233.68 },
        ],
    },
    "R44 Raven II": {
        long: [
            { y: 703, x: 233.68 }, { y: 703, x: 260.0 }, { y: 907, x: 260.0 },
            { y: 1134, x: 248.92 }, { y: 1134, x: 236.22 }, { y: 998, x: 233.68 },
        ],
        lat: [
            { y: -7.62, x: 233.68 }, { y: -7.62, x: 254.0 }, { y: -4.0, x: 260.0 },
            { y: 4.0, x: 260.0 }, { y: 7.62, x: 254.0 }, { y: 7.62, x: 233.68 },
        ],
    },
    "R44 Clipper II": {
        long: [
            { y: 703, x: 233.68 }, { y: 703, x: 260.0 }, { y: 907, x: 260.0 },
            { y: 1134, x: 248.92 }, { y: 1134, x: 236.22 }, { y: 998, x: 233.68 },
        ],
        lat: [
            { y: -7.62, x: 233.68 }, { y: -7.62, x: 254.0 }, { y: -4.0, x: 260.0 },
            { y: 4.0, x: 260.0 }, { y: 7.62, x: 254.0 }, { y: 7.62, x: 233.68 },
        ],
    },
    "EC120B": {
        long: [
            { y: 1035, x: 404.75 }, { y: 1035, x: 416.0 }, { y: 1300, x: 415.0 },
            { y: 1715, x: 409.5 }, { y: 1715, x: 388.0 }, { y: 1400, x: 383.0 },
            { y: 1300, x: 383.0 },
        ],
        lat: [
            { y: -9.0, x: 400.0 }, { y: -9.0, x: 416.0 }, { y: 8, x: 416.0 },
            { y: 8, x: 400.0 }, { y: 4.8, x: 387.4 }, { y: 4.8, x: 383.0 },
            { y: -5.1, x: 383.0 }, { y: -5.1, x: 387.4 },
        ],
    },
    "EC-HIL": {
        long: [
            { y: 1035, x: 404.75 }, { y: 1035, x: 416.0 }, { y: 1300, x: 415.0 },
            { y: 1800, x: 409.5 }, { y: 1800, x: 388.0 }, { y: 1400, x: 383.0 },
            { y: 1300, x: 383.0 },
        ],
        lat: [
            { y: -9.0, x: 400.0 }, { y: -9.0, x: 416.0 }, { y: 8, x: 416.0 },
            { y: 8, x: 400.0 }, { y: 4.8, x: 387.4 }, { y: 4.8, x: 383.0 },
            { y: -5.1, x: 383.0 }, { y: -5.1, x: 387.4 },
        ],
    },
    "CABRI G2": {
        long: [
            { y: 470, x: 212.0 }, { y: 500, x: 212.0 }, { y: 700, x: 202.5 },
            { y: 700, x: 191.5 }, { y: 550, x: 191.5 },
        ],
        lat: [
            { y: -80, x: 211.5 }, { y: 80, x: 211.5 }, { y: 80, x: 191.0 }, { y: -80, x: 191.0 },
        ],
    },
};

function calcPoint(p, min, cp, max, origen) {
    let valor = ((p - min) * cp) / (max - min);
    if (origen > 0) valor = origen - valor;
    return Math.trunc(valor);
}
function drawPoly(poly, canvas) {
    const ctx = canvas.getContext("2d");
    const cw = canvas.width, ch = canvas.height;
    let maxx = -Infinity, minx = Infinity, maxy = -Infinity, miny = Infinity;
    for (let i = 0; i < poly.length; i++) {
        maxx = Math.max(maxx, poly[i].x); minx = Math.min(minx, poly[i].x);
        maxy = Math.max(maxy, poly[i].y); miny = Math.min(miny, poly[i].y);
    }
    ctx.clearRect(0, 0, cw, ch);
    ctx.fillStyle = "#D3D3D3";
    ctx.beginPath();
    ctx.moveTo(calcPoint(poly[0].x, minx, cw, maxx, 0), calcPoint(poly[0].y, miny, ch, maxy, ch));
    for (let i = 1; i < poly.length; i++) {
        ctx.lineTo(calcPoint(poly[i].x, minx, cw, maxx, 0), calcPoint(poly[i].y, miny, ch, maxy, ch));
    }
    ctx.closePath(); ctx.fill();
    return { minx, miny, maxx, maxy };
}
function drawPoint(x, y, tipo, color, maxmins) {
    const canvas = document.getElementById(`${tipo}canvas`);
    if (!canvas) return;
    const cw = canvas.width, ch = canvas.height;
    const ctx = canvas.getContext("2d");
    const { minx, miny, maxx, maxy } = maxmins[tipo];
    const px = calcPoint(x, minx, cw, maxx, 0);
    const py = calcPoint(y, miny, ch, maxy, ch);
    ctx.beginPath(); ctx.arc(px, py, 5, 0, Math.PI * 2, false);
    ctx.fillStyle = color; ctx.fill();
}
function pointInPoly(pt, poly) {
    let c = false;
    for (let i = -1, l = poly.length, j = l - 1; ++i < l; j = i) {
        const cond = ((poly[i].y <= pt.y && pt.y < poly[j].y) || (poly[j].y <= pt.y && pt.y < poly[i].y))
          && (pt.x < (poly[j].x - poly[i].x) * (pt.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x);
        if (cond) c = !c;
    }
    return c;
}
function checkValidity(tipo1, pt, poly, tipo2, maxmins, changes) {
    const inside = pointInPoly(pt, poly);
    const colors = { takeoff: { red: "red", green: "green" }, landing: { red: "magenta", green: "mediumseagreen" } };
    const input = document.querySelector(`input[name='${tipo1}_gw_${tipo2}_arm']`);
    if (input) { input.style.backgroundColor = inside ? colors[tipo1].green : colors[tipo1].red; input.style.color = "#fff"; }
    drawPoint(pt.x, pt.y, tipo2, inside ? colors[tipo1].green : colors[tipo1].red, maxmins);
    changes[`valid_${tipo1}_${tipo2}cg`] = inside;
    return changes;
}
function ensureCanvases() {
    let longDiv = document.getElementById("longcanvasdiv");
    let latDiv = document.getElementById("latcanvasdiv");
    if (!longDiv || !latDiv) return;
    if (!document.getElementById("longcanvas")) {
        const c1 = document.createElement("canvas"); c1.id = "longcanvas"; c1.width = CanvasWidth; c1.height = CanvasHeight;
        longDiv.appendChild(c1); const ctx = c1.getContext("2d"); ctx.fillStyle = "white"; ctx.fillRect(0, 0, c1.width, c1.height);
    }
    if (!document.getElementById("latcanvas")) {
        const c2 = document.createElement("canvas"); c2.id = "latcanvas"; c2.width = CanvasWidth; c2.height = CanvasHeight;
        latDiv.appendChild(c2); const ctx = c2.getContext("2d"); ctx.fillStyle = "yellow"; ctx.fillRect(0, 0, c2.width, c2.height);
    }
}
function drawAll(stateData) {
    ensureCanvases();
    const longC = document.getElementById("longcanvas");
    const latC = document.getElementById("latcanvas");
    if (!longC || !latC) return {};

    const d = stateData || {};
    const tipo = d["helicoptero_tipo"];
    const modelo = d["helicoptero_modelo"];
    const matricula = d["helicoptero_matricula"];
    const gancho = d["gancho_carga_cb"];
    let key;
    if (matricula === "EC-HIL" && gancho === true) key = "EC-HIL";
    else if (tipo === "R44" && modelo) key = modelo;
    else key = tipo;

    const group = Polygons[key];
    if (!group) return {};

    const longInfo = drawPoly(group.long, longC);
    const latInfo = drawPoly(group.lat, latC);
    const maxmins = { long: longInfo, lat: latInfo };

    let changes = {};
    changes = checkValidity("takeoff", { x: d["takeoff_gw_long_arm"], y: d["takeoff_gw"] }, group.long, "long", maxmins, changes);
    changes = checkValidity("takeoff", { x: d["takeoff_gw_long_arm"], y: d["takeoff_gw_lat_arm"] }, group.lat, "lat", maxmins, changes);
    changes = checkValidity("landing", { x: d["landing_gw_long_arm"], y: d["landing_gw"] }, group.long, "long", maxmins, changes);
    changes = checkValidity("landing", { x: d["landing_gw_long_arm"], y: d["landing_gw_lat_arm"] }, group.lat, "lat", maxmins, changes);
    return changes;
}

/* ---- Parches OWL sin this._super ---- */

const _frMounted = FormRenderer.prototype.mounted;
const _frConfirm = FormRenderer.prototype.confirmChange;

patch(FormRenderer.prototype, {
    name: "leulit_operaciones.weight_and_balance_renderer",

    mounted() {
        if (_frMounted) _frMounted.apply(this, arguments);
        const model = this.props?.record?.model || this.props?.archInfo?.model;
        if (model !== "leulit.weight_and_balance") return;
        drawAll(this.state?.data);
    },

    async confirmChange(state, id, fields, ev) {
        const res = _frConfirm ? await _frConfirm.apply(this, arguments) : undefined;
        const model = this.props?.record?.model || this.props?.archInfo?.model;
        if (model !== "leulit.weight_and_balance") return res;
        const wb = drawAll(state?.data);
        for (const k of Object.keys(wb)) {
            if (!fields.includes(k)) fields.push(k);
            ev.data.changes[k] = wb[k];
            state.data[k] = wb[k];
        }
        return res;
    },
});

const _fcMounted = FormController.prototype.mounted;
const _fcWillUnmount = FormController.prototype.willUnmount;
const _fcSave = FormController.prototype.saveRecord;

patch(FormController.prototype, {
    name: "leulit_operaciones.weight_and_balance_controller",

    mounted() {
        if (_fcMounted) _fcMounted.apply(this, arguments);
        this._kbdHandler = (ev) => {
            if (ev.target && ev.target.closest("input.keyboarddisabled")) {
                ev.stopPropagation();
                ev.preventDefault();
            }
        };
        this.el.addEventListener("keydown", this._kbdHandler, true);
    },

    willUnmount() {
        if (this._kbdHandler) this.el.removeEventListener("keydown", this._kbdHandler, true);
        if (_fcWillUnmount) _fcWillUnmount.apply(this, arguments);
    },

    async saveRecord(...args) {
        try {
            const longC = document.getElementById("longcanvas");
            const latC = document.getElementById("latcanvas");
            const extra = {};
            if (longC) extra.canvas_long = longC.toDataURL("image/jpeg");
            if (latC) extra.canvas_lat = latC.toDataURL("image/jpeg");
            if (Object.keys(extra).length && this.model?.root) {
                await this.model.root.update(extra);
            }
        } catch (_) {}
        return _fcSave ? _fcSave.apply(this, args) : undefined;
    },
});
