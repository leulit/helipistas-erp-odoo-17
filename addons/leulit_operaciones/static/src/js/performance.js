/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { onMounted, onWillUnmount } from "@odoo/owl";
import * as K from "@leulit_operaciones/js/performance_constants";

const el = (id) => document.getElementById(id);

function startDraw(divPrefix, inSpec, outSpec, src_in, src_out) {
    const inDiv = el(`${divPrefix}in_div`);
    const outDiv = el(`${divPrefix}out_div`);
    if (!inDiv || !outDiv) {
        return;
    }

    // Limpiar contenido previo
    inDiv.innerHTML = '';
    outDiv.innerHTML = '';

    const inCanvas = document.createElement("canvas");
    inCanvas.id = inSpec.id; 
    inCanvas.width = inSpec.width; 
    inCanvas.height = inSpec.height;
    
    const outCanvas = document.createElement("canvas");
    outCanvas.id = outSpec.id; 
    outCanvas.width = outSpec.width; 
    outCanvas.height = outSpec.height;

    inDiv.appendChild(inCanvas);
    outDiv.appendChild(outCanvas);

    // Cargar imágenes
    const loadImg = (canvas, src) => {
        if (!canvas) {
            return;
        }
        const ctx = canvas.getContext("2d");
        const img = new Image();
        img.onload = () => { 
            ctx.drawImage(img, 0, 0);
        };
        img.onerror = () => {
            // Failed to load image
        };
        img.src = src;
    };
    
    loadImg(inCanvas, src_in);
    loadImg(outCanvas, src_out);
}

function paintPoint(canvasId, bgSrc, x0, y0, imgH, peso, altura) {
    const c = el(canvasId); 
    if (!c) {
        return;
    }
    
    const ctx = c.getContext("2d");
    const img = new Image(); 
    img.src = bgSrc;
    
    img.onload = () => {
        // Redibujar la imagen de fondo
        ctx.clearRect(0, 0, c.width, c.height);
        ctx.drawImage(img, 0, 0);
        
        // Sistema de coordenadas original con translate
        // El origen se traslada a (x0, y0 + imgH)
        // Luego se dibuja en coordenadas relativas (peso, altura)
        const originX = x0;
        const originY = y0 + imgH;
        const pointX = originX + peso;
        const pointY = originY + altura;
        
        // Dibujar el punto
        ctx.save();
        ctx.beginPath();
        ctx.arc(pointX, pointY, 6, 0, Math.PI * 2, false); // Radio 6 para que sea más visible
        ctx.fillStyle = "#FF0000";
        ctx.fill();
        ctx.strokeStyle = "#FFFFFF";
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.closePath();
        ctx.restore();
    };
    
    img.onerror = () => {
        // Failed to load background image
    };
}

function calc_peso(peso, inicio, proporcion, pasarLibras) {
    if (pasarLibras) peso = peso * 2.2046227;
    return (peso - inicio) * proporcion;
}
// Interpola Y en X dado un array de puntos [[x,y],...] ordenados por X
function interpAtX(pts, x) {
    if (pts.length === 1) return pts[0][1];
    const n = pts.length;
    if (x <= pts[0][0]) {
        const dx = pts[1][0] - pts[0][0];
        if (dx === 0) return pts[0][1];
        return pts[0][1] + (x - pts[0][0]) * (pts[1][1] - pts[0][1]) / dx;
    }
    if (x >= pts[n - 1][0]) {
        const dx = pts[n - 1][0] - pts[n - 2][0];
        if (dx === 0) return pts[n - 1][1];
        return pts[n - 2][1] + (x - pts[n - 2][0]) * (pts[n - 1][1] - pts[n - 2][1]) / dx;
    }
    for (let i = 0; i < n - 1; i++) {
        if (x >= pts[i][0] && x <= pts[i + 1][0]) {
            const dx = pts[i + 1][0] - pts[i][0];
            if (dx === 0) return pts[i][1];
            return pts[i][1] + (x - pts[i][0]) * (pts[i + 1][1] - pts[i][1]) / dx;
        }
    }
    return pts[n - 1][1];
}

