{
    "name": "Parte piloto privado",
    "summary": "Transcripción del PTV en papel de pilotos privados: crea, firma y cierra el vuelo en nombre del piloto",
    "author": "Leulit S.L.",
    "website": "http://www.leulit.com",
    "category": "leulit",
    "version": "17.0.1.0.0",
    "depends": [
        "leulit",
        "leulit_operaciones",
        "leulit_esignature"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/leulit_piloto_view.xml",
        "wizard/parte_privado_wizard_view.xml",
        "menu.xml"
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "LGPL-3"
}
