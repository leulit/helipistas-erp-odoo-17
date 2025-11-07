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
    // Prevenir división por cero
    if (max === min) return origen > 0 ? origen : 0;
    
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
    
    // Buscar el campo (puede ser un input o un div readonly)
    const fieldName = `${tipo1}_gw_${tipo2}_arm`;
  
    // Función para aplicar estilos (la usaremos de forma asíncrona)
    const applyStylesToField = () => {
        let targetElement = null;
        
        // Método 1: Buscar por clase wb_cg_indicator y el nombre del campo
        const allCgIndicators = document.querySelectorAll('.wb_cg_indicator');
        for (const widget of allCgIndicators) {
            if (widget.getAttribute('name') === fieldName) {
                const input = widget.querySelector('input');
                targetElement = input || widget;
                break;
            }
        }
        
        // Método 2: Buscar el div.o_field_widget con ese name
        if (!targetElement) {
            const fieldDiv = document.querySelector(`div[name='${fieldName}']`);
            if (fieldDiv) {
                const input = fieldDiv.querySelector('input');
                targetElement = input || fieldDiv;
            }
        }
        
        // Método 3: Buscar directamente por el input con name
        if (!targetElement) {
            const inputField = document.querySelector(`input[name='${fieldName}']`);
            if (inputField) {
                targetElement = inputField;
            }
        }
        
        // Aplicar el estilo si encontramos el elemento
        if (targetElement) { 
            const bgColor = inside ? colors[tipo1].green : colors[tipo1].red;
            
            // Aplicar estilos al elemento encontrado
            targetElement.style.setProperty('background-color', bgColor, 'important');
            targetElement.style.setProperty('color', '#fff', 'important');
            targetElement.style.setProperty('font-weight', 'bold', 'important');
            targetElement.style.setProperty('text-align', 'center', 'important');
            targetElement.style.setProperty('padding', '2px 4px', 'important');
            targetElement.style.setProperty('border-radius', '3px', 'important');
            return true;
        }
        return false;
    };
    
    // Intentar aplicar estilos inmediatamente
    const applied = applyStylesToField();
    
    // Si no se aplicó (elemento aún no en DOM), reintentar después de un pequeño delay
    if (!applied) {
        setTimeout(applyStylesToField, 100);
        setTimeout(applyStylesToField, 300);
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
    
    // Validar que al menos tenemos tipo o modelo
    if (!tipo && !modelo && !matricula) {
        console.warn("Weight&Balance drawAll: No hay datos de helicóptero para dibujar");
        return {};
    }
    
    let key;
    if (matricula === "EC-HIL" && gancho === true) key = "EC-HIL";
    else if (tipo === "R44" && modelo) key = modelo;
    else key = tipo;

    const group = Polygons[key];
    if (!group) {
        console.warn(`Weight&Balance drawAll: No se encontró polígono para key="${key}"`);
        return {};
    }

    const longInfo = drawPoly(group.long, longC);
    const latInfo = drawPoly(group.lat, latC);
    const maxmins = { long: longInfo, lat: latInfo };

    let changes = {};
    
    // Solo calcular validaciones si tenemos valores numéricos válidos
    const takeoffLongArm = parseFloat(d["takeoff_gw_long_arm"]);
    const takeoffGw = parseFloat(d["takeoff_gw"]);
    const takeoffLatArm = parseFloat(d["takeoff_gw_lat_arm"]);
    const landingLongArm = parseFloat(d["landing_gw_long_arm"]);
    const landingGw = parseFloat(d["landing_gw"]);
    const landingLatArm = parseFloat(d["landing_gw_lat_arm"]);
    
    if (!isNaN(takeoffLongArm) && !isNaN(takeoffGw)) {
        changes = checkValidity("takeoff", { x: takeoffLongArm, y: takeoffGw }, group.long, "long", maxmins, changes);
    }
    if (!isNaN(takeoffLongArm) && !isNaN(takeoffLatArm)) {
        changes = checkValidity("takeoff", { x: takeoffLongArm, y: takeoffLatArm }, group.lat, "lat", maxmins, changes);
    }
    if (!isNaN(landingLongArm) && !isNaN(landingGw)) {
        changes = checkValidity("landing", { x: landingLongArm, y: landingGw }, group.long, "long", maxmins, changes);
    }
    if (!isNaN(landingLongArm) && !isNaN(landingLatArm)) {
        changes = checkValidity("landing", { x: landingLongArm, y: landingLatArm }, group.lat, "lat", maxmins, changes);
    }
    
    return changes;
}

