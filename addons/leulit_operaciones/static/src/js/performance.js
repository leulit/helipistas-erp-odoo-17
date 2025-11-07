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
        console.warn(`Cannot find divs: ${divPrefix}in_div or ${divPrefix}out_div`);
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
            console.warn(`Canvas not found for src: ${src}`);
            return;
        }
        const ctx = canvas.getContext("2d");
        const img = new Image();
        img.onload = () => { 
            ctx.drawImage(img, 0, 0); 
            console.log(`Image loaded: ${src}`);
        };
        img.onerror = () => {
            console.error(`Failed to load image: ${src}`);
        };
        img.src = src;
    };
    
    loadImg(inCanvas, src_in);
    loadImg(outCanvas, src_out);
}

function paintPoint(canvasId, bgSrc, x0, y0, imgH, peso, altura) {
    const c = el(canvasId); if (!c) return;
    const ctx = c.getContext("2d");
    const img = new Image(); img.src = bgSrc;
    img.onload = () => {
        ctx.drawImage(img, 0, 0);
        ctx.beginPath();
        ctx.translate(x0, y0 + imgH);
        ctx.arc(peso, altura, 4, 0, Math.PI * 2, false);
        ctx.fillStyle = "#FF0000";
        ctx.translate(-x0, -(y0 + imgH));
        ctx.fill();
        ctx.closePath();
    };
}