// Nuevo formato: cada fila = [[x1,y1],[x2,y2],..., temperatura_number]
// El último elemento es un número (temperatura exacta de esa curva)
function calc_altura(temperaturas, temperatura, peso) {
    const bands = temperaturas.map(row => ({
        temp: row[row.length - 1],
        pts: row.slice(0, -1).slice().sort((a, b) => a[0] - b[0]),
    })).sort((a, b) => a.temp - b.temp);

    const n = bands.length;
    if (n === 0) return 0;
    if (n === 1) return interpAtX(bands[0].pts, peso);
    if (temperatura <= bands[0].temp) return interpAtX(bands[0].pts, peso);
    if (temperatura >= bands[n - 1].temp) return interpAtX(bands[n - 1].pts, peso);

    for (let i = 0; i < n - 1; i++) {
        if (temperatura >= bands[i].temp && temperatura < bands[i + 1].temp) {
            const y1 = interpAtX(bands[i].pts, peso);
            const y2 = interpAtX(bands[i + 1].pts, peso);
            const ratio = (temperatura - bands[i].temp) / (bands[i + 1].temp - bands[i].temp);
            return y1 + ratio * (y2 - y1);
        }
    }
    return interpAtX(bands[n - 1].pts, peso);
}

/* ---- Patch FormRenderer con OWL hooks ---- */
patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        const self = this;
        
        // Variables para cleanup
        let notebookClickHandler = null;
        let observer = null;
        
        onMounted(() => {
            const model = self.props?.record?.resModel;
            
            if (model !== "leulit.performance") return;
            
            // Función auxiliar para crear un canvas con imagen
            const createCanvas = (divId, canvasId, width, height, imgSrc) => {
                const div = el(divId);
                if (!div) return;
                
                // Si el canvas ya existe, verificar si tiene contenido
                let canvas = el(canvasId);
                if (canvas) {
                    // Canvas existe, no hacer nada
                    return;
                }
                
                // Crear nuevo canvas
                canvas = document.createElement("canvas");
                canvas.id = canvasId;
                canvas.width = width;
                canvas.height = height;
                
                // Estilo para mejor visualización - mantener tamaño original
                canvas.style.display = "block";
                
                div.appendChild(canvas);
                
                // Cargar imagen
                const ctx = canvas.getContext("2d");
                const img = new Image();
                img.onload = () => { 
                    ctx.drawImage(img, 0, 0);
                };
                img.onerror = () => {
                    // Failed to load image
                };
                img.src = imgSrc;
            };
            
            // Función para inicializar canvas
            const initializeCanvas = () => {
                // EC-HIL
                createCanvas(K.canvas_hil_in + "_div", K.canvas_hil_in, 500, 725, K.src_hil_in);
                createCanvas(K.canvas_hil_out + "_div", K.canvas_hil_out, 520, 770, K.src_hil_out);
                
                // EC120B
                createCanvas(K.canvas_ec_in + "_div", K.canvas_ec_in, 500, 725, K.src_ec_in);
                createCanvas(K.canvas_ec_out + "_div", K.canvas_ec_out, 520, 770, K.src_ec_out);
                
                // R22
                createCanvas(K.canvas_r22_in + "_div", K.canvas_r22_in, 500, 725, K.src_r22_in);
                createCanvas(K.canvas_r22_out + "_div", K.canvas_r22_out, 520, 770, K.src_r22_out);
                
                // R22 II
                createCanvas(K.canvas_r22_2_in + "_div", K.canvas_r22_2_in, 500, 717, K.src_r22_2_in);
                createCanvas(K.canvas_r22_2_out + "_div", K.canvas_r22_2_out, 500, 790, K.src_r22_2_out);
                
                // R44 ASTRO
                createCanvas(K.canvas_r44_in + "_div", K.canvas_r44_in, 620, 900, K.src_r44_in);
                createCanvas(K.canvas_r44_out + "_div", K.canvas_r44_out, 620, 900, K.src_r44_out);
                
                // R44 II
                createCanvas(K.canvas_r44_2_in + "_div", K.canvas_r44_2_in, 500, 725, K.src_r44_2_in);
                createCanvas(K.canvas_r44_2_out + "_div", K.canvas_r44_2_out, 520, 770, K.src_r44_2_out);
                
                // CABRI G2
                createCanvas(K.canvas_cabri_in + "_div", K.canvas_cabri_in, 500, 725, K.src_cabri_in);
                createCanvas(K.canvas_cabri_out + "_div", K.canvas_cabri_out, 520, 770, K.src_cabri_out);
            };
            
            // Inicializar inmediatamente
            setTimeout(() => {
                initializeCanvas();
            }, 100);
            
            // Capturar clicks en pestañas del notebook para reinicializar canvas
            notebookClickHandler = (ev) => {
                const navLink = ev.target.closest('.nav-link');
                if (navLink && navLink.closest('.o_notebook_headers')) {
                    setTimeout(initializeCanvas, 100);
                }
            };
            
            // Registrar listener para clicks en pestañas
            document.addEventListener('click', notebookClickHandler, true);
            
            // También observar cambios en atributos (class) para detectar cambios de pestaña activa
            observer = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    if (mutation.type === 'attributes' && 
                        (mutation.attributeName === 'class' || mutation.attributeName === 'style')) {
                        const target = mutation.target;
                        if (target.classList && target.classList.contains('tab-pane')) {
                            if (target.classList.contains('active')) {
                                setTimeout(initializeCanvas, 50);
                            }
                        }
                    }
                }
            });
            
            // Observar el formulario completo
            const form = document.querySelector('.o_form_view');
            if (form) {
                observer.observe(form, { 
                    attributes: true, 
                    attributeFilter: ['class', 'style'],
                    subtree: true 
                });
            }
        });
        
        // Cleanup al desmontar - DEBE estar en el nivel de setup(), no dentro de onMounted()
        onWillUnmount(() => {
            if (notebookClickHandler) {
                document.removeEventListener('click', notebookClickHandler, true);
            }
            if (observer) {
                observer.disconnect();
            }
        });
    },
});

