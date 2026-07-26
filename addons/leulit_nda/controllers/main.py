# -*- encoding: utf-8 -*-
import logging

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.addons.web.controllers.home import Home

_logger = logging.getLogger(__name__)


class NdaHome(Home):

    @http.route()
    def web_client(self, s_action=None, **kw):
        response = super().web_client(s_action=s_action, **kw)
        if response.status_code == 200 and request.env.user._nda_debe_firmar():
            return request.redirect("/nda/acuerdo")
        return response


class NdaController(http.Controller):

    @http.route("/nda/acuerdo", type="http", auth="user", website=True)
    def nda_acuerdo(self, **kw):
        user = request.env.user
        if not user._nda_debe_firmar():
            return request.redirect("/web")
        acuerdo = request.env["leulit.nda.acuerdo"].sudo().get_current()
        return request.render("leulit_nda.pagina_acuerdo", {
            "acuerdo": acuerdo,
            "user": user,
        })

    @http.route("/nda/enviar_codigo", type="json", auth="user")
    def nda_enviar_codigo(self, **kw):
        try:
            request.env.user.action_nda_enviar_codigo()
            return {"ok": True}
        except UserError as e:
            return {"ok": False, "error": str(e)}
        except Exception:
            _logger.exception("Error enviando el código NDA")
            return {"ok": False, "error": "No se ha podido enviar el código. Inténtalo de nuevo."}

    @http.route("/nda/verificar_codigo", type="json", auth="user")
    def nda_verificar_codigo(self, codigo=None, **kw):
        try:
            request.env.user.action_nda_verificar_codigo(codigo)
            return {"ok": True}
        except UserError as e:
            return {"ok": False, "error": str(e)}
        except Exception:
            _logger.exception("Error verificando el código NDA")
            return {"ok": False, "error": "No se ha podido verificar el código. Inténtalo de nuevo."}
