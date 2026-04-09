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

async function fetchAerovias(orm, rutaId) {
    // aerovia_ids es One2many de leulit.rel_ruta_aerovia (modelo intermedio)
    // que tiene aerovia_id -> Many2one de leulit.ruta_aerovia
    const relRecords = await orm.searchRead(
        "leulit.rel_ruta_aerovia",
        [["ruta_id", "=", rutaId]],
        ["aerovia_id"],
    );
    const aeroviaIds = relRecords.map(r => r.aerovia_id[0]).filter(Boolean);
    if (!aeroviaIds.length) return [];
    return await orm.read("leulit.ruta_aerovia", aeroviaIds, [
        "name", "sp_lat", "sp_lng", "ep_lat", "ep_lng",
    ]);
}

function drawAerovias(map, infoWindow, aerovias) {
    const bounds = new google.maps.LatLngBounds();
    const iconCircle = {
        url: "http://maps.google.com/mapfiles/kml/pal4/icon57.png",
        size: new google.maps.Size(30, 30),
        origin: new google.maps.Point(0, 0),
        anchor: new google.maps.Point(15, 15),
    };

    for (const item of aerovias) {
        const sp = new google.maps.LatLng(item.sp_lat, item.sp_lng);
        const ep = new google.maps.LatLng(item.ep_lat, item.ep_lng);

        const spMarker = new google.maps.Marker({ map, position: sp, draggable: false, icon: iconCircle });
        const epMarker = new google.maps.Marker({ map, position: ep, draggable: false, icon: iconCircle });
        bounds.extend(spMarker.getPosition());
        bounds.extend(epMarker.getPosition());

        const poly = new google.maps.Polyline({
            path: [spMarker.getPosition(), epMarker.getPosition()],
            geodesic: true,
            strokeColor: "#0000ff",
            strokeOpacity: 0.75,
            strokeWeight: 2,
            infoWindowContent: `${item.id}.- ${item.name}`,
        });
        poly.setMap(map);
        google.maps.event.addListener(poly, "click", (ev) => {
            infoWindow.setContent(poly.infoWindowContent);
            infoWindow.setPosition(ev.latLng);
            infoWindow.open(map);
        });
    }
    if (!bounds.isEmpty()) map.fitBounds(bounds);
}

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        const self = this;

        onMounted(() => {
            const model = self.props?.record?.resModel;
            if (model !== "leulit.ruta") return;

            setTimeout(async () => {
                const el = document.getElementById("gmap_ruta_div");
                if (!el) return;

                const resId = self.props?.record?.resId;
                if (!resId) return;

                await loadGoogleMaps();

                const map = new google.maps.Map(el, {
                    mapTypeId: google.maps.MapTypeId.ROADMAP,
                    minZoom: 2,
                    maxZoom: 20,
                    fullscreenControl: true,
                    mapTypeControl: true,
                });
                const infoWindow = new google.maps.InfoWindow();

                const aerovias = await fetchAerovias(self.env.services.orm, resId);
                drawAerovias(map, infoWindow, aerovias);
            }, 100);
        });
    },
});
