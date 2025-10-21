# -*- coding: utf-8 -*-
{
    "name": "Leulit Hide Menus",
    "summary": "Leulit - Hide specific menus for certain user groups",
    "description": "\n    ",
    "author": "Leulit S.L.",
    "website": "http://www.leulit.com",
    "category": "leulit",
    "version": "17.0.1.0.0",
    'depends': [
        'mail',
        'calendar',
        'project',
        'leulit',  # <-- DEPENDENCIA AÑADIDA. Reemplaza 'leulit' si el módulo tiene otro nombre.
    ],
    'data': [
        'views/hide_menus.xml',
    ],
    "demo": [],
    "css": [],
    "installable": True,
    "auto_install": False,
    "application": True,
    "license": "LGPL-3"
}