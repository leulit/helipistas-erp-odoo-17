/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Widget de Mapa Meteorológico
 * Permite seleccionar un punto o polilínea en el mapa
 * y obtener información meteorológica
 */
export class MeteoMapWidget extends Component {
    static template = "leulit_meteo.MeteoMapWidget";
    static props = {
        ...standardFieldProps,
        readonly: { type: Boolean, optional: true },
        config: { type: Object, optional: true },
    };

    setup() {
        this.mapRef = useRef("mapContainer");
        this.map = null;
        this.markers = [];
        this.polyline = null;
        this.state = useState({
            isPolylineMode: false,
            points: [],
            loading: false,
        });

        onMounted(() => this.initMap());
        onWillUnmount(() => this.destroyMap());
    }

    /**
     * Inicializa el mapa usando Leaflet
     */
    async initMap() {
        if (typeof L === 'undefined') {
            console.error('Leaflet no está cargado');
            return;
        }

        // Obtener coordenadas iniciales desde el registro
        const record = this.props.record;
        const lat = record.data.latitud || 40.4168; // Madrid por defecto
        const lng = record.data.longitud || -3.7038;
        const isPolyline = record.data.es_polilinea || false;

        // Crear el mapa centrado en las coordenadas
        this.map = L.map(this.mapRef.el, {
            center: [lat, lng],
            zoom: 6,
            zoomControl: true,
        });

        // Agregar capa de tiles (OpenStreetMap)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19,
        }).addTo(this.map);

        // Inicializar modo
        this.state.isPolylineMode = isPolyline;

        // Cargar puntos existentes si es polilínea
        if (isPolyline && record.data.puntos_ids) {
            await this.loadExistingPoints();
        } else if (!isPolyline && lat && lng) {
            // Agregar marker único
            this.addMarker(lat, lng);
        }

        // Agregar event listeners
        if (!this.props.readonly) {
            this.map.on('click', this.onMapClick.bind(this));
        }

        // Invalidate size para asegurar render correcto
        setTimeout(() => {
            if (this.map) {
                this.map.invalidateSize();
            }
        }, 100);
    }

    /**
     * Destruye el mapa al desmontar el componente
     */
    destroyMap() {
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
    }

    /**
     * Carga puntos existentes para polilíneas
     */
    async loadExistingPoints() {
        const record = this.props.record;
        const puntosIds = record.data.puntos_ids || [];

        if (!puntosIds.length) return;

        try {
            // Leer los puntos desde el servidor
            const points = await this.props.record.model.orm.read(
                'leulit.meteo.consulta.punto',
                puntosIds,
                ['latitud', 'longitud', 'secuencia', 'nombre'],
                {}
            );

            // Ordenar por secuencia
            points.sort((a, b) => a.secuencia - b.secuencia);

            // Agregar markers
            this.state.points = [];
            const latLngs = [];
            
            for (const point of points) {
                const marker = this.addMarker(point.latitud, point.longitud, point.nombre);
                this.state.points.push({
                    lat: point.latitud,
                    lng: point.longitud,
                    nombre: point.nombre,
                });
                latLngs.push([point.latitud, point.longitud]);
            }

            // Dibujar polilínea
            if (latLngs.length > 1) {
                this.drawPolyline(latLngs);
                
                // Ajustar vista para mostrar todos los puntos
                const bounds = L.latLngBounds(latLngs);
                this.map.fitBounds(bounds, { padding: [50, 50] });
            }
        } catch (error) {
            console.error('Error cargando puntos:', error);
        }
    }

    /**
     * Maneja el click en el mapa
     */
    onMapClick(e) {
        const { lat, lng } = e.latlng;

        if (this.state.isPolylineMode) {
            // Agregar punto a la polilínea
            this.addPointToPolyline(lat, lng);
        } else {
            // Reemplazar marker único
            this.clearMarkers();
            this.addMarker(lat, lng);
            this.updateRecordCoordinates(lat, lng);
        }
    }

    /**
     * Agrega un marker al mapa
     */
    addMarker(lat, lng, label = null) {
        const marker = L.marker([lat, lng], { draggable: !this.props.readonly })
            .addTo(this.map);

        if (label) {
            marker.bindPopup(label);
        }

        // Permitir arrastrar si no es readonly
        if (!this.props.readonly) {
            marker.on('dragend', (e) => {
                const position = e.target.getLatLng();
                if (this.state.isPolylineMode) {
                    this.updatePolylinePoint(marker, position.lat, position.lng);
                } else {
                    this.updateRecordCoordinates(position.lat, position.lng);
                }
            });

            // Permitir eliminar con click derecho en modo polilínea
            if (this.state.isPolylineMode) {
                marker.on('contextmenu', () => {
                    this.removePointFromPolyline(marker);
                });
            }
        }

        this.markers.push(marker);
        return marker;
    }

    /**
     * Agregar punto a la polilínea
     */
    addPointToPolyline(lat, lng) {
        const pointNumber = this.state.points.length + 1;
        const label = `Punto ${pointNumber}`;
        
        this.addMarker(lat, lng, label);
        this.state.points.push({ lat, lng, nombre: label });

        // Redibujar polilínea
        this.redrawPolyline();
    }

    /**
     * Actualiza un punto de la polilínea después de arrastrar
     */
    updatePolylinePoint(marker, lat, lng) {
        const index = this.markers.indexOf(marker);
        if (index !== -1 && index < this.state.points.length) {
            this.state.points[index].lat = lat;
            this.state.points[index].lng = lng;
            this.redrawPolyline();
        }
    }

    /**
     * Elimina un punto de la polilínea
     */
    removePointFromPolyline(marker) {
        const index = this.markers.indexOf(marker);
        if (index !== -1) {
            this.markers.splice(index, 1);
            this.state.points.splice(index, 1);
            this.map.removeLayer(marker);
            this.redrawPolyline();
        }
    }

    /**
     * Redibuja la polilínea
     */
    redrawPolyline() {
        // Eliminar polilínea anterior
        if (this.polyline) {
            this.map.removeLayer(this.polyline);
        }

        // Dibujar nueva polilínea si hay suficientes puntos
        if (this.state.points.length > 1) {
            const latLngs = this.state.points.map(p => [p.lat, p.lng]);
            this.drawPolyline(latLngs);
        }

        // Actualizar etiquetas de puntos
        this.markers.forEach((marker, i) => {
            marker.setPopupContent(`Punto ${i + 1}`);
        });
    }

    /**
     * Dibuja una polilínea en el mapa
     */
    drawPolyline(latLngs) {
        this.polyline = L.polyline(latLngs, {
            color: '#3388ff',
            weight: 3,
            opacity: 0.7,
        }).addTo(this.map);
    }

    /**
     * Limpia todos los markers
     */
    clearMarkers() {
        this.markers.forEach(marker => this.map.removeLayer(marker));
        this.markers = [];
        
        if (this.polyline) {
            this.map.removeLayer(this.polyline);
            this.polyline = null;
        }
        
        this.state.points = [];
    }

    /**
     * Actualiza las coordenadas en el registro (modo punto único)
     */
    updateRecordCoordinates(lat, lng) {
        this.props.record.update({
            latitud: lat,
            longitud: lng,
        });
    }

    /**
     * Toggle modo polilínea
     */
    togglePolylineMode() {
        this.state.isPolylineMode = !this.state.isPolylineMode;
        this.clearMarkers();
        
        this.props.record.update({
            es_polilinea: this.state.isPolylineMode,
        });
    }

    /**
     * Guarda la polilínea en el registro
     */
    async savePolyline() {
        if (!this.state.points.length) {
            alert('Debe agregar al menos un punto a la polilínea');
            return;
        }

        this.state.loading = true;

        try {
            const record = this.props.record;
            
            // Preparar datos de puntos
            const puntosData = this.state.points.map((point, index) => ({
                secuencia: index + 1,
                nombre: point.nombre || `Punto ${index + 1}`,
                latitud: point.lat,
                longitud: point.lng,
            }));

            // Eliminar puntos anteriores y crear nuevos
            const commands = [
                [5], // Delete all
                ...puntosData.map(p => [0, 0, p]) // Create new points
            ];

            await record.update({
                puntos_ids: commands,
                es_polilinea: true,
            });

            // Notificación de éxito
            this.env.services.notification.add('Polilínea guardada correctamente', {
                type: 'success',
            });

        } catch (error) {
            console.error('Error guardando polilínea:', error);
            this.env.services.notification.add('Error al guardar la polilínea', {
                type: 'danger',
            });
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Centra el mapa en una ubicación
     */
    centerMap() {
        if (this.state.points.length > 0) {
            const latLngs = this.state.points.map(p => [p.lat, p.lng]);
            const bounds = L.latLngBounds(latLngs);
            this.map.fitBounds(bounds, { padding: [50, 50] });
        } else if (this.markers.length > 0) {
            const marker = this.markers[0];
            this.map.setView(marker.getLatLng(), 10);
        }
    }
}

// Registrar el widget en el registro de campos
registry.category("fields").add("meteo_map", MeteoMapWidget);
