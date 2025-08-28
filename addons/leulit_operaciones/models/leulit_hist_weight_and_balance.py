# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_hist_weight_and_balance(models.Model):
    _name           = "leulit.hist_weight_and_balance"
    _description    = "leulit_hist_weight_and_balance"


    def unlink(self):
        raise UserError("No se puede eliminar.")

    # def write(self, vals):
    #     raise ValidationError("¡¡ALERTA!! Si hay vuelos con estos datos de carga y centrado no se pueden cambiar.")


    def _get_tipos(self):
        return utilitylib.leulit_get_tipos_helicopteros()


    helicoptero_tipo = fields.Selection(selection=_get_tipos,string="Tipo", required=True)
    helicoptero_matricula = fields.Char(string="Matricula")
    is_carga = fields.Boolean(string="¿Esta carga y centrado contiene gancho?")
    fecha = fields.Date(string="Fecha")

    frs_mass = fields.Float(string="")
    frs_long = fields.Float(string="")
    frs_lat = fields.Float(string="")

    fls_mass = fields.Float(string="")
    fls_long = fields.Float(string="")
    fls_lat = fields.Float(string="")

    aftrp_mass = fields.Float(string="")
    aftrp_long = fields.Float(string="")
    aftrp_lat = fields.Float(string="")

    aftlp_mass = fields.Float(string="")
    aftlp_long = fields.Float(string="")
    aftlp_lat = fields.Float(string="")

    aftcp_mass = fields.Float(string="")
    aftcp_long = fields.Float(string="")
    aftcp_lat = fields.Float(string="")
    
    bufrs_mass = fields.Float(string="")
    bufrs_long = fields.Float(string="")
    bufrs_lat = fields.Float(string="")
    
    bufls_mass = fields.Float(string="")
    bufls_long = fields.Float(string="")
    bufls_lat = fields.Float(string="")
    
    buaftrs_mass = fields.Float(string="")
    buaftrs_long = fields.Float(string="")
    buaftrs_lat = fields.Float(string="")
    
    buaftls_mass = fields.Float(string="")
    buaftls_long = fields.Float(string="")
    buaftls_lat = fields.Float(string="")
    
    baggage_noseats_mass = fields.Float(string="")
    baggage_noseats_long = fields.Float(string="")
    baggage_noseats_lat = fields.Float(string="")
    
    baggage_zonac_mass = fields.Float(string="")
    baggage_zonac_long = fields.Float(string="")
    baggage_zonac_lat = fields.Float(string="")
    
    baggage_zonad_mass = fields.Float(string="")
    baggage_zonad_long = fields.Float(string="")
    baggage_zonad_lat = fields.Float(string="")
    
    main_baggage_mass = fields.Float(string="")
    main_baggage_long = fields.Float(string="")
    main_baggage_lat = fields.Float(string="")
    
    front_baggage_mass = fields.Float(string="")
    front_baggage_long = fields.Float(string="")
    front_baggage_lat = fields.Float(string="")
    
    forward_right_door_mass = fields.Float(string="")
    forward_right_door_long = fields.Float(string="")
    forward_right_door_lat = fields.Float(string="")
    
    forward_left_door_mass = fields.Float(string="")
    forward_left_door_long = fields.Float(string="")
    forward_left_door_lat = fields.Float(string="")
    
    aft_right_door_mass = fields.Float(string="")
    aft_right_door_long = fields.Float(string="")
    aft_right_door_lat = fields.Float(string="")
    
    aft_left_door_mass = fields.Float(string="")
    aft_left_door_long = fields.Float(string="")
    aft_left_door_lat = fields.Float(string="")
    
    sliding_door_mass = fields.Float(string="")
    sliding_door_long = fields.Float(string="")
    sliding_door_lat = fields.Float(string="")
    
    rear_cargo_door_mass = fields.Float(string="")
    rear_cargo_door_long = fields.Float(string="")
    rear_cargo_door_lat = fields.Float(string="")
    
    cyclic_mass = fields.Float(string="")
    cyclic_long = fields.Float(string="")
    cyclic_lat = fields.Float(string="")
    
    collective_mass = fields.Float(string="")
    collective_long = fields.Float(string="")
    collective_lat = fields.Float(string="")
    
    pedals_mass = fields.Float(string="")
    pedals_long = fields.Float(string="")
    pedals_lat = fields.Float(string="")

    items_on_mount_bar_right_mass = fields.Float(string="")
    items_on_mount_bar_right_long = fields.Float(string="")
    items_on_mount_bar_right_lat = fields.Float(string="")

    items_on_mount_bar_left_mass = fields.Float(string="")
    items_on_mount_bar_left_long = fields.Float(string="")
    items_on_mount_bar_left_lat = fields.Float(string="")
    
    cineflex_mass = fields.Float(string="")
    cineflex_long = fields.Float(string="")
    cineflex_lat = fields.Float(string="")
    
    tyler_mass = fields.Float(string="")
    tyler_long = fields.Float(string="")
    tyler_lat = fields.Float(string="")
    
    gss_mass = fields.Float(string="")
    gss_long = fields.Float(string="")
    gss_lat = fields.Float(string="")
    
    af120_camera_mount_mass = fields.Float(string="")
    af120_camera_mount_long = fields.Float(string="")
    af120_camera_mount_lat = fields.Float(string="")

    gancho_carga_mass = fields.Float(string="")
    gancho_carga_long = fields.Float(string="")
    gancho_carga_lat = fields.Float(string="")

    carga_externa_mass = fields.Float('')
    carga_externa_long = fields.Float('')
    carga_externa_lat = fields.Float('')

    espejo_mass = fields.Float('')
    espejo_long = fields.Float('')
    espejo_lat = fields.Float('')
    
    frontseat_mass = fields.Float(string="")
    frontseat_long = fields.Float(string="")
    frontseat_lat = fields.Float(string="")
    
    rearseat_mass = fields.Float(string="")
    rearseat_long = fields.Float(string="")
    rearseat_lat = fields.Float(string="")
    
    dualcontrols_mass = fields.Float(string="")
    dualcontrols_long = fields.Float(string="")
    dualcontrols_lat = fields.Float(string="")
    
    misc1_mass = fields.Float(string="")
    misc1_long = fields.Float(string="")
    misc1_lat = fields.Float(string="")
    
    misc2_mass = fields.Float(string="")
    misc2_long = fields.Float(string="")
    misc2_lat = fields.Float(string="")
    
    fueltakeoff_mass = fields.Float(string="")
    fueltakeoff_long = fields.Float(string="")
    fueltakeoff_lat = fields.Float(string="")
    
    takeoff_gw_mass = fields.Float(string="")
    takeoff_gw_long = fields.Float(string="")
    takeoff_gw_lat = fields.Float(string="")
    
    fuellanding_mass = fields.Float(string="")
    fuellanding_long = fields.Float(string="")
    fuellanding_lat = fields.Float(string="")
    
    landing_gw_mass = fields.Float(string="")
    landing_gw_long = fields.Float(string="")
    landing_gw_lat = fields.Float(string="")
    
    maswithoutfuel_mass = fields.Float(string="")
    maswithoutfuel_long = fields.Float(string="")
    maswithoutfuel_lat = fields.Float(string="")

