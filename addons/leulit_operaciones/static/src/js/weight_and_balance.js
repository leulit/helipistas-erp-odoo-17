/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormController } from "@web/views/form/form_controller";
import { onMounted, onPatched } from "@odoo/owl";
import { Record } from "@web/model/relational_model/record";

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
    const colors = { 
        takeoff: { red: "red", green: "green" }, 
        landing: { red: "magenta", green: "mediumseagreen" } 
    };
    
    // Buscar el input de múltiples formas para asegurar que lo encontramos
    const fieldName = `${tipo1}_gw_${tipo2}_arm`;
    let input = null;
    
    // Método 1: Buscar por clase wb_cg_indicator y el nombre del campo (más confiable)
    const allCgIndicators = document.querySelectorAll('.wb_cg_indicator');
    for (const widget of allCgIndicators) {
        // Verificar si el widget tiene el atributo name correcto
        if (widget.getAttribute('name') === fieldName) {
            input = widget.querySelector('input');
            if (input) break;
        }
    }
    
    // Método 2: Buscar el div.o_field_widget con ese name y luego su input
    if (!input) {
        const fieldDiv = document.querySelector(`div[name='${fieldName}']`);
        if (fieldDiv) {
            input = fieldDiv.querySelector('input');
        }
    }
    
    // Método 3: Buscar input directamente por ID que contenga el nombre del campo
    if (!input) {
        const allInputs = document.querySelectorAll('table input');
        for (const el of allInputs) {
            if (el.id && el.id.includes(fieldName)) {
                input = el;
                break;
            }
        }
    }
    
    // Aplicar el estilo si encontramos el input
    if (input) { 
        const bgColor = inside ? colors[tipo1].green : colors[tipo1].red;
        
        // Aplicar múltiples formas para asegurar que el estilo se aplique
        input.style.setProperty('background-color', bgColor, 'important');
        input.style.setProperty('color', '#fff', 'important');
        input.style.setProperty('font-weight', 'bold', 'important');
        input.style.setProperty('text-align', 'center', 'important');
        
        // También aplicar al padre si existe
        const parent = input.closest('.o_field_widget');
        if (parent) {
            parent.style.setProperty('background-color', bgColor, 'important');
        }
        
        console.log(`✓ Colored field ${fieldName}: ${bgColor} (inside: ${inside})`);
    } else {
        console.warn(`✗ Could not find input for field: ${fieldName}`);
    }
    
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

/* ---- Parches OWL para Odoo 17 ---- */

// Patch al Record para interceptar cambios en el modelo
patch(Record.prototype, {
    async update(changes, options) {
        const result = await super.update(changes, options);
        
        // Solo actuar si es el modelo weight_and_balance
        if (this.resModel === "leulit.weight_and_balance") {
            console.log("Weight & Balance - Record updated with changes:", Object.keys(changes));
            
            // Redibujar los canvas después de actualizar el modelo
            setTimeout(async () => {
                const data = this.data || {};
                const wb = drawAll(data);
                
                // Si hay campos de validación para actualizar, hacerlo con update() para que se guarden
                if (Object.keys(wb).length > 0) {
                    // Actualizar usando update() para que se persistan los cambios
                    await this.update(wb, { save: false });
                }
            }, 10);
        }
        
        return result;
    },
});

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        const self = this;
        
        onMounted(() => {
            const model = self.props?.record?.resModel;
            if (model !== "leulit.weight_and_balance") return;
            
            console.log("Weight & Balance mounted - initial draw");
            setTimeout(async () => {
                const data = self.props?.record?.data || {};
                const wb = drawAll(data);
                
                // Actualizar los campos de validación en el modelo usando update()
                if (Object.keys(wb).length > 0 && self.props?.record?.update) {
                    await self.props.record.update(wb, { save: false });
                }
            }, 100);
        });

        // onPatched se ejecuta cada vez que el componente se re-renderiza por cambios
        onPatched(() => {
            const model = self.props?.record?.resModel;
            if (model !== "leulit.weight_and_balance") return;
            
            console.log("Weight & Balance patched - redrawing");
            const data = self.props?.record?.data || {};
            drawAll(data);
        });
    },
});

patch(FormController.prototype, {
    async beforeLeave() {
        // Primero guardar los canvas antes de salir
        try {
            const model = this.model?.root?.resModel;
            if (model === "leulit.weight_and_balance") {
                const longC = document.getElementById("longcanvas");
                const latC = document.getElementById("latcanvas");
                const extra = {};
                
                if (longC) extra.canvas_long = longC.toDataURL("image/jpeg");
                if (latC) extra.canvas_lat = latC.toDataURL("image/jpeg");
                
                if (Object.keys(extra).length && this.model?.root?.update) {
                    console.log("Saving canvas images before leaving...");
                    await this.model.root.update(extra, { save: true });
                }
            }
        } catch (error) {
            console.error("Error saving canvas data:", error);
        }
        
        return super.beforeLeave(...arguments);
    },

    async saveButtonClicked(params = {}) {
        // Guardar los canvas antes de llamar al save original
        try {
            const model = this.model?.root?.resModel;
            if (model === "leulit.weight_and_balance") {
                const longC = document.getElementById("longcanvas");
                const latC = document.getElementById("latcanvas");
                const extra = {};
                
                if (longC) extra.canvas_long = longC.toDataURL("image/jpeg");
                if (latC) extra.canvas_lat = latC.toDataURL("image/jpeg");
                
                if (Object.keys(extra).length && this.model?.root?.update) {
                    console.log("Saving canvas images on save button...");
                    await this.model.root.update(extra, { save: false });
                }
            }
        } catch (error) {
            console.error("Error saving canvas data:", error);
        }
        
        // Llamar al guardado original que guardará todo junto
        return super.saveButtonClicked(params);
    },
});
