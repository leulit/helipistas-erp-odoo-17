# -*- encoding: utf-8 -*-
"""
Los cursos de perfil de formación pasan a colgar de la plantilla de curso
(leulit.curso_template) en vez de una revisión concreta (leulit.curso).

- Revisiones usadas en perfiles sin plantilla: se les crea una plantilla con su
  mismo nombre y flags, y se cuelgan de ella.
- curso_template_id = plantilla de la revisión a la que apuntaba cada curso de PF.

Idempotente: solo toca registros sin plantilla.
"""
import logging

_logger = logging.getLogger(__name__)

FLAGS = ['ato_mo', 'ato_mi', 'nco', 'aoc', 'ttaa', 'lci', 'camo', 'p_145']


def migrate(cr, version):
    cols = ', '.join('c.' + f for f in FLAGS)
    cr.execute("""
        SELECT DISTINCT c.id, c.name, {cols}
          FROM leulit_perfil_formacion_curso pfc
          JOIN leulit_curso c ON c.id = pfc.curso
         WHERE c.template_id IS NULL
    """.format(cols=cols))
    huerfanos = cr.fetchall()
    for row in huerfanos:
        curso_id, name, flags = row[0], row[1], row[2:]
        cr.execute("""
            INSERT INTO leulit_curso_template (name, {flags}, create_uid, write_uid, create_date, write_date)
            VALUES (%s, {ph}, 1, 1, now() at time zone 'UTC', now() at time zone 'UTC')
            RETURNING id
        """.format(flags=', '.join(FLAGS), ph=', '.join(['%s'] * len(FLAGS))), [name] + [bool(f) for f in flags])
        template_id = cr.fetchone()[0]
        cr.execute("UPDATE leulit_curso SET template_id = %s WHERE id = %s", (template_id, curso_id))
        _logger.info("leulit_escuela migración: creada plantilla %s para el curso %s (%s)", template_id, curso_id, name)

    cr.execute("""
        UPDATE leulit_perfil_formacion_curso pfc
           SET curso_template_id = c.template_id
          FROM leulit_curso c
         WHERE c.id = pfc.curso
           AND pfc.curso_template_id IS NULL
    """)
    _logger.info("leulit_escuela migración: %s cursos de perfil de formación enlazados a su plantilla (%s plantillas nuevas)",
                 cr.rowcount, len(huerfanos))

    cr.execute("SELECT count(*) FROM leulit_perfil_formacion_curso WHERE curso_template_id IS NULL")
    sin_plantilla = cr.fetchone()[0]
    if sin_plantilla:
        _logger.warning("leulit_escuela migración: %s cursos de perfil de formación sin curso asociado (ni antes ni ahora)", sin_plantilla)