/* ---- Parches OWL para Odoo 17 ---- */

// Variable para evitar loops infinitos
let isUpdatingCanvas = false;

// Patch al Record para interceptar cambios en el modelo
patch(Record.prototype, {
    async update(changes, options) {
        const result = await super.update(changes, options);
        
        // Solo actuar si es el modelo weight_and_balance y no estamos ya actualizando canvas
        if (this.resModel === "leulit.weight_and_balance" && !isUpdatingCanvas) {
            // Redibujar los canvas después de actualizar el modelo
            setTimeout(async () => {
                isUpdatingCanvas = true;
                try {
                    const data = this.data || {};
                    const wb = drawAll(data);
                    
                    // Guardar también los canvas como imágenes (con try/catch por si falla toDataURL)
                    try {
                        const longC = document.getElementById("longcanvas");
                        const latC = document.getElementById("latcanvas");
                        if (longC) wb.canvas_long = longC.toDataURL("image/jpeg");
                        if (latC) wb.canvas_lat = latC.toDataURL("image/jpeg");
                    } catch (canvasError) {
                        console.warn("Error al convertir canvas a imagen:", canvasError);
                    }
                    
                    // Si hay campos de validación para actualizar, hacerlo con update() para que se guarden
                    if (Object.keys(wb).length > 0) {
                        // Actualizar directamente usando super.update() para evitar
                        // reentrada en este parche (this.update llamaría de nuevo
                        // a la función parcheada y puede provocar bucles).
                        await super.update(wb, { save: false });
                    }
                } finally {
                    isUpdatingCanvas = false;
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
            
            // Esperar múltiples ciclos para asegurar que TODOS los campos relacionados estén cargados
            const tryDrawCanvas = (attempt = 1) => {
                const maxAttempts = 5;
                
                // Verificar que tenemos un record válido con datos
                if (!self.props?.record?.data) {
                    if (attempt < maxAttempts) {
                        setTimeout(() => tryDrawCanvas(attempt + 1), 200 * attempt);
                    }
                    return;
                }
                
                const data = self.props.record.data;
                
                // Debug: ver qué datos tenemos
                console.log(`Weight&Balance onMounted (intento ${attempt}) - datos cargados:`, {
                    helicoptero_tipo: data.helicoptero_tipo,
                    helicoptero_modelo: data.helicoptero_modelo,
                    helicoptero_matricula: data.helicoptero_matricula,
                    frs: data.frs,
                    fls: data.fls,
                    takeoff_gw: data.takeoff_gw,
                    takeoff_gw_long_arm: data.takeoff_gw_long_arm,
                    landing_gw: data.landing_gw,
                });
                
                // Asegurar que los canvas existen primero
                ensureCanvases();
                
                // Verificar si tenemos datos de helicóptero
                const hasValidData = data.helicoptero_tipo || data.helicoptero_modelo;
                if (!hasValidData) {
                    console.warn(`Weight&Balance: No hay tipo/modelo de helicóptero (intento ${attempt}/${maxAttempts})`);
                    if (attempt < maxAttempts) {
                        setTimeout(() => tryDrawCanvas(attempt + 1), 200 * attempt);
                    }
                    return;
                }
                
                // Verificar si tenemos datos calculados (los campos computados tardan en cargar)
                const hasComputedData = data.takeoff_gw_long_arm !== undefined && data.takeoff_gw_long_arm !== false;
                if (!hasComputedData) {
                    console.warn(`Weight&Balance: Campos computados aún no cargados (intento ${attempt}/${maxAttempts})`);
                    if (attempt < maxAttempts) {
                        setTimeout(() => tryDrawCanvas(attempt + 1), 300 * attempt);
                    }
                    return;
                }
                
                console.log("Weight&Balance: Todos los datos cargados, dibujando canvas...");
                
                // Dibujar los gráficos con los datos reales del formulario
                const wb = drawAll(data);
                
                // Guardar también los canvas como imágenes (con try/catch)
                try {
                    const longC = document.getElementById("longcanvas");
                    const latC = document.getElementById("latcanvas");
                    if (longC) wb.canvas_long = longC.toDataURL("image/jpeg");
                    if (latC) wb.canvas_lat = latC.toDataURL("image/jpeg");
                } catch (canvasError) {
                    console.warn("Error al convertir canvas a imagen en onMounted:", canvasError);
                }
                
                // Actualizar los campos de validación y canvas en el modelo
                if (Object.keys(wb).length > 0 && self.props.record?.update) {
                    self.props.record.update(wb, { save: false });
                }
            };
            
            // Iniciar el primer intento
            setTimeout(() => tryDrawCanvas(1), 100);
        });

        // onPatched se ejecuta cada vez que el componente se re-renderiza por cambios
        onPatched(() => {
            const model = self.props?.record?.resModel;
            if (model !== "leulit.weight_and_balance") return;
            
            const data = self.props?.record?.data || {};
            
            // Solo redibujar si tenemos datos válidos
            const hasValidData = data.helicoptero_tipo || data.helicoptero_modelo;
            if (!hasValidData) return;
            
            drawAll(data);
            
            // Guardar los canvas actualizados en el modelo (sin disparar update)
            setTimeout(() => {
                try {
                    const longC = document.getElementById("longcanvas");
                    const latC = document.getElementById("latcanvas");
                    if (longC && latC && self.props?.record) {
                        const canvasData = {
                            canvas_long: longC.toDataURL("image/jpeg"),
                            canvas_lat: latC.toDataURL("image/jpeg")
                        };
                        Object.assign(self.props.record.data, canvasData);
                    }
                } catch (canvasError) {
                    console.warn("Error al convertir canvas a imagen en onPatched:", canvasError);
                }
            }, 50);
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
                    await this.model.root.update(extra, { save: true });
                }
            }
        } catch (error) {
            // Error saving canvas data
        }
        
        return super.beforeLeave(...arguments);
    },

    async onButtonClicked(clickParams) {
        // Interceptar el botón btn_save_wizard para guardar canvas antes de ejecutar Python
        if (clickParams.name === "btn_save_wizard") {
            const model = this.model?.root?.resModel;
            if (model === "leulit.weight_and_balance") {
                const longC = document.getElementById("longcanvas");
                const latC = document.getElementById("latcanvas");
                const extra = {};
                
                if (longC) extra.canvas_long = longC.toDataURL("image/jpeg");
                if (latC) extra.canvas_lat = latC.toDataURL("image/jpeg");
                
                if (Object.keys(extra).length) {
                    // Asignar directamente a data sin disparar onchange
                    Object.assign(this.model.root.data, extra);
                }
            }
        }
        
        return super.onButtonClicked(clickParams);
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
                
                // Actualizar el modelo sin guardar aún - los datos quedarán en el record
                if (Object.keys(extra).length && this.model?.root) {
                    // Asignar directamente a los datos del record
                    Object.assign(this.model.root.data, extra);
                }
            }
        } catch (error) {
            // Error saving canvas data
        }
        
        // Llamar al guardado original que guardará todo junto incluyendo canvas_long y canvas_lat
        return super.saveButtonClicked(params);
    },
});
