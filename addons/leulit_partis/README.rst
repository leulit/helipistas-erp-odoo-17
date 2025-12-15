===============================
Leulit Riesgo MAGERIT PILAR
===============================

Extiende los módulos de la OCA ``mgmtsystem_asset`` y ``mgmtsystem_risk`` para incorporar
automatizaciones alineadas con el marco PART-IS (SGSI), apoyándose en las metodologías
MAGERIT y PILAR para el cálculo interno. Sirve como base para mantener la
documentación del SGSI y los manuales requeridos por la normativa AESA/EASA PART-IS.

Características
===============

* Valoración C-I-D de activos con cálculo automático de criticidad PART-IS (basado en MAGERIT).
* Seguimiento del ciclo de mejora continua PART-IS (SGSI) con fechas de revisión calculadas.
* Catálogos reutilizables para amenazas, vulnerabilidades y controles PART-IS (SGSI).
* Matriz de probabilidad e impacto intrínseco para cuantificar riesgos (1-25) con umbrales configurables.
* Registro estructurado de estrategias de tratamiento PART-IS y cálculo del riesgo residual.
* Reportabilidad del SGSI alineada con IS.D.OR.205 e IS.D.OR.210.
* Integración con ``mgmtsystem.document`` para manuales y evidencias PART-IS.

Instalación
===========

1. Instale los módulos OCA ``mgmtsystem_asset`` y ``mgmtsystem_risk``.
2. Añada este módulo al ``odoo.conf`` dentro de ``addons_path``.
3. Reinicie Odoo y actualice la lista de aplicaciones.

Uso
===

**1. Identificación y valoración de activos (IS.D.OR.205)**

- Actualice cada activo con sus valores C-I-D siguiendo la escala PART-IS (basada en MAGERIT).
- Revise el campo "Índice PART-IS (SGSI)" y la criticidad calculada para priorizar el análisis.
- Ajuste la parametrización de umbrales desde Ajustes > PART-IS (SGSI).

**2. Catálogos corporativos**

- Mantenga amenazas, vulnerabilidades y controles en el menú PART-IS (SGSI).
- Relacione cada vulnerabilidad con los activos afectados para guiar los análisis.
- Asigne probabilidades por defecto a las amenazas según el criterio corporativo.

**3. Análisis de riesgos MAGERIT (IS.D.OR.205)**

- Cree o edite riesgos seleccionando el activo primario; el impacto se ajusta automáticamente
  en función del nivel PART-IS (SGSI) del activo.
- Seleccione amenaza y vulnerabilidad para dejar trazabilidad respecto al catálogo PART-IS (SGSI) y facilitar auditorías.
- Ajuste la probabilidad intrínseca y revise la severidad resultante (1-25) para priorizar tratamientos.

**4. Tratamiento PART-IS (IS.D.OR.210)**

- Defina la estrategia (reducir, evitar, aceptar, transferir) y vincule controles desde el catálogo PART-IS (SGSI).
- El resumen de controles se genera automáticamente, documentando el plan de actuación.
- Ajuste probabilidad e impacto residuales y verifique el nivel residual obtenido.

**5. Seguimiento y mejora continua**

- Consulte la próxima revisión PART-IS (SGSI) calculada en el activo y programe tareas de seguimiento.
- Use los controles vinculados como base para crear CAPAs u otras acciones en módulos mgmtsystem.
- Genere reportes desde las vistas lista para evidenciar cumplimiento ante AESA/EASA.
- Documente decisiones y evidencias adicionales en la bitácora del SGSI (p.ej. `mgmtsystem.nonconformity`).

Documentación SGSI y Manuales PART-IS
====================================

- Utilice el módulo OCA ``mgmtsystem.document`` (o equivalente) para registrar el Manual SGSI, políticas y
  procedimientos. Referencie los riesgos, controles y activos mediante campos many2many para asegurar la trazabilidad.
- Cada revisión del manual puede vincularse a una acción de mejora o no conformidad, dejando constancia del análisis y
  la aprobación. El campo "Próxima Revisión PART-IS (SGSI)" ayuda a planificar fechas de actualización.
