{
    "name": "NDA",
    "summary": "LEULIT NDA",
    "description": "\n    Bloquea el acceso al backend hasta que el usuario firme el acuerdo de confidencialidad (NDA).\n    ",
    "author": "Leulit S.L.",
    "website": "http://www.leulit.com",
    "category": "leulit",
    "version": "17.0.1.0.0",
    "depends": [
        "leulit",
        "mail",
        "web",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_template_data.xml",
        "data/leulit_nda_acuerdo_data.xml",
        "views/leulit_nda_acuerdo_views.xml",
        "views/templates.xml",
        "report/leulit_nda_report.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "leulit_nda/static/src/css/nda_acuerdo.css",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "LGPL-3",
}
