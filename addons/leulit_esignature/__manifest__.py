{
    "name": "Leulit e-signature",
    "summary": "LEULIT MIGRACIÓN",
    "description": "\n    ",
    "author": "Leulit S.L.",
    "website": "http://www.leulit.com",
    "category": "leulit",
    "version": "17.0.1.0.0",
    "depends": [
        "leulit",
        "leulit_operaciones",
        "leulit_escuela",
        "leulit_seguridad",
        "leulit_taller"
    ],
    "data": [
        "groups.xml",
        "security.xml",
        "res_users.xml",
        "views.xml",
        "anomalia.xml",
        "vuelo.xml",
        "escuela/alumno_reports.xml",
        "views/leulit_maintenance_boroscopia.xml",
        "views/leulit_maintenance_crs.xml",
        "views/leulit_maintenance_form_one.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "leulit_esignature/static/src/js/csv_code.js",
            "leulit_esignature/static/src/js/leulit_esignature.js",
        ],
    },
    "demo": [],
    "css": [],
    "installable": True,
    "auto_install": False,
    "application": True,
    "license": "LGPL-3"
}