- Para generar la documentación exigida por AESA/EASA PART-IS:

  * Exporte las vistas lista de activos, riesgos y planes de tratamiento con filtros por compañía/alcance.
  * Adjunte los informes resultantes al registro documental (p.ej. como adjuntos en ``mgmtsystem.document``).
  * Incluya el resumen de controles residuales en el manual para evidenciar los requisitos de IS.D.OR.210.

- Cree plantillas de informes (QWeb, BI o herramientas externas) aprovechando los modelos del módulo para emitir
  versiones firmadas del Manual SGSI y de los anexos de análisis de riesgos.
- Acceda al menú **Documentación SGSI** (añadido por este módulo) para gestionar documentos con la vista filtrada a
  manuales PART-IS y crear nuevos registros con los campos precargados.

Plantilla sugerida de Manual SGSI
---------------------------------

.. code-block:: rst

  ==============================
  Manual del Sistema de Gestión
  ==============================

  1. Alcance y contexto
    - Alcance organizativo y normativo (PART-IS, ENS, ISO, etc.).
    - Catálogo de activos críticos (referencia a ``mgmtsystem.asset``).

  2. Análisis de riesgos (IS.D.OR.205)
    - Metodología empleada (PART-IS soportado por matrices MAGERIT configuradas).
    - Resumen de riesgos intrínsecos por activo (extraído de ``mgmtsystem.risk``).

  3. Tratamiento (IS.D.OR.210)
    - Estrategias PART-IS (SGSI) por riesgo.
    - Controles implementados y responsables.

  4. Plan de mejora continua
    - Próximas revisiones PART-IS (SGSI) y responsables.
    - CAPAs/No conformidades abiertas (referencia a ``mgmtsystem.nonconformity``).

  5. Anexos
    - Listado de amenazas/vulnerabilidades corporativas.
    - Evidencias adjuntas.

Flujos operativos recomendados
------------------------------

**F1. Alta y revisión de activos**

1. Responsable de SGSI crea/actualiza el activo en ``mgmtsystem.asset``.
2. Define C-I-D, guarda y revisa el índice PART-IS (SGSI) calculado.
3. Programa la próxima revisión según criticidad (campo PART-IS (SGSI)).

**F2. Mantenimiento de catálogos**

1. Comité de seguridad revisa amenazas, vulnerabilidades y controles desde el menú SGSI.
2. Para cada vulnerabilidad se asignan activos afectados.
3. Se publica un acta vinculada (p.ej. documento o no conformidad) con los cambios aprobados.

**F3. Análisis de riesgo periódicos**

1. Analista duplica riesgos anteriores o crea nuevos desde ``mgmtsystem.risk``.
2. Selecciona activo → impacto se ajusta automáticamente; amenaza/vulnerabilidad se elige del catálogo PART-IS (SGSI).
3. Establece probabilidad intrínseca, guarda y obtiene riesgo intrínseco.
4. Si el nivel supera el umbral aceptable, pasa a F4.

**F4. Tratamiento y seguimiento**

1. Se decide estrategia PART-IS (SGSI) y se vinculan controles.
2. El analista documenta tareas en proyectos/CAPAs y ajusta probabilidad/impacto residuales.
3. Se genera un informe y se adjunta al manual o al registro documental.
4. Se programa seguimiento basado en ``pilar_next_review_date``.

**F5. Revisión y actualización del manual SGSI**

1. Responsable documenta la revisión en ``mgmtsystem.document`` enlazando riesgos y controles vigentes.
2. Adjunta exportes de listas (PDF/Excel) como evidencias.
3. Somete el manual a aprobación a través del workflow de mgmtsystem.
4. Registra en ``mgmtsystem.nonconformity`` cualquier desviación detectada y asigna acciones.

Estos flujos pueden adaptarse añadiendo automatizaciones (por ejemplo, recordatorios vía servidor de acciones) o
integraciones con módulos de ticketing según las necesidades de la organización.
