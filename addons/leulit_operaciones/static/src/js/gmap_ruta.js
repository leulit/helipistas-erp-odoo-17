/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";

function initMap(el) {
    if (!el || !window.google || !google.maps) return null;
    return {
        map: new google.maps.Map(el, {
            mapTypeId: google.maps.MapTypeId.ROADMAP,
            minZoom: 2,
            maxZoom: 20,
            fullscreenControl: true,
            mapTypeControl: true,
        }),
        infoWindow: new google.maps.InfoWindow(),
    };
}

async function fetchAerovias(orm, rutaId) {
    const [ruta] = await orm.read("leulit.ruta", [rutaId], ["aerovia_ids"]);
    const ids = ruta?.aerovia_ids || [];
    if (!ids.length) return [];
    return await orm.read("leulit.ruta_aerovia", ids, [
        "name", "sp_lat", "sp_lng", "ep_lat", "ep_lng",
    ]);
}

function drawAerovias(mapCtx, aerovias) {
    const { map, infoWindow } = mapCtx;
    const bounds = new google.maps.LatLngBounds();
    const icon = {
        url: "http://maps.google.com/mapfiles/kml/pal4/icon57.png",
        size: new google.maps.Size(30, 30),
        origin: new google.maps.Point(0, 0),
        anchor: new google.maps.Point(15, 15),
    };

    for (const item of aerovias) {
        const sp = new google.maps.LatLng(item.sp_lat, item.sp_lng);
        const ep = new google.maps.LatLng(item.ep_lat, item.ep_lng);

        const spMarker = new google.maps.Marker({ map, position: sp, draggable: false, icon });
        const epMarker = new google.maps.Marker({ map, position: ep, draggable: false, icon });
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

const _frSetup = FormRenderer.prototype.setup;
const _frMounted = FormRenderer.prototype.mounted;

patch(FormRenderer.prototype, {
    name: "leulit_operaciones.gmap_ruta",

    setup() {
        if (_frSetup) _frSetup.apply(this, arguments);
        this.orm = this.env.services.orm;
    },

    async mounted() {
        if (_frMounted) _frMounted.apply(this, arguments);

        const rec = this.props?.record;
        const model = rec?.model || this.props?.archInfo?.model;
        if (model !== "leulit.ruta") return;

        const el = this.el.querySelector(".o_google_map_view");
        const mapCtx = initMap(el);
        if (!mapCtx || !rec?.resId) return;

        const aerovias = await fetchAerovias(this.orm, rec.resId);
        drawAerovias(mapCtx, aerovias);
    },
});
