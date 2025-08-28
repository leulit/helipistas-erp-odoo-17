/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";

const _frSetup = FormRenderer.prototype.setup;
const _frMounted = FormRenderer.prototype.mounted;

patch(FormRenderer.prototype, {
    name: "leulit_operaciones.gmap_aerovia",

    setup() {
        if (_frSetup) _frSetup.apply(this, arguments);
        this.orm = this.env.services.orm;
    },

    async mounted() {
        if (_frMounted) _frMounted.apply(this, arguments);

        const rec = this.props?.record;
        const model = rec?.model || this.props?.archInfo?.model;
        if (model !== "leulit.ruta_aerovia") return;

        const host = this.el.querySelector(".o_google_map_view");
        if (!host || !window.google || !google.maps) return;

        const map = new google.maps.Map(host, {
            mapTypeId: google.maps.MapTypeId.ROADMAP,
            minZoom: 2,
            maxZoom: 20,
            fullscreenControl: true,
            mapTypeControl: true,
        });
        const infoWindow = new google.maps.InfoWindow();

        const [item] = await this.orm.read("leulit.ruta_aerovia", [rec.resId], [
            "name", "sp_lat", "sp_lng", "ep_lat", "ep_lng",
        ]);
        if (!item) return;

        const sp = new google.maps.LatLng(item.sp_lat, item.sp_lng);
        const ep = new google.maps.LatLng(item.ep_lat, item.ep_lng);
        const icon = {
            url: "http://maps.google.com/mapfiles/kml/pal4/icon57.png",
            size: new google.maps.Size(30, 30),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(15, 15),
        };
        new google.maps.Marker({ map, position: sp, draggable: false, icon });
        new google.maps.Marker({ map, position: ep, draggable: false, icon });

        const poly = new google.maps.Polyline({
            path: [sp, ep],
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

        const bounds = new google.maps.LatLngBounds();
        bounds.extend(sp); bounds.extend(ep);
        map.fitBounds(bounds);
    },
});