function calc_peso(peso, inicio, proporcion, pasarLibras, dividir) {
    if (pasarLibras) peso = peso * 2.2046227;
    peso = peso - inicio;
    return dividir ? (peso / proporcion) : (peso * proporcion);
}
function obtener_altura(y_low, y_high, distancia) {
    const dis = (y_high - y_low) / 10;
    return y_low + distancia * dis;
}
function buscar_altura(x, temperaturas, temperatura, i, max) {
    let altura;
    const seg = temperaturas[i];
    const L = seg.length - 1;
    const interp = (x1, y1, x2, y2) => (x * (y2 - y1) + y1 * (x2 - x1) - x1 * (y2 - y1)) / (x2 - x1);

    if (!max) {
        let distancia;
        const last = seg.length - 1;
        if (temperatura === seg[last][0]) distancia = 0;
        else {
            distancia = temperatura - seg[last][1];
            if (distancia < 0) distancia = 10 + distancia;
        }
        let y_low, y_high;
        if (L === 4) {
            y_low  = interp(seg[0][0], seg[0][1], seg[1][0], seg[1][1]);
            y_high = interp(seg[2][0], seg[2][1], seg[3][0], seg[3][1]);
        } else if (L === 5) {
            y_low  = interp(seg[0][0], seg[0][1], seg[1][0], seg[1][1]);
            const hi = x > seg[2][0] ? seg[4] : seg[3];
            y_high = interp(seg[2][0], seg[2][1], hi[0], hi[1]);
        } else if (L === 6) {
            const lo = x > seg[1][0] ? seg[4] : seg[1];
            y_low  = interp(lo[0], lo[1], lo === seg[1] ? seg[1][0] : seg[0][0], lo === seg[1] ? seg[1][1] : seg[0][1]);
            const hi = x > seg[2][0] ? seg[5] : seg[3];
            y_high = interp(seg[2][0], seg[2][1], hi[0], hi[1]);
        } else if (L === 7) {
            const lo = x > seg[6][0] ? seg[1] : (x > seg[1][0] ? seg[4] : seg[6]);
            y_low  = interp(lo[0], lo[1], lo === seg[1] ? seg[1][0] : seg[0][0], lo === seg[1] ? seg[1][1] : seg[0][1]);
            const hi = x > seg[2][0] ? seg[5] : seg[3];
            y_high = interp(seg[2][0], seg[2][1], hi[0], hi[1]);
        } else if (L === 8) {
            const lo = x > seg[4][0] ? seg[6] : (x > seg[1][0] ? seg[4] : seg[1]);
            y_low  = interp(lo[0], lo[1], lo === seg[1] ? seg[1][0] : seg[0][0], lo === seg[1] ? seg[1][1] : seg[0][1]);
            const hi = x > seg[5][0] ? seg[7] : (x > seg[2][0] ? seg[5] : seg[3]);
            y_high = interp(seg[2][0], seg[2][1], hi[0], hi[1]);
        }
        altura = obtener_altura(y_low, y_high, distancia);
    } else {
        let x1, y1, x2, y2;
        if (L === 6)      [x1, y1, x2, y2] = x > seg[2][0] ? [seg[2][0], seg[2][1], seg[5][0], seg[5][1]] : [seg[2][0], seg[2][1], seg[3][0], seg[3][1]];
        else if (L === 5) [x1, y1, x2, y2] = x > seg[2][0] ? [seg[2][0], seg[2][1], seg[4][0], seg[4][1]] : [seg[2][0], seg[2][1], seg[3][0], seg[3][1]];
        else if (L === 8) {
            if (x > seg[5][0] && x <= seg[7][0]) [x1, y1, x2, y2] = [seg[5][0], seg[5][1], seg[7][0], seg[7][1]];
            else if (x > seg[2][0])              [x1, y1, x2, y2] = [seg[2][0], seg[2][1], seg[5][0], seg[5][1]];
            else                                  [x1, y1, x2, y2] = [seg[2][0], seg[2][1], seg[3][0], seg[3][1]];
        } else             [x1, y1, x2, y2] = [seg[2][0], seg[2][1], seg[3][0], seg[3][1]];
        altura = (x * (y2 - y1) + y1 * (x2 - x1) - x1 * (y2 - y1)) / (x2 - x1);
    }
    return altura;
}
function calc_altura(temperaturas, temperatura, peso) {
    const lastI = temperaturas.length - 1;
    const topMax = temperaturas[lastI][temperaturas[lastI].length - 1][1];
    if (temperatura >= topMax) return buscar_altura(peso, temperaturas, temperatura, lastI, true);
    for (let i = 0; i < temperaturas.length; i++) {
        const row = temperaturas[i];
        const lo = row[row.length - 1][0], hi = row[row.length - 1][1];
        if (temperatura >= lo && temperatura < hi) return buscar_altura(peso, temperaturas, temperatura, i, false);
    }
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
            console.log("FormRenderer mounted - Model:", model);
            
            if (model !== "leulit.performance") return;
            
            console.log("Performance form mounted - initializing canvas...");
            
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
                console.log(`Creating canvas: ${canvasId}`);
                canvas = document.createElement("canvas");
                canvas.id = canvasId;
                canvas.width = width;
                canvas.height = height;
                div.appendChild(canvas);
                
                // Cargar imagen
                const ctx = canvas.getContext("2d");
                const img = new Image();
                img.onload = () => { 
                    ctx.drawImage(img, 0, 0); 
                    console.log(`Image loaded: ${imgSrc}`);
                };
                img.onerror = () => console.error(`Failed to load: ${imgSrc}`);
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
            setTimeout(initializeCanvas, 100);
            
            // Capturar clicks en pestañas del notebook para reinicializar canvas
            notebookClickHandler = (ev) => {
                const navLink = ev.target.closest('.nav-link');
                if (navLink && navLink.closest('.o_notebook_headers')) {
                    console.log("Notebook tab clicked, initializing canvas...");
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
                                console.log("Tab pane became active, initializing canvas...");
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
        let clickHandler = null;

        onMounted(() => {
            console.log("Performance controller mounted");

            // Event handler para el botón "Calcular"
            clickHandler = (ev) => {
                const btn = ev.target.closest(".calcular_button");
                if (!btn) return;
                
                console.log("Calcular button clicked!");
                ev.preventDefault();
                ev.stopPropagation();
                
                const d = self.model?.root?.data || {};
                const t = d.temperatura;
                const p = d.peso;
                
                console.log(`Calculating with peso: ${p}, temperatura: ${t}`);

                if (el(K.canvas_r22_in) && el(K.canvas_r22_out)) {
                    const p_out = calc_peso(p, K.inicio_eje_r22, K.proporcion_beta_out, true, false);
                    const p_in  = calc_peso(p, K.inicio_eje_r22, K.proporcion_beta_in,  true, false);
                    const a_out = calc_altura(K.temperaturas_beta_out, t, p_out);
                    const a_in  = calc_altura(K.temperaturas_beta_in,  t, p_in);
                    paintPoint(K.canvas_r22_in,  K.src_r22_in,  K.inicio_eje_x_beta_in,  K.inicio_eje_y_beta_in,  K.altura_imagen_beta_in,  p_in,  a_in);
                    paintPoint(K.canvas_r22_out, K.src_r22_out, K.inicio_eje_x_beta_out, K.inicio_eje_y_beta_out, K.altura_imagen_beta_out, p_out, a_out);
                }
                if (el(K.canvas_r22_2_in) && el(K.canvas_r22_2_out)) {
                    const p_out = calc_peso(p, K.inicio_eje_r22_2_out, K.proporcion_beta_2_out, true, false);
                    const p_in  = calc_peso(p, K.inicio_eje_r22_2_in,  K.proporcion_beta_2_in,  true, true);
                    const a_out = calc_altura(K.temperaturas_beta_2_out, t, p_out);
                    const a_in  = calc_altura(K.temperaturas_beta_2_in,  t, p_in);
                    paintPoint(K.canvas_r22_2_in,  K.src_r22_2_in,  K.inicio_eje_x_beta_2_in,  K.inicio_eje_y_beta_2_in,  K.altura_imagen_beta_2_in,  p_in,  a_in);
                    paintPoint(K.canvas_r22_2_out, K.src_r22_2_out, K.inicio_eje_x_beta_2_out, K.inicio_eje_y_beta_2_out, K.altura_imagen_beta_2_out, p_out, a_out);
                }
                if (el(K.canvas_cabri_in) && el(K.canvas_cabri_out)) {
                    const p_cabri = calc_peso(p, K.inicio_eje_cabri, K.proporcion_cabri, false, true);
                    const a_in  = calc_altura(K.temperaturas_cabri_in,  t, p_cabri);
                    const a_out = calc_altura(K.temperaturas_cabri_out, t, p_cabri);
                    paintPoint(K.canvas_cabri_in,  K.src_cabri_in,  K.inicio_eje_x_cabri_in,  K.inicio_eje_y_cabri_in,  K.altura_imagen_cabri_in,  p_cabri, a_in);
                    paintPoint(K.canvas_cabri_out, K.src_cabri_out, K.inicio_eje_x_cabri_out, K.inicio_eje_y_cabri_out, K.altura_imagen_cabri_out, p_cabri, a_out);
                }
                if (el(K.canvas_r44_2_in) && el(K.canvas_r44_2_out)) {
                    const p_in  = calc_peso(p, K.inicio_eje_r44_2_in,  K.proporcion_r44_2_in,  true, false);
                    const p_out = calc_peso(p, K.inicio_eje_r44_2_out, K.proporcion_r44_2_out, true, false);
                    const a_in  = calc_altura(K.temperaturas_r44_2_ige, t, p_in);
                    const a_out = calc_altura(K.temperaturas_r44_2_oge, t, p_out);
                    paintPoint(K.canvas_r44_2_in,  K.src_r44_2_in,  K.inicio_eje_x_r44_2_in,  K.inicio_eje_y_r44_2_in,  K.altura_imagen_r44, p_in,  a_in);
                    paintPoint(K.canvas_r44_2_out, K.src_r44_2_out, K.inicio_eje_x_r44_2_out, K.inicio_eje_y_r44_2_out, K.altura_imagen_r44, p_out, a_out);
                }
                if (el(K.canvas_r44_in) && el(K.canvas_r44_out)) {
                    const p_r44 = calc_peso(p, K.inicio_eje_r44, K.proporcion_r44, true, false);
                    const a_in  = calc_altura(K.temperaturas_r44_ige, t, p_r44);
                    const a_out = calc_altura(K.temperaturas_r44_oge, t, p_r44);
                    paintPoint(K.canvas_r44_in,  K.src_r44_in,  K.inicio_eje_x_r44_in,  K.inicio_eje_y_r44_in,  K.altura_imagen_r44, p_r44, a_in);
                    paintPoint(K.canvas_r44_out, K.src_r44_out, K.inicio_eje_x_r44_out, K.inicio_eje_y_r44_out, K.altura_imagen_r44, p_r44, a_out);
                }
                if (el(K.canvas_ec_in) && el(K.canvas_ec_out)) {
                    const p_in  = calc_peso(p, K.inicio_eje_ec, K.proporcion_ec_in,  false, false);
                    const p_out = calc_peso(p, K.inicio_eje_ec, K.proporcion_ec_out, false, false);
                    const a_in  = calc_altura(K.temperaturas_ec_in,  t, p_in);
                    const a_out = calc_altura(K.temperaturas_ec_out, t, p_out);
                    paintPoint(K.canvas_ec_in,  K.src_ec_in,  K.inicio_eje_x_ec_in,  K.inicio_eje_y_ec_in,  K.altura_imagen_ec_in,  p_in,  a_in);
                    paintPoint(K.canvas_ec_out, K.src_ec_out, K.inicio_eje_x_ec_out, K.inicio_eje_y_ec_out, K.altura_imagen_ec_out, p_out, a_out);
                }
                if (el(K.canvas_hil_in) && el(K.canvas_hil_out)) {
                    const p_in  = calc_peso(p, K.inicio_eje_hil, K.proporcion_hil_in,  false, false);
                    const p_out = calc_peso(p, K.inicio_eje_hil, K.proporcion_hil_out, false, false);
                    const a_in  = calc_altura(K.temperaturas_hil_in,  t, p_in);
                    const a_out = calc_altura(K.temperaturas_hil_out, t, p_out);
                    paintPoint(K.canvas_hil_in,  K.src_hil_in,  K.inicio_eje_x_hil_in,  K.inicio_eje_y_hil_in,  K.altura_imagen_hil_in,  p_in,  a_in);
                    paintPoint(K.canvas_hil_out, K.src_hil_out, K.inicio_eje_x_hil_out, K.inicio_eje_y_hil_out, K.altura_imagen_hil_out, p_out, a_out);
                }
            };
            
            // Adjuntar listener directamente a los botones usando onclick
            setTimeout(() => {
                const buttons = document.querySelectorAll('.calcular_button');
                console.log(`Attaching listeners to ${buttons.length} calcular buttons`);
                buttons.forEach((btn, idx) => {
                    console.log(`Button ${idx} details:`, {
                        className: btn.className,
                        text: btn.textContent?.trim(),
                        tagName: btn.tagName,
                        type: btn.type,
                        hasOnclick: !!btn.onclick
                    });
                    
                    // Usar onclick en lugar de addEventListener para evitar que Odoo lo bloquee
                    btn.onclick = (ev) => {
                        console.log("Button onclick triggered!");
                        clickHandler(ev);
                        return false; // Prevenir comportamiento default
                    };
                    
                    // Verificar que se asignó
                    console.log(`Listener ${idx} attached, onclick is now:`, typeof btn.onclick);
                });
                
                // Test: hacer click programático
                if (buttons.length > 0) {
                    console.log("Testing programmatic click...");
                    setTimeout(() => {
                        buttons[0].click();
                    }, 2000);
                }
            }, 500);
            
            // También adjuntar después de 1 segundo por si el botón se renderiza tarde
            setTimeout(() => {
                const buttons = document.querySelectorAll('.calcular_button');
                if (buttons.length > 0) {
                    buttons.forEach((btn) => {
                        if (!btn.onclick) {
                            btn.onclick = (ev) => {
                                console.log("Button onclick triggered (delayed)!");
                                clickHandler(ev);
                                return false;
                            };
                        }
                    });
                }
            }, 1000);
            
            // Registrar el event listener en el documento para capturar todos los clicks
            document.addEventListener("click", clickHandler, true);
            
            console.log("Calcular button listener registered");
        });

        onWillUnmount(() => {
            // Limpiar event listener al desmontar
            if (clickHandler) {
                document.removeEventListener("click", clickHandler, true);
            }
        });
    },

    async saveButtonClicked(params = {}) {
        // Guardar canvas como imágenes antes del save
        if (this.props.resModel === "leulit.performance") {
            try {
                let cin = "", cout = "";
                
                // Determinar qué canvas están activos
                if (el(K.canvas_hil_in + "_div")   && el(K.canvas_hil_out + "_div"))   { cin = K.canvas_hil_in;   cout = K.canvas_hil_out; }
                if (el(K.canvas_ec_in + "_div")    && el(K.canvas_ec_out + "_div"))    { cin = K.canvas_ec_in;    cout = K.canvas_ec_out; }
                if (el(K.canvas_r44_in + "_div")   && el(K.canvas_r44_out + "_div"))   { cin = K.canvas_r44_in;   cout = K.canvas_r44_out; }
                if (el(K.canvas_r44_2_in + "_div") && el(K.canvas_r44_2_out + "_div")) { cin = K.canvas_r44_2_in; cout = K.canvas_r44_2_out; }
                if (el(K.canvas_cabri_in + "_div") && el(K.canvas_cabri_out + "_div")) { cin = K.canvas_cabri_in; cout = K.canvas_cabri_out; }
                if (el(K.canvas_r22_in + "_div")   && el(K.canvas_r22_out + "_div"))   { cin = K.canvas_r22_in;   cout = K.canvas_r22_out; }
                if (el(K.canvas_r22_2_in + "_div") && el(K.canvas_r22_2_out + "_div")) { cin = K.canvas_r22_2_in; cout = K.canvas_r22_2_out; }

                const extra = {};
                if (cin && el(cin))   extra.ige = el(cin).toDataURL("image/jpeg");
                if (cout && el(cout)) extra.oge = el(cout).toDataURL("image/jpeg");
                
                if (Object.keys(extra).length && this.model?.root) {
                    console.log("Saving performance canvas images...");
                    await this.model.root.update(extra, { save: false });
                }
            } catch (error) {
                console.error("Error saving performance canvas:", error);
            }
        }
        
        // Llamar al save original
        return super.saveButtonClicked(params);
    },
});
