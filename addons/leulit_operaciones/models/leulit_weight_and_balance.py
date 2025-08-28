# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_weight_and_balance(models.Model):
    _name           = "leulit.weight_and_balance"
    _description    = "leulit_weight_and_balance"


    def btn_save_wizard(self):        
        for item in self:
            item.vuelo_id.weight_and_balance_id = item.id
            if item.fueltakeoff < 0:
                item.write({
                    'valid_takeoff_longcg'      : False,
                    'valid_takeoff_latcg'       : False,
                    'valid_landing_longcg'      : False,
                    'valid_landing_latcg'       : False,
                })
                raise UserError('El valor indicado en el campo combustible al despegue no es correcto')
            else:
                if item.fuellanding < 0:
                    item.write({
                        'valid_takeoff_longcg'      : False,
                        'valid_takeoff_latcg'       : False,
                        'valid_landing_longcg'      : False,
                        'valid_landing_latcg'       : False,
                    })
                    raise UserError('El valor indicado en el campo combustible previsto al aterrizaje no es correcto')
            if item.vuelo_id:
                pax = 0
                if item.frs > 0:
                    pax += 1
                if item.fls > 0:
                    pax += 1
                if item.aftrp > 0:
                    pax += 1
                if item.aftlp > 0:
                    pax += 1
                if item.aftcp > 0:
                    pax += 1
                item.vuelo_id.pasajeros_wb = pax
        return {'type': 'ir.actions.act_window_close'}


    def _get_fields_list(self, tipohelicoptero):
        return {
                    'R22': [
                        'emptyweight',
                        'frs',
                        'fls',
                        'bufrs',
                        'bufls',
                        'forward_right_door',
                        'forward_left_door',
                        'cyclic',
                        'collective',
                        'pedals',
                        'dualcontrols',
                        'items_on_mount_bar_right',
                        'items_on_mount_bar_left'
                        'gancho_carga',
                        'carga_externa',
                        'misc1',
                        'misc2',
                        'fueltakeoff',
                        'fuellanding',
                    ],
                    'R44': [
                        'emptyweight',
                        'frs',
                        'fls',
                        'aftrp',
                        'aftlp',
                        'bufrs',
                        'bufls',
                        'buaftrs',
                        'buaftls',
                        'cineflex',
                        'tyler',
                        'gss',
                        'gancho_carga',
                        'carga_externa',
                        'misc1',
                        'misc2',
                        'fueltakeoff',
                        'fuellanding',
                        'forward_right_door',
                        'forward_left_door',
                        'aft_right_door',
                        'aft_left_door',
                        'cyclic',
                        'collective',
                        'pedals',
                        'dualcontrols',
                        'items_on_mount_bar_right',
                        'items_on_mount_bar_left'
                    ],
                    'EC120B': [
                        'emptyweight',
                        'frs',
                        'fls',
                        'aftrp',
                        'aftlp',
                        'aftcp',
                        'baggage_zonac',
                        'baggage_zonad',
                        'baggage_noseats',
                        'misc1',
                        'af120_camera_mount',
                        'gancho_carga',
                        'carga_externa',
                        'espejo',
                        'misc2',
                        'fueltakeoff',
                        'fuellanding',
                        'forward_right_door',
                        'forward_left_door',
                        'sliding_door',
                        'rear_cargo_door',
                        'dualcontrols',
                        'frontseat',
                        'rearseat',
                    ],
                    'CABRI G2': [
                        'emptyweight',
                        'frs',
                        'fls',
                        'front_baggage',
                        'main_baggage',
                        'misc1',
                        'misc2',
                        'fueltakeoff',
                        'fuellanding',
                        'forward_right_door',
                        'forward_left_door',
                    ],
                }.get(tipohelicoptero, [])


    def _get_fields_list_orm(self):
        for item in self:
            item.fieldslist = self._get_fields_list( item.helicoptero_tipo )

    def _set_data(self, data, valor1, valor2, valor3, prefijo):
        data[prefijo] = valor1
        data[prefijo+'_long_arm'] = valor2
        data[prefijo+'_lat_arm'] = valor3
        return data

    def _set_data_r44(self, data):
        vuelo = self.env['leulit.vuelo'].search([('id','=',data['vuelo_id'])])
        hist_wb = self.env['leulit.hist_weight_and_balance'].search([('fecha','<=',vuelo.fechavuelo),('helicoptero_matricula','=',vuelo.helicoptero_id.name)],order="fecha desc",limit=1)
        if not hist_wb:
            hist_wb = self.env['leulit.hist_weight_and_balance'].search([('fecha','<=',vuelo.fechavuelo),('helicoptero_tipo','=',vuelo.helicoptero_tipo)],order="fecha desc",limit=1)
        data = self._set_data( data, hist_wb.forward_right_door_mass, hist_wb.forward_right_door_long, hist_wb.forward_right_door_lat, 'forward_right_door')
        data = self._set_data( data, hist_wb.forward_left_door_mass, hist_wb.forward_left_door_long, hist_wb.forward_left_door_lat, 'forward_left_door')
        data = self._set_data( data, hist_wb.aft_right_door_mass, hist_wb.aft_right_door_long, hist_wb.aft_right_door_lat, 'aft_right_door')
        data = self._set_data( data, hist_wb.aft_left_door_mass, hist_wb.aft_left_door_long, hist_wb.aft_left_door_lat, 'aft_left_door')
        data = self._set_data( data, hist_wb.cyclic_mass, hist_wb.cyclic_long, hist_wb.cyclic_lat, 'cyclic')
        data = self._set_data( data, hist_wb.collective_mass, hist_wb.collective_long, hist_wb.collective_lat, 'collective')
        data = self._set_data( data, hist_wb.pedals_mass, hist_wb.pedals_long, hist_wb.pedals_lat, 'pedals')
        data = self._set_data( data, hist_wb.dualcontrols_mass, hist_wb.dualcontrols_long, hist_wb.dualcontrols_lat, 'dualcontrols')
        data = self._set_data( data, hist_wb.items_on_mount_bar_right_mass, hist_wb.items_on_mount_bar_right_long, hist_wb.items_on_mount_bar_right_lat, 'items_on_mount_bar_right')
        data = self._set_data( data, hist_wb.items_on_mount_bar_left_mass, hist_wb.items_on_mount_bar_left_long, hist_wb.items_on_mount_bar_left_lat, 'items_on_mount_bar_left')
        data = self._set_data( data, hist_wb.cineflex_mass, hist_wb.cineflex_long, hist_wb.cineflex_lat, 'cineflex')
        data = self._set_data( data, hist_wb.tyler_mass, hist_wb.tyler_long, hist_wb.tyler_lat, 'tyler')
        data = self._set_data( data, hist_wb.gss_mass, hist_wb.gss_long, hist_wb.gss_lat, 'gss')
        data = self._set_data( data, hist_wb.gancho_carga_mass, hist_wb.gancho_carga_long, hist_wb.gancho_carga_lat, 'gancho_carga')
        data = self._set_data( data, hist_wb.carga_externa_mass, hist_wb.carga_externa_long, hist_wb.carga_externa_lat, 'carga_externa')
        data = self._set_data( data, hist_wb.frs_mass, hist_wb.frs_long, hist_wb.frs_lat, 'frs')
        data = self._set_data( data, hist_wb.fls_mass, hist_wb.fls_long, hist_wb.fls_lat, 'fls')
        data = self._set_data( data, hist_wb.aftrp_mass, hist_wb.aftrp_long, hist_wb.aftrp_lat, 'aftrp')
        data = self._set_data( data, hist_wb.aftlp_mass, hist_wb.aftlp_long, hist_wb.aftlp_lat, 'aftlp')
        data = self._set_data( data, hist_wb.bufrs_mass, hist_wb.bufrs_long, hist_wb.bufrs_lat, 'bufrs')
        data = self._set_data( data, hist_wb.bufls_mass, hist_wb.bufls_long, hist_wb.bufls_lat, 'bufls')
        data = self._set_data( data, hist_wb.buaftrs_mass, hist_wb.buaftrs_long, hist_wb.buaftrs_lat, 'buaftrs')
        data = self._set_data( data, hist_wb.buaftls_mass, hist_wb.buaftls_long, hist_wb.buaftls_lat, 'buaftls')
        data = self._set_data( data, hist_wb.misc1_mass, hist_wb.misc1_long, hist_wb.misc1_lat, 'misc1')
        data = self._set_data( data, hist_wb.misc2_mass, hist_wb.misc2_long, hist_wb.misc2_lat, 'misc2')
        data = self._set_data( data, data['fueltakeoff'], hist_wb.fueltakeoff_long, hist_wb.fueltakeoff_lat, 'fueltakeoff')
        data = self._set_data( data, hist_wb.takeoff_gw_mass, hist_wb.takeoff_gw_long, hist_wb.takeoff_gw_lat, 'takeoff_gw')
        data = self._set_data( data, data['fuellanding'], hist_wb.fuellanding_long, hist_wb.fuellanding_lat, 'fuellanding')
        data = self._set_data( data, hist_wb.landing_gw_mass, hist_wb.landing_gw_long, hist_wb.landing_gw_lat, 'landing_gw')
        data = self._set_data( data, hist_wb.maswithoutfuel_mass, hist_wb.maswithoutfuel_long, hist_wb.maswithoutfuel_lat, 'maswithoutfuel')
        return data

    def _set_data_r22(self, data):
        vuelo = self.env['leulit.vuelo'].search([('id','=',data['vuelo_id'])])
        hist_wb = self.env['leulit.hist_weight_and_balance'].search([('fecha','<=',vuelo.fechavuelo),('helicoptero_matricula','=',vuelo.helicoptero_id.name)],order="fecha desc",limit=1)
        if not hist_wb:
            hist_wb = self.env['leulit.hist_weight_and_balance'].search([('fecha','<=',vuelo.fechavuelo),('helicoptero_tipo','=',vuelo.helicoptero_tipo)],order="fecha desc",limit=1)
        data = self._set_data( data, hist_wb.forward_right_door_mass, hist_wb.forward_right_door_long, hist_wb.forward_right_door_lat, 'forward_right_door')
        data = self._set_data( data, hist_wb.forward_left_door_mass, hist_wb.forward_left_door_long, hist_wb.forward_left_door_lat, 'forward_left_door')
        data = self._set_data( data, hist_wb.cyclic_mass, hist_wb.cyclic_long, hist_wb.cyclic_lat, 'cyclic')
        data = self._set_data( data, hist_wb.collective_mass, hist_wb.collective_long, hist_wb.collective_lat, 'collective')
        data = self._set_data( data, hist_wb.pedals_mass, hist_wb.pedals_long, hist_wb.pedals_lat, 'pedals')
        data = self._set_data( data, hist_wb.dualcontrols_mass, hist_wb.dualcontrols_long, hist_wb.dualcontrols_lat, 'dualcontrols')
        data = self._set_data( data, hist_wb.items_on_mount_bar_right_mass, hist_wb.items_on_mount_bar_right_long, hist_wb.items_on_mount_bar_right_lat, 'items_on_mount_bar_right')
        data = self._set_data( data, hist_wb.items_on_mount_bar_left_mass, hist_wb.items_on_mount_bar_left_long, hist_wb.items_on_mount_bar_left_lat, 'items_on_mount_bar_left')
        data = self._set_data( data, hist_wb.gancho_carga_mass, hist_wb.gancho_carga_long, hist_wb.gancho_carga_lat, 'gancho_carga')
        data = self._set_data( data, hist_wb.carga_externa_mass, hist_wb.carga_externa_long, hist_wb.carga_externa_lat, 'carga_externa')
        data = self._set_data( data, hist_wb.frs_mass, hist_wb.frs_long, hist_wb.frs_lat, 'frs')
        data = self._set_data( data, hist_wb.fls_mass, hist_wb.fls_long, hist_wb.fls_lat, 'fls')
        data = self._set_data( data, hist_wb.bufrs_mass, hist_wb.bufrs_long, hist_wb.bufrs_lat, 'bufrs')
        data = self._set_data( data, hist_wb.bufls_mass, hist_wb.bufls_long, hist_wb.bufls_lat, 'bufls')
        data = self._set_data( data, hist_wb.misc1_mass, hist_wb.misc1_long, hist_wb.misc1_lat, 'misc1')
        data = self._set_data( data, hist_wb.misc2_mass, hist_wb.misc2_long, hist_wb.misc2_lat, 'misc2')
        data = self._set_data( data, data['fueltakeoff'], hist_wb.fueltakeoff_long, hist_wb.fueltakeoff_lat, 'fueltakeoff')
        data = self._set_data( data, hist_wb.takeoff_gw_mass, hist_wb.takeoff_gw_long, hist_wb.takeoff_gw_lat, 'takeoff_gw')
        data = self._set_data( data, data['fuellanding'], hist_wb.fuellanding_long, hist_wb.fuellanding_lat, 'fuellanding')
        data = self._set_data( data, hist_wb.landing_gw_mass, hist_wb.landing_gw_long, hist_wb.landing_gw_lat, 'landing_gw')
        
        return data

    def _set_data_rEC120B(self, data):
        vuelo = self.env['leulit.vuelo'].search([('id','=',data['vuelo_id'])])
        hist_wb = self.env['leulit.hist_weight_and_balance'].search([('fecha','<=',vuelo.fechavuelo),('helicoptero_matricula','=',vuelo.helicoptero_id.name)],order="fecha desc",limit=1)
        if not hist_wb:
            hist_wb = self.env['leulit.hist_weight_and_balance'].search([('fecha','<=',vuelo.fechavuelo),('helicoptero_tipo','=',vuelo.helicoptero_tipo)],order="fecha desc",limit=1)
        data = self._set_data( data, hist_wb.forward_right_door_mass, hist_wb.forward_right_door_long, hist_wb.forward_right_door_lat, 'forward_right_door')
        data = self._set_data( data, hist_wb.forward_left_door_mass, hist_wb.forward_left_door_long, hist_wb.forward_left_door_lat, 'forward_left_door')
        data = self._set_data( data, hist_wb.sliding_door_mass, hist_wb.sliding_door_long, hist_wb.sliding_door_lat, 'sliding_door')
        data = self._set_data( data, hist_wb.rear_cargo_door_mass, hist_wb.rear_cargo_door_long, hist_wb.rear_cargo_door_lat, 'rear_cargo_door')
        data = self._set_data( data, hist_wb.frontseat_mass, hist_wb.frontseat_long, hist_wb.frontseat_lat, 'frontseat')
        data = self._set_data( data, hist_wb.rearseat_mass, hist_wb.rearseat_long, hist_wb.rearseat_lat, 'rearseat')
        data = self._set_data( data, hist_wb.dualcontrols_mass, hist_wb.dualcontrols_long, hist_wb.dualcontrols_lat, 'dualcontrols')
        data = self._set_data( data, hist_wb.baggage_noseats_mass, hist_wb.baggage_noseats_long, hist_wb.baggage_noseats_lat, 'baggage_noseats')
        data = self._set_data( data, hist_wb.baggage_zonac_mass, hist_wb.baggage_zonac_long, hist_wb.baggage_zonac_lat, 'baggage_zonac')
        data = self._set_data( data, hist_wb.baggage_zonad_mass, hist_wb.baggage_zonad_long, hist_wb.baggage_zonad_lat, 'baggage_zonad')
        data = self._set_data( data, hist_wb.frs_mass, hist_wb.frs_long, hist_wb.frs_lat, 'frs')
        data = self._set_data( data, hist_wb.fls_mass, hist_wb.fls_long, hist_wb.fls_lat, 'fls')
        data = self._set_data( data, hist_wb.aftrp_mass, hist_wb.aftrp_long, hist_wb.aftrp_lat, 'aftrp')
        data = self._set_data( data, hist_wb.aftlp_mass, hist_wb.aftlp_long, hist_wb.aftlp_lat, 'aftlp')
        data = self._set_data( data, hist_wb.aftcp_mass, hist_wb.aftcp_long, hist_wb.aftcp_lat, 'aftcp')
        data = self._set_data( data, hist_wb.af120_camera_mount_mass, hist_wb.af120_camera_mount_long, hist_wb.af120_camera_mount_lat, 'af120_camera_mount')
        data = self._set_data( data, hist_wb.gancho_carga_mass, hist_wb.gancho_carga_long, hist_wb.gancho_carga_lat, 'gancho_carga')
        data = self._set_data( data, hist_wb.carga_externa_mass, hist_wb.carga_externa_long, hist_wb.carga_externa_lat, 'carga_externa')
        data = self._set_data( data, hist_wb.espejo_mass, hist_wb.espejo_long, hist_wb.espejo_lat, 'espejo')
        data = self._set_data( data, hist_wb.misc1_mass, hist_wb.misc1_long, hist_wb.misc1_lat, 'misc1')
        data = self._set_data( data, hist_wb.misc2_mass, hist_wb.misc2_long, hist_wb.misc2_lat, 'misc2')
        data = self._set_data( data, data['fueltakeoff'], hist_wb.fueltakeoff_long, hist_wb.fueltakeoff_lat, 'fueltakeoff')
        data = self._set_data( data, hist_wb.takeoff_gw_mass, hist_wb.takeoff_gw_long, hist_wb.takeoff_gw_lat, 'takeoff_gw')
        data = self._set_data( data, data['fuellanding'], hist_wb.fuellanding_long, hist_wb.fuellanding_lat, 'fuellanding')
        data = self._set_data( data, hist_wb.landing_gw_mass, hist_wb.landing_gw_long, hist_wb.landing_gw_lat, 'landing_gw')
        return data

    def _set_data_cabriG2(self, data):
        vuelo = self.env['leulit.vuelo'].search([('id','=',data['vuelo_id'])])
        hist_wb = self.env['leulit.hist_weight_and_balance'].search([('fecha','<=',vuelo.fechavuelo),('helicoptero_matricula','=',vuelo.helicoptero_id.name)],order="fecha desc",limit=1)
        if not hist_wb:
            hist_wb = self.env['leulit.hist_weight_and_balance'].search([('fecha','<=',vuelo.fechavuelo),('helicoptero_tipo','=',vuelo.helicoptero_tipo)],order="fecha desc",limit=1)
        data = self._set_data( data, hist_wb.forward_right_door_mass, hist_wb.forward_right_door_long, hist_wb.forward_right_door_lat, 'forward_right_door')
        data = self._set_data( data, hist_wb.forward_left_door_mass, hist_wb.forward_left_door_long, hist_wb.forward_left_door_lat, 'forward_left_door')
        data = self._set_data( data, hist_wb.frs_mass, hist_wb.frs_long, hist_wb.frs_lat, 'frs')
        data = self._set_data( data, hist_wb.fls_mass, hist_wb.fls_long, hist_wb.fls_lat, 'fls')
        data = self._set_data( data, hist_wb.main_baggage_mass, hist_wb.main_baggage_long, hist_wb.main_baggage_lat, 'main_baggage')
        data = self._set_data( data, hist_wb.front_baggage_mass, hist_wb.front_baggage_long, hist_wb.front_baggage_lat, 'front_baggage')
        data = self._set_data( data, hist_wb.misc1_mass, hist_wb.misc1_long, hist_wb.misc1_lat, 'misc1')
        data = self._set_data( data, hist_wb.misc2_mass, hist_wb.misc2_long, hist_wb.misc2_lat, 'misc2')
        data = self._set_data( data, data['fueltakeoff'], hist_wb.fueltakeoff_long, hist_wb.fueltakeoff_lat, 'fueltakeoff')
        data = self._set_data( data, hist_wb.takeoff_gw_mass, hist_wb.takeoff_gw_long, hist_wb.takeoff_gw_lat, 'takeoff_gw')
        data = self._set_data( data, data['fuellanding'], hist_wb.fuellanding_long, hist_wb.fuellanding_lat, 'fuellanding')
        data = self._set_data( data, hist_wb.landing_gw_mass, hist_wb.landing_gw_long, hist_wb.landing_gw_lat, 'landing_gw')
        
        return data


    @api.model
    def default_get(self, fields):
        data = super(leulit_weight_and_balance, self).default_get(fields)
        context = self.env.context
        data['fueltakeoff'] = context['default_fueltakeoff']
        data['fuellanding'] = context['default_fuellanding']
        data['helicoptero_tipo'] = context['default_helicoptero_tipo']
        data['helicoptero_modelo'] = context['default_helicoptero_modelo']
        helicoptero = self.env["leulit.helicoptero"].browse(context["default_helicoptero_id"])
        data['emptyweight'] = helicoptero.emptyweight
        data['emptyweight_long_arm'] = helicoptero.longarm
        data['emptyweight_lat_arm'] = helicoptero.latarm
        data = self._set_data( data, data['emptyweight'], data['emptyweight_long_arm'], data['emptyweight_lat_arm'], 'emptyweight')
        data['fieldslist'] = self._get_fields_list( data['helicoptero_tipo'] )
        if data['helicoptero_tipo'] == 'R44':
            data = self._set_data_r44( data )
        else:
            if data['helicoptero_tipo'] == 'R22':
                data = self._set_data_r22( data )
            else:
                if data['helicoptero_tipo'] == 'EC120B':
                    data = self._set_data_rEC120B( data )
                else:
                    if data['helicoptero_tipo'] == 'CABRI G2':
                        data = self._set_data_cabriG2( data )
        if context.get('default_frs'):
            data['frs'] = context['default_frs']
        if context.get('default_fls'):
            data['fls'] = context['default_fls']
        return data

    def change_data_vuelo(self):
        data = {}
        context = self.env.context
        data['fueltakeoff'] = context['default_fueltakeoff']
        data['fuellanding'] = context['default_fuellanding']
        data['helicoptero_tipo'] = context['default_helicoptero_tipo']
        data['helicoptero_modelo'] = context['default_helicoptero_modelo']
        helicoptero = self.env["leulit.helicoptero"].browse(context["default_helicoptero_id"])
        data['emptyweight'] = helicoptero.emptyweight
        data['emptyweight_long_arm'] = helicoptero.longarm
        data['emptyweight_lat_arm'] = helicoptero.latarm
        data = self._set_data( data, data['emptyweight'], data['emptyweight_long_arm'], data['emptyweight_lat_arm'], 'emptyweight')
        data['fieldslist'] = self._get_fields_list( data['helicoptero_tipo'] )
        data['vuelo_id'] = context['default_vuelo_id']
        if data['helicoptero_tipo'] == 'R44':
            data = self._set_data_r44( data )
        else:
            if data['helicoptero_tipo'] == 'R22':
                data = self._set_data_r22( data )
            else:
                if data['helicoptero_tipo'] == 'EC120B':
                    data = self._set_data_rEC120B( data )
                else:
                    if data['helicoptero_tipo'] == 'CABRI G2':
                        data = self._set_data_cabriG2( data )
        if context.get('default_frs'):
            data['frs'] = context['default_frs']
        self.write(data)


    def determineIfPointLiesWithinPolygon(self, locationToTest, polygondat):
        # Check that the argument is actually a LocationObject.

        # Set crossings value to initial zero value.
        iCrossings = 0

        # For each segment of the polygon (i.e. line drawn between each of the polygon's vertices) check whether
        # a ray cast straight down from the test location intersects the segment (keep in mind that the segment
        # may be intersected either coming or going). If the ray does cross the segment, increment the iCrossings
        #  variable.
        for iVertex in range(0, len(polygondat)):

            fSegmentStartX = polygondat[iVertex].fLongitude
            fSegmentStartY = polygondat[iVertex].fLatitude

            # If the last vertex is being tested then it joins the vertex at index 0.
            if iVertex < len(polygondat) - 1:
                fSegmentEndX = polygondat[iVertex + 1].fLongitude
                fSegmentEndY = polygondat[iVertex + 1].fLatitude
            else:
                fSegmentEndX = polygondat[0].fLongitude
                fSegmentEndY = polygondat[0].fLatitude

            fTestPointX = locationToTest.fLongitude
            fTestPointY = locationToTest.fLatitude

            # Quickly check that the ray falls within the range of values of longitude for the start and end of
            # the segment (keep in mind that the segment may be headed east or west).
            if ((fSegmentStartX < fTestPointX) and (fTestPointX < fSegmentEndX)) or ((fSegmentStartX > fTestPointX) and (fTestPointX > fSegmentEndX)):
                # Check if the segment is crossed in the Y axis as well (the point may lie below the segment).
                fT = (fTestPointX - fSegmentEndX) / (fSegmentStartX - fSegmentEndX)
                fCrossingY = ((fT * fSegmentStartY) + ((1 - fT) * fSegmentEndY))
                if fCrossingY >= fTestPointY:
                    iCrossings += 1

            # Check if the point lies on the segment, in particular if it lies precisely on a vertical line segment.
            if (fSegmentStartX == fTestPointX) and (fSegmentStartY <= fTestPointY):
                if fSegmentStartY == fTestPointY:
                    iCrossings += 1
                if fSegmentEndX == fTestPointX:
                    if ((fSegmentStartY <= fTestPointY) and (fTestPointY <= fSegmentEndY)) or ((fSegmentStartY >= fTestPointY) and (fTestPointY >= fSegmentEndY)):
                        iCrossings += 1
                elif fSegmentEndX > fTestPointX:
                    iCrossings += 1
                if polygondat[iVertex - 1].fLongitude > fTestPointX:
                    iCrossings += 1

        # If the number of segment crossings is an even number the point lies outside the polygon. If there is an
        #  odd number of crossings the point lies inside.
        iRemainder = iCrossings % 2
        if iRemainder != 0:
            return True  # Point is inside the polygon.
        else:
            return False  # Point is outside the polygon.

 
    
    @api.model
    def recalculate_weight_and_balance(self):
        numRecords = self.search_count([])
        numblocks = int(numRecords / 100)
        restblocks =int(numRecords % 100)
        for i in range(0,numblocks): 
            inicio = i*numblocks
            for item in self.search([], offset = inicio, limit=100):
                item.updateTotals()
        for item in self.search([], offset = numblocks*100, limit=restblocks):
            item.updateTotals()



    @api.onchange('frs','fls','aftrp','aftlp','aftcp','front_baggage','main_baggage','baggage_zonac','baggage_zonad','bufrs','bufls','buaftrs','buaftls','forward_right_door','forward_right_door_cb','forward_left_door','forward_left_door_cb','aft_right_door','aft_right_door_cb','aft_left_door','aft_left_door_cb','sliding_door','sliding_door_cb','rear_cargo_door','rear_cargo_door_cb','cyclic','cyclic_cb','collective','collective_cb','pedals','pedals_cb','cineflex','cineflex_cb','tyler','tyler_cb','gss','gss_cb','af120_camera_mount','af120_camera_mount_cb','dualcontrols','dualcontrols_cb','frontseat','frontseat_cb','rearseat','rearseat_cb','baggage_noseats','baggage_noseats_cb','misc1','misc2','gancho_carga_cb','gancho_carga','espejo','espejo_cb','carga_externa','carga_externa_cb','items_on_mount_bar_right','items_on_mount_bar_right_cb','items_on_mount_bar_left','items_on_mount_bar_left_cb')
    def updateTotals(self):
        strFieldslist = self.fieldslist.replace('[','').replace(']','').replace("'",'').replace(' ','')
        fieldslist = strFieldslist.split(',')
        total = 0
        total_longmoment = 0
        total_latmoment = 0
        for key in fieldslist:
            docalculation = True
            if hasattr(self, key+'_cb'):
                docalculation = getattr(self,key+'_cb')
            if hasattr(self, key):
                if docalculation:
                    item1 = getattr(self,key)
                    item2 = getattr(self,key+"_long_arm")
                    valor = item1 * item2
                    setattr(self,key+"_long_moment", valor)
                    valor = getattr(self,key+"_long_moment")

                    item1 = getattr(self,key)
                    item2 = getattr(self,key+"_lat_arm")
                    valor = item1 * item2
                    setattr(self,key+"_lat_moment", valor)

                    total += getattr(self,key)
                    total_longmoment += getattr(self,key+"_long_moment")
                    total_latmoment += getattr(self,key+"_lat_moment")
                else:
                    setattr(self,key+"_long_moment", 0)
                    setattr(self,key+"_lat_moment", 0)
                    
        self.takeoff_gw = total - self.fuellanding
        self.takeoff_gw_long_moment = total_longmoment - self.fuellanding_long_moment
        self.takeoff_gw_lat_moment = total_latmoment - self.fuellanding_lat_moment
        self.takeoff_gw_long_arm = (self.takeoff_gw_long_moment / self.takeoff_gw)  if self.takeoff_gw > 0 else 0.0
        self.takeoff_gw_lat_arm = (self.takeoff_gw_lat_moment / self.takeoff_gw)  if self.takeoff_gw > 0 else 0.0
        
        self.landing_gw = total - self.fueltakeoff
        self.landing_gw_long_moment = total_longmoment - self.fueltakeoff_long_moment
        self.landing_gw_lat_moment = total_latmoment - self.fueltakeoff_lat_moment
        self.landing_gw_long_arm = (self.landing_gw_long_moment / self.landing_gw)  if self.landing_gw > 0 else 0.0
        self.landing_gw_lat_arm = (self.landing_gw_lat_moment / self.landing_gw)  if self.landing_gw > 0 else 0.0

        self.maswithoutfuel = total - self.fuellanding - self.fueltakeoff
        self.maswithoutfuel_long_moment = total_longmoment - self.fuellanding_long_moment - self.fueltakeoff_long_moment
        self.maswithoutfuel_lat_moment = total_latmoment - self.fuellanding_lat_moment - self.fueltakeoff_lat_moment
        self.maswithoutfuel_long_arm = (self.maswithoutfuel_long_moment / self.maswithoutfuel)  if self.maswithoutfuel > 0 else 0.0
        self.maswithoutfuel_lat_arm = (self.maswithoutfuel_lat_moment / self.maswithoutfuel)  if self.maswithoutfuel > 0 else 0.0


    vuelo_id = fields.Many2one('leulit.vuelo','Vuelo origen', required=True)
    helicoptero_matricula = fields.Char(related='vuelo_id.helicoptero_id.name')
    tipocalculopasajeros = fields.Selection([('Masa pesada','Masa pesada'),
                                                    ('Masa declarada','Masa declarada (6kg de equpaje de mano y 4kg cómo ropa)'),
                                                    ('Masa estandard','Masa estandard (piloto 85 kg, masculino 104 kg, femenino 86 kg, niño(de 2-12 años 35kg), equipaje mano 6kg, equipos emergencia 3kg)')],
                                                    'Cálculo peso pasajeros', required=True,default="Masa declarada")
    fieldslist = fields.Char(compute=_get_fields_list_orm,string='',store=False)
    helicoptero_tipo = fields.Char('Tipo helicoptero', size=50, readonly=True)
    helicoptero_modelo = fields.Char('Tipo Modelo', size=50, readonly=True)
    name = fields.Char('Nombre', size=50)

    valid_takeoff_longcg = fields.Boolean('Valid TakeOff Long. CG')
    valid_takeoff_latcg = fields.Boolean('Valid TakeOff Lat. CG')
    valid_landing_longcg = fields.Boolean('Valid Landing Long. CG')
    valid_landing_latcg = fields.Boolean('Valid Landing Lat. CG')

    emptyweight = fields.Float('Peso en vacío')
    emptyweight_long_arm = fields.Float('')
    emptyweight_lat_arm = fields.Float('')
    emptyweight_long_moment = fields.Float('')
    emptyweight_lat_moment = fields.Float('')

    forward_right_door = fields.Float('Forward right door')
    forward_right_door_long_arm = fields.Float('')
    forward_right_door_lat_arm = fields.Float('')
    forward_right_door_long_moment = fields.Float('')
    forward_right_door_lat_moment = fields.Float('')
    forward_right_door_cb = fields.Boolean('')

    forward_left_door = fields.Float('Forward left door')
    forward_left_door_long_arm = fields.Float('')
    forward_left_door_lat_arm = fields.Float('')
    forward_left_door_long_moment = fields.Float('')
    forward_left_door_lat_moment = fields.Float('')
    forward_left_door_cb = fields.Boolean('')

    aft_right_door = fields.Float('')
    aft_right_door_long_arm = fields.Float('')
    aft_right_door_lat_arm = fields.Float('')
    aft_right_door_long_moment = fields.Float('')
    aft_right_door_lat_moment = fields.Float('')
    aft_right_door_cb = fields.Boolean('')

    aft_left_door = fields.Float('')
    aft_left_door_long_arm = fields.Float('')
    aft_left_door_lat_arm = fields.Float('')
    aft_left_door_long_moment = fields.Float('')
    aft_left_door_lat_moment = fields.Float('')
    aft_left_door_cb = fields.Boolean('')

    sliding_door = fields.Float('')
    sliding_door_long_arm = fields.Float('')
    sliding_door_lat_arm = fields.Float('')
    sliding_door_long_moment = fields.Float('')
    sliding_door_lat_moment = fields.Float('')
    sliding_door_cb = fields.Boolean('')

    rear_cargo_door = fields.Float('')
    rear_cargo_door_long_arm = fields.Float('')
    rear_cargo_door_lat_arm = fields.Float('')
    rear_cargo_door_long_moment = fields.Float('')
    rear_cargo_door_lat_moment = fields.Float('')
    rear_cargo_door_cb = fields.Boolean('')

    frontseat = fields.Float('')
    frontseat_long_arm = fields.Float('')
    frontseat_lat_arm = fields.Float('')
    frontseat_long_moment = fields.Float('')
    frontseat_lat_moment = fields.Float('')
    frontseat_cb = fields.Boolean('')

    rearseat = fields.Float('')
    rearseat_long_arm = fields.Float('')
    rearseat_lat_arm = fields.Float('')
    rearseat_long_moment = fields.Float('')
    rearseat_lat_moment = fields.Float('')
    rearseat_cb = fields.Boolean('')

    front_baggage = fields.Float('')
    front_baggage_long_arm = fields.Float('')
    front_baggage_lat_arm = fields.Float('')
    front_baggage_long_moment = fields.Float('')
    front_baggage_lat_moment = fields.Float('')

    main_baggage = fields.Float('')
    main_baggage_long_arm = fields.Float('')
    main_baggage_lat_arm = fields.Float('')
    main_baggage_long_moment = fields.Float('')
    main_baggage_lat_moment = fields.Float('')

    baggage_noseats = fields.Float('')
    baggage_noseats_long_arm = fields.Float('')
    baggage_noseats_lat_arm = fields.Float('')
    baggage_noseats_long_moment = fields.Float('')
    baggage_noseats_lat_moment = fields.Float('')
    baggage_noseats_cb = fields.Boolean('')

    baggage_zonac = fields.Float('')
    baggage_zonac_long_arm = fields.Float('')
    baggage_zonac_lat_arm = fields.Float('')
    baggage_zonac_long_moment = fields.Float('')
    baggage_zonac_lat_moment = fields.Float('')

    baggage_zonad = fields.Float('')
    baggage_zonad_long_arm = fields.Float('')
    baggage_zonad_lat_arm = fields.Float('')
    baggage_zonad_long_moment = fields.Float('')
    baggage_zonad_lat_moment = fields.Float('')

    cyclic = fields.Float('')
    cyclic_long_arm = fields.Float('')
    cyclic_lat_arm = fields.Float('')
    cyclic_long_moment = fields.Float('')
    cyclic_lat_moment = fields.Float('')
    cyclic_cb = fields.Boolean('')

    collective = fields.Float('')
    collective_long_arm = fields.Float('')
    collective_lat_arm = fields.Float('')
    collective_long_moment = fields.Float('')
    collective_lat_moment = fields.Float('')
    collective_cb = fields.Boolean('')

    pedals = fields.Float('')
    pedals_long_arm = fields.Float('')
    pedals_lat_arm = fields.Float('')
    pedals_long_moment = fields.Float('')
    pedals_lat_moment = fields.Float('')
    pedals_cb = fields.Boolean('')

    items_on_mount_bar_right = fields.Float('')
    items_on_mount_bar_right_long_arm = fields.Float('')
    items_on_mount_bar_right_lat_arm = fields.Float('')
    items_on_mount_bar_right_long_moment = fields.Float('')
    items_on_mount_bar_right_lat_moment = fields.Float('')
    items_on_mount_bar_right_cb = fields.Boolean('')

    items_on_mount_bar_left = fields.Float('')
    items_on_mount_bar_left_long_arm = fields.Float('')
    items_on_mount_bar_left_lat_arm = fields.Float('')
    items_on_mount_bar_left_long_moment = fields.Float('')
    items_on_mount_bar_left_lat_moment = fields.Float('')
    items_on_mount_bar_left_cb = fields.Boolean('')

    cineflex = fields.Float('')
    cineflex_long_arm = fields.Float('')
    cineflex_lat_arm = fields.Float('')
    cineflex_long_moment = fields.Float('')
    cineflex_lat_moment = fields.Float('')
    cineflex_cb = fields.Boolean('')

    tyler = fields.Float('')
    tyler_long_arm = fields.Float('')
    tyler_lat_arm = fields.Float('')
    tyler_long_moment = fields.Float('')
    tyler_lat_moment = fields.Float('')
    tyler_cb = fields.Boolean('')

    gss = fields.Float('')
    gss_long_arm = fields.Float('')
    gss_lat_arm = fields.Float('')
    gss_long_moment = fields.Float('')
    gss_lat_moment = fields.Float('')
    gss_cb = fields.Boolean('')

    af120_camera_mount = fields.Float('')
    af120_camera_mount_long_arm = fields.Float('')
    af120_camera_mount_lat_arm = fields.Float('')
    af120_camera_mount_long_moment = fields.Float('')
    af120_camera_mount_lat_moment = fields.Float('')
    af120_camera_mount_cb = fields.Boolean('')

    gancho_carga = fields.Float('')
    gancho_carga_long_arm = fields.Float('')
    gancho_carga_lat_arm = fields.Float('')
    gancho_carga_long_moment = fields.Float('')
    gancho_carga_lat_moment = fields.Float('')
    gancho_carga_cb = fields.Boolean('')

    carga_externa = fields.Float('')
    carga_externa_long_arm = fields.Float('')
    carga_externa_lat_arm = fields.Float('')
    carga_externa_long_moment = fields.Float('')
    carga_externa_lat_moment = fields.Float('')
    carga_externa_cb = fields.Boolean('')

    espejo = fields.Float('')
    espejo_long_arm = fields.Float('')
    espejo_lat_arm = fields.Float('')
    espejo_long_moment = fields.Float('')
    espejo_lat_moment = fields.Float('')
    espejo_cb = fields.Boolean('')

    dualcontrols = fields.Float('')
    dualcontrols_long_arm = fields.Float('')
    dualcontrols_lat_arm = fields.Float('')
    dualcontrols_long_moment = fields.Float('')
    dualcontrols_lat_moment = fields.Float('')
    dualcontrols_cb = fields.Boolean('')

    frs = fields.Float('')
    frs_long_arm = fields.Float('')
    frs_lat_arm = fields.Float('')
    frs_long_moment = fields.Float('')
    frs_lat_moment = fields.Float('')

    fls = fields.Float('')
    fls_long_arm = fields.Float('')
    fls_lat_arm = fields.Float('')
    fls_long_moment = fields.Float('')
    fls_lat_moment = fields.Float('')

    aftrp = fields.Float('')
    aftrp_long_arm = fields.Float('')
    aftrp_lat_arm = fields.Float('')
    aftrp_long_moment = fields.Float('')
    aftrp_lat_moment = fields.Float('')

    aftlp = fields.Float('')
    aftlp_long_arm = fields.Float('')
    aftlp_lat_arm = fields.Float('')
    aftlp_long_moment = fields.Float('')
    aftlp_lat_moment = fields.Float('')

    aftcp = fields.Float('')
    aftcp_long_arm = fields.Float('')
    aftcp_lat_arm = fields.Float('')
    aftcp_long_moment = fields.Float('')
    aftcp_lat_moment = fields.Float('')

    bufrs = fields.Float('')
    bufrs_long_arm = fields.Float('')
    bufrs_lat_arm = fields.Float('')
    bufrs_long_moment = fields.Float('')
    bufrs_lat_moment = fields.Float('')

    bufls = fields.Float('r')
    bufls_long_arm = fields.Float('')
    bufls_lat_arm = fields.Float('')
    bufls_long_moment = fields.Float('')
    bufls_lat_moment = fields.Float('')

    buaftrs = fields.Float('')
    buaftrs_long_arm = fields.Float('')
    buaftrs_lat_arm = fields.Float('')
    buaftrs_long_moment = fields.Float('')
    buaftrs_lat_moment = fields.Float('')

    buaftls = fields.Float('')
    buaftls_long_arm = fields.Float('')
    buaftls_lat_arm = fields.Float('')
    buaftls_long_moment = fields.Float('')
    buaftls_lat_moment = fields.Float('')

    misc1 = fields.Float('')
    misc1_long_arm = fields.Float('')
    misc1_lat_arm = fields.Float('')
    misc1_long_moment = fields.Float('')
    misc1_lat_moment = fields.Float('')

    misc2 = fields.Float('')
    misc2_long_arm = fields.Float('')
    misc2_lat_arm = fields.Float('')
    misc2_long_moment = fields.Float('')
    misc2_lat_moment = fields.Float('')

    fueltakeoff = fields.Float('')
    fueltakeoff_long_arm = fields.Float('')
    fueltakeoff_lat_arm = fields.Float('')
    fueltakeoff_long_moment = fields.Float('')
    fueltakeoff_lat_moment = fields.Float('')

    takeoff_gw = fields.Float('')
    takeoff_gw_long_arm = fields.Float('')
    takeoff_gw_lat_arm = fields.Float('')
    takeoff_gw_long_moment = fields.Float('')
    takeoff_gw_lat_moment = fields.Float('')

    fuellanding = fields.Float('')
    fuellanding_long_arm = fields.Float('')
    fuellanding_lat_arm = fields.Float('')
    fuellanding_long_moment = fields.Float('')
    fuellanding_lat_moment = fields.Float('')

    landing_gw = fields.Float('')
    landing_gw_long_arm = fields.Float('')
    landing_gw_lat_arm = fields.Float('')
    landing_gw_long_moment = fields.Float('')
    landing_gw_lat_moment = fields.Float('')

    maswithoutfuel = fields.Float('')
    maswithoutfuel_long_arm = fields.Float('')
    maswithoutfuel_lat_arm = fields.Float('')
    maswithoutfuel_long_moment = fields.Float('')
    maswithoutfuel_lat_moment = fields.Float('')

    canvas_long = fields.Binary('Canvas Long', attachment=False)
    canvas_lat = fields.Binary('Canvas Lat', attachment=False)
    

    # def updatepesos(self, cr, uid, context=None):
    #     import threading
    #     from openerp import pooler
    #     db_name = cr.dbname
    #     local_cr = pooler.get_db(db_name).cursor()
    #     _logger.exception('-- thr -> INIT w&b pesos')
    #     thread = threading.Thread(target=self.updatepesosAsync,
    #                               name='updatepesosAsync',
    #                               args=(local_cr, uid),
    #                               kwargs={'context': context.copy()})
    #     _logger.exception('-- thr -> START w&b pesos')
    #     thread.start()


    # def updatepesosAsync(self, cr, uid, context=None):
    #     import sys
    #     import traceback
    #     import psycopg2
    #     try:
    #         ids = self.search(cr, uid, [])
    #         for item in self.read(cr, uid, ids,['vuelo_id','id']):
    #             _logger.exception('-- thr -> w&b pesos item = %r',item)
    #             vuelo = self.pool['leulit.vuelo'].browse(cr, uid, item['vuelo_id'][0])
    #             _logger.exception('-- thr -> w&b pesos vuelo = %r', vuelo)
    #             _logger.exception('-- thr -> w&b pesos vuelo.fuelsalida = %r', vuelo.fuelsalida)
    #             _logger.exception('-- thr -> w&b pesos vuelo.helicoptero_id.tipo = %r', vuelo.helicoptero_id.tipo)
    #             _logger.exception('-- thr -> w&b pesos vuelo.combustiblelanding = %r', vuelo.combustiblelanding)
    #             self.write(cr, uid, item['id'], {
    #                 'fueltakeoff'   : utilitylib.convert_litros_to_kg(vuelo.fuelsalida, vuelo.helicoptero_id.tipo),
    #                 'fuellanding'   : utilitylib.convert_litros_to_kg(vuelo.combustiblelanding, vuelo.helicoptero_id.tipo)
    #             })
    #         return True
    #     except Exception as exc:
    #         cr.rollback()
    #         ex_type, sys_exc, tb = sys.exc_info()
    #         tb_msg = ''.join(traceback.format_tb(tb, 30))
    #         msg = _("Unexpected exception.\n %s \n %s" % (repr(exc), tb_msg))
    #         _logger.exception('-- thr -> updatepesosAsync --> err 2 -> %r',msg)
    #     finally:
    #         try:
    #             cr.commit()
    #         except psycopg2.Error:
    #             _logger.exception('-- thr -> updatepesosAsync --> err 3 -> Can not do final commit')
    #         cr.close()