/* ---- Patch FormController para eventos y guardado ---- */
patch(FormController.prototype, {
    setup() {
        super.setup();
        
        // Solo ejecutar para el modelo leulit.performance
        if (this.props.resModel !== "leulit.performance") {
            return;
        }

        const self = this;

        onMounted(() => {
            // Función de cálculo (ahora declarada antes para poder usarla en auto-cálculo)
            const doCalculation = () => {
                const d = self.model?.root?.data || {};
                const t = d.temperatura;
                const p = d.peso;

                if (el(K.canvas_r22_in) && el(K.canvas_r22_out)) {
                    const p_in  = calc_peso(p, K.inicio_eje_r22_in,  K.proporcion_r22_in,  false);
                    const p_out = calc_peso(p, K.inicio_eje_r22_out, K.proporcion_r22_out, false);
                    const a_in  = calc_altura(K.temperaturas_r22_in,  t, p_in);
                    const a_out = calc_altura(K.temperaturas_r22_out, t, p_out);
                    paintPoint(K.canvas_r22_in,  K.src_r22_in,  K.inicio_eje_x_r22_in,  K.inicio_eje_y_r22_in,  K.altura_imagen_r22_in,  p_in,  a_in);
                    paintPoint(K.canvas_r22_out, K.src_r22_out, K.inicio_eje_x_r22_out, K.inicio_eje_y_r22_out, K.altura_imagen_r22_out, p_out, a_out);
                }
                if (el(K.canvas_r22_2_in) && el(K.canvas_r22_2_out)) {
                    const p_in  = calc_peso(p, K.inicio_eje_r22_2_in,  K.proporcion_r22_2_in,  false);
                    const p_out = calc_peso(p, K.inicio_eje_r22_2_out, K.proporcion_r22_2_out, false);
                    const a_in  = calc_altura(K.temperaturas_r22_2_in,  t, p_in);
                    const a_out = calc_altura(K.temperaturas_r22_2_out, t, p_out);
                    paintPoint(K.canvas_r22_2_in,  K.src_r22_2_in,  K.inicio_eje_x_r22_2_in,  K.inicio_eje_y_r22_2_in,  K.altura_imagen_r22_2_in,  p_in,  a_in);
                    paintPoint(K.canvas_r22_2_out, K.src_r22_2_out, K.inicio_eje_x_r22_2_out, K.inicio_eje_y_r22_2_out, K.altura_imagen_r22_2_out, p_out, a_out);
                }
                if (el(K.canvas_cabri_in) && el(K.canvas_cabri_out)) {
                    const p_in  = calc_peso(p, K.inicio_eje_cabri, K.proporcion_cabri_in,  false);
                    const p_out = calc_peso(p, K.inicio_eje_cabri, K.proporcion_cabri_out, false);
                    const a_in  = calc_altura(K.temperaturas_cabri_in,  t, p_in);
                    const a_out = calc_altura(K.temperaturas_cabri_out, t, p_out);
                    paintPoint(K.canvas_cabri_in,  K.src_cabri_in,  K.inicio_eje_x_cabri_in,  K.inicio_eje_y_cabri_in,  K.altura_imagen_cabri_in,  p_in,  a_in);
                    paintPoint(K.canvas_cabri_out, K.src_cabri_out, K.inicio_eje_x_cabri_out, K.inicio_eje_y_cabri_out, K.altura_imagen_cabri_out, p_out, a_out);
                }
                if (el(K.canvas_r44_2_in) && el(K.canvas_r44_2_out)) {
                    const p_in  = calc_peso(p, K.inicio_eje_r44_2_in,  K.proporcion_r44_2_in,  false);
                    const p_out = calc_peso(p, K.inicio_eje_r44_2_out, K.proporcion_r44_2_out, false);
                    const a_in  = calc_altura(K.temperaturas_r44_2_in,  t, p_in);
                    const a_out = calc_altura(K.temperaturas_r44_2_out, t, p_out);
                    paintPoint(K.canvas_r44_2_in,  K.src_r44_2_in,  K.inicio_eje_x_r44_2_in,  K.inicio_eje_y_r44_2_in,  K.altura_imagen_r44_2_in,  p_in,  a_in);
                    paintPoint(K.canvas_r44_2_out, K.src_r44_2_out, K.inicio_eje_x_r44_2_out, K.inicio_eje_y_r44_2_out, K.altura_imagen_r44_2_out, p_out, a_out);
                }
                if (el(K.canvas_r44_in) && el(K.canvas_r44_out)) {
                    const p_in  = calc_peso(p, K.inicio_eje_r44_in,  K.proporcion_r44_in,  false);
                    const p_out = calc_peso(p, K.inicio_eje_r44_out, K.proporcion_r44_out, false);
                    const a_in  = calc_altura(K.temperaturas_r44_in,  t, p_in);
                    const a_out = calc_altura(K.temperaturas_r44_out, t, p_out);
                    paintPoint(K.canvas_r44_in,  K.src_r44_in,  K.inicio_eje_x_r44_in,  K.inicio_eje_y_r44_in,  K.altura_imagen_r44_in,  p_in,  a_in);
                    paintPoint(K.canvas_r44_out, K.src_r44_out, K.inicio_eje_x_r44_out, K.inicio_eje_y_r44_out, K.altura_imagen_r44_out, p_out, a_out);
                }
                if (el(K.canvas_ec_in) && el(K.canvas_ec_out)) {
                    const p_in  = calc_peso(p, K.inicio_eje_ec_in,  K.proporcion_ec_in,  false);
                    const p_out = calc_peso(p, K.inicio_eje_ec_out, K.proporcion_ec_out, false);
                    const a_in  = calc_altura(K.temperaturas_ec_in,  t, p_in);
                    const a_out = calc_altura(K.temperaturas_ec_out, t, p_out);
                    paintPoint(K.canvas_ec_in,  K.src_ec_in,  K.inicio_eje_x_ec_in,  K.inicio_eje_y_ec_in,  K.altura_imagen_ec_in,  p_in,  a_in);
                    paintPoint(K.canvas_ec_out, K.src_ec_out, K.inicio_eje_x_ec_out, K.inicio_eje_y_ec_out, K.altura_imagen_ec_out, p_out, a_out);
                }
                if (el(K.canvas_hil_in) && el(K.canvas_hil_out)) {
                    const p_in  = calc_peso(p, K.inicio_eje_hil_in,  K.proporcion_hil_in,  false);
                    const p_out = calc_peso(p, K.inicio_eje_hil_out, K.proporcion_hil_out, false);
                    const a_in  = calc_altura(K.temperaturas_hil_in,  t, p_in);
                    const a_out = calc_altura(K.temperaturas_hil_out, t, p_out);
                    paintPoint(K.canvas_hil_in,  K.src_hil_in,  K.inicio_eje_x_hil_in,  K.inicio_eje_y_hil_in,  K.altura_imagen_hil_in,  p_in,  a_in);
                    paintPoint(K.canvas_hil_out, K.src_hil_out, K.inicio_eje_x_hil_out, K.inicio_eje_y_hil_out, K.altura_imagen_hil_out, p_out, a_out);
                }
            };
            
            // ESTRATEGIA AGRESIVA: Interceptar TODOS los clicks en el form
            const formElement = document.querySelector('.o_form_view');
            if (formElement) {
                formElement.addEventListener('click', (ev) => {
                    // Buscar si el click fue en o cerca del botón calcular
                    const target = ev.target;
                    const isButton = target.classList?.contains('calcular_button');
                    const inButton = target.closest('.calcular_button');
                    const isCalcButton = target.getAttribute?.('name') === 'dummy_calcular';
                    
                    if (isButton || inButton || isCalcButton) {
                        ev.preventDefault();
                        ev.stopPropagation();
                        ev.stopImmediatePropagation();
                        doCalculation();
                        return false;
                    }
                }, true); // Fase de captura - antes que nadie
            }
            
            // PLAN B: También intentar con el botón directamente después de que se renderice
            setTimeout(() => {
                const buttons = document.querySelectorAll('.calcular_button, button[name="dummy_calcular"]');
                
                buttons.forEach((btn, idx) => {
                    // Triple asignación por las dudas
                    btn.onclick = (ev) => {
                        ev.preventDefault();
                        ev.stopPropagation();
                        doCalculation();
                        return false;
                    };
                    
                    btn.addEventListener('click', (ev) => {
                        ev.preventDefault();
                        ev.stopPropagation();
                        doCalculation();
                    }, true);
                    
                    btn.addEventListener('mousedown', (ev) => {
                        ev.preventDefault();
                    });
                });
            }, 300);
            
            // AUTO-CALCULAR si ya tiene datos al abrir el formulario
            setTimeout(() => {
                const data = self.model?.root?.data;
                if (data && data.peso && data.temperatura) {
                    doCalculation();
                }
            }, 800); // Dar tiempo para que los canvas se carguen completamente
        });

        onWillUnmount(() => {
            // Controller unmounting
        });
    },

    async saveButtonClicked(params = {}) {
        // Guardar canvas como imágenes antes del save
        if (this.props.resModel === "leulit.performance") {
            try {
                let cin = "", cout = "";
                
                if (el(K.canvas_hil_in + "_div")   && el(K.canvas_hil_out + "_div"))   { 
                    cin = K.canvas_hil_in;   
                    cout = K.canvas_hil_out;
                }
                if (el(K.canvas_ec_in + "_div")    && el(K.canvas_ec_out + "_div"))    { 
                    cin = K.canvas_ec_in;    
                    cout = K.canvas_ec_out;
                }
                if (el(K.canvas_r44_in + "_div")   && el(K.canvas_r44_out + "_div"))   { 
                    cin = K.canvas_r44_in;   
                    cout = K.canvas_r44_out;
                }
                if (el(K.canvas_r44_2_in + "_div") && el(K.canvas_r44_2_out + "_div")) { 
                    cin = K.canvas_r44_2_in; 
                    cout = K.canvas_r44_2_out;
                }
                if (el(K.canvas_cabri_in + "_div") && el(K.canvas_cabri_out + "_div")) { 
                    cin = K.canvas_cabri_in; 
                    cout = K.canvas_cabri_out;
                }
                if (el(K.canvas_r22_in + "_div")   && el(K.canvas_r22_out + "_div"))   { 
                    cin = K.canvas_r22_in;   
                    cout = K.canvas_r22_out;
                }
                if (el(K.canvas_r22_2_in + "_div") && el(K.canvas_r22_2_out + "_div")) { 
                    cin = K.canvas_r22_2_in; 
                    cout = K.canvas_r22_2_out;
                }

                const extra = {};
                if (cin && el(cin)) {
                    const canvasElement = el(cin);
                    extra.ige = canvasElement.toDataURL("image/png");
                }
                if (cout && el(cout)) {
                    const canvasElement = el(cout);
                    extra.oge = canvasElement.toDataURL("image/png");
                }
                
                if (Object.keys(extra).length && this.model?.root) {
                    // Actualizar el modelo sin guardar aún
                    await this.model.root.update(extra, { save: false });
                }
            } catch (error) {
                // Error saving performance canvas
            }
        }
        
        // Llamar al save original - esto guardará todo incluyendo ige y oge
        const result = await super.saveButtonClicked(params);
        return result;
    },
});
