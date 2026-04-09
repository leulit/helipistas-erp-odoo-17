/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { onMounted } from "@odoo/owl";

const GMAPS_API_KEY = "AIzaSyCh4m4h_SZyhCxLxZ_3jmmApRLI2hBndmE";
const GMAPS_SRC = `https://maps.googleapis.com/maps/api/js?v=quarterly&key=${GMAPS_API_KEY}&libraries=geometry,drawing`;

let gmapsPromise = null;

function loadGoogleMaps() {
    if (gmapsPromise) return gmapsPromise;
    if (window.google && window.google.maps) {
        gmapsPromise = Promise.resolve();
        return gmapsPromise;
    }
    gmapsPromise = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = GMAPS_SRC;
        script.async = true;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
    return gmapsPromise;
}

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        const self = this;

        onMounted(() => {
            const model = self.props?.record?.resModel;
            if (model !== "leulit.ruta_aerovia") return;

            setTimeout(async () => {
                const host = document.getElementById("gmap_aerovia_div");
                if (!host) return;

                const resId = self.props?.record?.resId;
                if (!resId) return;

                await loadGoogleMaps();

                const map = new google.maps.Map(host, {
                    mapTypeId: google.maps.MapTypeId.ROADMAP,
                    minZoom: 2,
                    maxZoom: 20,
                    fullscreenControl: true,
                    mapTypeControl: true,
                });
                const infoWindow = new google.maps.InfoWindow();

                // Traer todas las aerovías activas
                const todas = await self.env.services.orm.searchRead(
                    "leulit.ruta_aerovia",
                    [["activo", "=", true]],
                    ["id", "name", "sp_lat", "sp_lng", "ep_lat", "ep_lng"],
                );

                const bounds = new google.maps.LatLngBounds();
                const iconCircle = {
                    url: "http://maps.google.com/mapfiles/kml/pal4/icon57.png",
                    size: new google.maps.Size(30, 30),
                    origin: new google.maps.Point(0, 0),
                    anchor: new google.maps.Point(15, 15),
                };
                const iconFlag = {
                    url: "http://maps.google.com/mapfiles/kml/pal4/icon53.png",
                    size: new google.maps.Size(30, 30),
                    origin: new google.maps.Point(0, 5),
                    anchor: new google.maps.Point(15, 15),
                };

                for (const item of todas) {
                    const isCurrent = item.id === resId;
                    const sp = new google.maps.LatLng(item.sp_lat, item.sp_lng);
                    const ep = new google.maps.LatLng(item.ep_lat, item.ep_lng);

                    // Marcadores: icono de bandera para la actual, círculo para el resto
                    new google.maps.Marker({ map, position: sp, draggable: false, icon: isCurrent ? iconFlag : iconCircle });
                    new google.maps.Marker({ map, position: ep, draggable: false, icon: isCurrent ? iconFlag : iconCircle });

                    // Línea: roja para la actual, azul para el resto
                    const poly = new google.maps.Polyline({
                        path: [sp, ep],
                        geodesic: true,
                        strokeColor: isCurrent ? "#ff0000" : "#0000ff",
                        strokeOpacity: isCurrent ? 1.0 : 0.75,
                        strokeWeight: isCurrent ? 3 : 2,
                    });
                    poly.setMap(map);
                    if (!isCurrent) {
                        const itemId = item.id;
                        const itemName = item.name;
                        google.maps.event.addListener(poly, "click", (ev) => {
                            infoWindow.setContent(`
                                <div style="padding:4px">
                                    <b>${itemId}.- ${itemName}</b><br/>
                                    <button id="gmap_open_btn_${itemId}" style="margin-top:6px;cursor:pointer">Abrir</button>
                                </div>
                            `);
                            infoWindow.setPosition(ev.latLng);
                            infoWindow.open(map);
                            google.maps.event.addListenerOnce(infoWindow, "domready", () => {
                                const btn = document.getElementById(`gmap_open_btn_${itemId}`);
                                if (btn) {
                                    btn.addEventListener("click", () => {
                                        self.env.services.action.doAction({
                                            type: "ir.actions.act_window",
                                            res_model: "leulit.ruta_aerovia",
                                            res_id: itemId,
                                            views: [[false, "form"]],
                                            target: "current",
                                        });
                                    });
                                }
                            });
                        });
                    }

                    // El zoom se ajusta a la aerovía actual
                    if (isCurrent) {
                        bounds.extend(sp);
                        bounds.extend(ep);
                    }
                }

                if (!bounds.isEmpty()) map.fitBounds(bounds);
            }, 100);
        });
    },
});
