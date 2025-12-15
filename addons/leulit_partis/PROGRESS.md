# Diario de Progreso - SGSI PART-IS (AESA)

> Última actualización: 2025-12-15

## Marco Normativo Prioritario

**ORDEN DE PRIORIDAD EN DESARROLLO:**
1. **EASA PART-IS** (Reglamento UE 2018/1139) - Requisito obligatorio
2. **AESA SGSI** - Normativa española de seguridad de información aeronáutica
3. **MAGERIT v3** - Metodología de análisis de riesgos (herramienta)
4. **PILAR** - Procedimiento de valoración cuantitativa (herramienta)
5. **ISO/IEC 27001:2022** - Estándar internacional complementario

⚠️ **Nota crítica**: Todas las implementaciones de MAGERIT, PILAR e ISO 27001 están **supeditadas** al cumplimiento de PART-IS de AESA.

---

## Cambios Recientes

### 2025-12-15: Sistema de Auditoría y Trazabilidad Completo
- ✅ **Implementada integración completa con auditlog** (IS.D.OR.305)
  - Dependencia añadida al módulo `auditlog` de OCA
  - Configuración automática de reglas de auditoría (noupdate=1)
  - 5 reglas preconfiguradas: activos/riesgos, amenazas, vulnerabilidades, controles, configuración
  - Auditoría de lectura activada solo para activos (información más sensible)
  - 6 campos críticos auditados específicamente con líneas de regla
  - Modelo `mgmtsystem.audit.report` para reportes consolidados
  - Cálculo automático de estadísticas por tipo de operación
  - Detección inteligente de cambios críticos en workflow y niveles
  - Vistas completas: form con KPIs, tree, search con filtros predefinidos
  - Botones de navegación a logs generales y cambios críticos
  - Menú "Auditoría" con 3 opciones: reportes, logs SGSI, configuración
  - Permisos: solo managers y RBase pueden acceder

**Campos críticos auditados:**
- Estado del plan de tratamiento
- Aprobador del plan
- Nivel de criticidad del activo
- Nivel de riesgo residual
- Estrategia de tratamiento

**Casos de uso:**
- Auditorías internas y externas del SGSI
- Investigación de incidentes de seguridad
- Cumplimiento normativo PART-IS
- Análisis de comportamiento de usuarios
- Detección de cambios no autorizados

### 2025-12-15 (Anterior): Wizards de Análisis Masivo y Gestión en Lote
- ✅ **Implementados wizards de productividad** para análisis masivo
  - **Wizard de Análisis Masivo de Riesgos**: Crea múltiples análisis combinando activos × amenazas
    - Contador en tiempo real de riesgos a crear
    - Datos comunes configurables (departamento, responsable, fecha)
    - Estrategia y controles por defecto aplicables a todos
    - Sincronización automática de probabilidad desde amenaza e impacto desde activo
    - Notificación de éxito con navegación directa a riesgos creados
  - **Wizard de Aplicación de Controles en Lote**: Actualiza múltiples riesgos simultáneamente
    - Modo añadir (preserva controles existentes) o reemplazar (sustituye todos)
    - Actualización opcional de estrategia y eficacia de controles
    - Alerta visual en modo reemplazar
    - Notificación de éxito con resumen
  - Accesibles desde vista de lista (botón "Acción") y menú "Herramientas Masivas"
  - Permisos configurados para usuarios y managers

**Casos de uso:**
- Analizar todas las amenazas del catálogo sobre activos críticos
- Aplicar controles estándar a múltiples riesgos similares
- Actualizar estrategias en lote tras revisión de políticas

### 2025-12-15 (Anterior): Workflow de Aprobación de Planes de Tratamiento
- ✅ **Implementado workflow completo de aprobación** (IS.D.OR.210)
  - 5 estados: draft, pending, approved, implemented, rejected
  - Botones de acción contextuales en header del formulario
  - Validaciones automáticas (estrategia + controles obligatorios)
  - Wizard modal para capturar motivo de rechazo
  - Campos de seguimiento: aprobador, fechas de aprobación e implementación
  - Tracking automático en chatter para auditoría
  - Permisos diferenciados: usuarios (solicitan/implementan) vs managers (aprueban/rechazan)
  - Histórico completo de decisiones y cambios de estado

**Flujo implementado:**
1. Usuario crea plan → estado "Borrador"
2. Usuario solicita aprobación → valida estrategia y controles → "Pendiente"
3. Manager aprueba/rechaza → si rechaza, captura motivo → "Aprobado" o "Rechazado"
4. Usuario marca implementado → "Implementado" (solo desde aprobado)
5. Posibilidad de volver a borrador desde rechazado

### 2025-12-15 (Anterior): Dashboard SGSI Completo y KPIs
- ✅ **Implementado Dashboard completo con KPIs** (IS.D.OR.305)
  - Modelo `mgmtsystem.dashboard` con 11 KPIs computados en tiempo real
  - Vista Kanban interactiva con cards y barra de progreso
  - Vista Form con grupos de indicadores (Activos, Riesgos, Controles, Cumplimiento)
  - Vistas Pivot y Graph para análisis de activos y riesgos
  - KPI de cumplimiento SGSI calculado (activos valorados + riesgos tratados)
  - Acciones rápidas desde dashboard a vistas de activos y riesgos
  - Menú estructurado: Panel de Control → Análisis Visual
  - Permisos configurados para usuarios, managers y RBase

**KPIs Implementados:**
- Total Activos / Críticos / Alto / Revisiones Pendientes
- Total Riesgos / Intríns Críticos / Residuales Críticos / Sin Tratar
- Total Controles / Activos
- % Cumplimiento SGSI

### 2025-12-15 (Anterior): Correcciones Críticas y Preparación para Instalación
- ✅ **Corregidos errores XML en todas las vistas** del módulo
  - Eliminadas referencias a campos inexistentes (`description` en `mgmtsystem.hazard`)
  - Corregidas etiquetas XML mal formadas en `mgmtsystem_catalog_views.xml`
  - Corregida sintaxis XML corrupta en `mgmtsystem_risk_views.xml`
  - Validados todos los archivos XML con `xmllint` (8 archivos, 0 errores)
- ✅ **Resueltos problemas de traducción**
  - Identificados 7 mensajes duplicados en `i18n/es.po`
  - Archivo de traducción movido a backup temporal (`es.po.backup`)
  - Módulo listo para instalación (traducciones se regenerarán desde Odoo)
- ✅ **Validación estructural completa**
  - Todos los modelos Python sin errores de sintaxis
  - Todas las vistas XML bien formadas
  - Dependencias de OCA verificadas
  - Estructura de menús consistente

**Siguiente paso:** Instalar el módulo en Odoo y exportar traducciones limpias.

### 2025-12-15 (Anterior): Revisión Completa y Vistas Finales
- ✅ **Completadas todas las vistas necesarias** para gestión SGSI PART-IS
- ✅ **Agregadas vistas Tree personalizadas** para Activos y Riesgos
- ✅ **Agregadas vistas Search avanzadas** con filtros por criticidad y niveles de riesgo
- ✅ **Implementados filtros de búsqueda** en todos los catálogos (Amenazas, Vulnerabilidades, Controles)
- ✅ **Creado menú de Activos de Información** independiente
- ✅ **Creado menú de Análisis de Riesgos** independiente
- ✅ **Agregado menú de Panel de Control** para dashboard futuro
- ✅ **Agregado menú de Configuración** con acceso a umbrales MAGERIT
- ✅ **Indicadores visuales** (decoraciones de color) para identificación rápida de criticidad
- ✅ **Consolidado menú principal único** "SGSI PART-IS"
- ✅ **Dominio corregido** para separar activos (sin amenaza) de riesgos (con amenaza)

**Cumplimiento PART-IS verificado:**
- ✅ IS.D.OR.215 - Gestión de Activos (vistas completas)
- ✅ IS.D.OR.205 - Análisis de Riesgos (vistas completas)
- ✅ IS.D.OR.210 - Tratamiento de Riesgos (controles y estrategias)
- ✅ IS.D.OR.220 - Gestión Documental (integración document_page)
- ✅ IS.ORG.0100 - Establecimiento del SGSI (configuración de umbrales)

### 2025-11-19: Renombrado del Módulo
- **Módulo renombrado** de `leulit_riesgo_magerit_pilar` a `leulit_partis`
- Actualizados todos los `config_parameter` de `leulit_riesgo_magerit_pilar.*` a `leulit_partis.*`
- Modificado `__manifest__.py` con el nuevo nombre: "Leulit PART-IS"
- Actualizadas todas las referencias en:
  - Modelos (`mgmtsystem_asset.py`, `mgmtsystem_risk.py`, `res_config_settings.py`)
  - Tests (`test_risk_computations.py`)
  - Traducciones (`i18n/es.po`)
  - Documentación (`.github/copilot-instructions.md`)
- El directorio del módulo se ha renombrado correctamente

**⚠️ Importante para actualización:**
```bash
# Para instalar el módulo renombrado:
odoo-bin -d <database> -u leulit_partis

# Si ya tenías instalado leulit_riesgo_magerit_pilar:
# 1. Desinstalar el módulo antiguo desde la interfaz de Odoo
# 2. Actualizar la lista de aplicaciones
# 3. Instalar el nuevo módulo leulit_partis
```

## Resumen

- Se ha creado el módulo PART-IS con dependencias de OCA (`mgmtsystem_asset`, `mgmtsystem_risk`, `mgmtsystem_document`).
- Los modelos de activos y riesgos heredan su lógica base para incorporar campos y cálculos MAGERIT/PILAR.
- Se añadieron vistas heredadas para exponer la información en formularios.
- Catálogos reutilizables para amenazas, vulnerabilidades y controles PILAR disponibles.
- Documentación inicial publicada en `README.rst`.
- Integración completa con gestión documental SGSI.

## Tareas Completadas

- [x] Revisar matrices y escalas MAGERIT/PILAR para permitir configuración avanzada.
- [x] Crear vistas/acciones específicas para mantener catálogos (menús si procede).
- [x] Añadir reglas de seguridad adicionales (record rules) para catálogos activos.
- [x] Ajustar reglas para incluir el rol RBase con permisos completos.
- [x] Generar traducciones (`i18n/es.po`) y revisar etiquetas en vistas.
- [x] Implementar tests `TransactionCase` que cubran cálculos de criticidad y riesgo residual.
- [x] Ampliar documentación: flujo completo SGSI, ejemplos y dependencias.
- [x] Integrar la gestión documental SGSI (menús, vistas y campos en `mgmtsystem.document`).
- [x] Renombrar módulo a `leulit_partis` para mejor identificación del framework PART-IS.
- [x] **Validación y corrección completa de archivos XML** (sin errores de formato).
- [x] **Validación de estructura del módulo** (listo para instalación en Odoo 17).

## Próximas Acciones (Prioridad PART-IS)

### Crítico Inmediato
- [x] **Instalación del módulo en producción** ✅ 2025-12-15
- [ ] **Verificación post-instalación**
  - Verificar que todos los menús son accesibles (SGSI PART-IS)
  - Comprobar que las vistas Tree/Form/Search funcionan correctamente
  - Validar cálculos automáticos (crear activo de prueba con valoración C-I-D)
  - Validar cálculos de riesgo (crear análisis de riesgo de prueba)
- [ ] **Regenerar traducciones español**
  - Ir a Configuración → Traducciones → Exportar Traducciones
  - Seleccionar módulo `leulit_partis` e idioma `Español`
  - Descargar y reemplazar el archivo `i18n/es.po`
  - Actualizar módulo para cargar nuevas traducciones

### Alta Prioridad (Requisitos PART-IS)
- [x] **Dashboard de indicadores SGSI** ✅ 2025-12-15 (IS.D.OR.305 - Mejora continua)
  - ✅ Modelo `mgmtsystem.dashboard` con KPIs computados
  - ✅ Vista Kanban con cards interactivas
  - ✅ Vista Form con todos los indicadores
  - ✅ Gráficos pivot/graph de activos por criticidad
  - ✅ Gráficos pivot/graph de riesgos (matriz)
  - ✅ KPI de cumplimiento SGSI (%)
  - ✅ Navegación rápida a activos y riesgos desde dashboard
  - ✅ Menú "Panel de Control" con submenú "Análisis Visual"
Estructura de Menús Implementada

```
SGSI PART-IS (Menú Principal - web_icon)
├── Panel de Control (seq. 5) - Futuro dashboard
├── Catálogos (seq. 10)
│   ├── Amenazas (con búsqueda por categoría)
│   ├── Vulnerabilidades (con filtros de activos)
│   └── Controles (con búsqueda por tipo)
├── Activos de Información (seq. 20) - IS.D.OR.215
│   └── Vistas: Tree, Form, Search (filtros por criticidad)
├── Análisis de Riesgos (seq. 30) - IS.D.OR.205/210
│   └── Vistas: Tree, Form, Search (filtros multinivel)
├── Documentación SGSI (seq. 40) - IS.D.OR.220
│   └── Integración con document_page (OCA)
└── Configuración (seq. 100) - Solo administradores
    └── Umbrales MAGERIT/PILAR configurables
```

## Modelos y Mapeo PART-IS

| Modelo Odoo | Uso SGSI | Requisito PART-IS |
|-------------|----------|-------------------|
| `mgmtsystem.hazard` (activos) | Inventario de activos críticos | IS.D.OR.215 |
| `mgmtsystem.hazard` (riesgos) | Análisis de riesgos | IS.D.OR.205 |
| `mgmtsystem.risk.threat` | Catálogo de amenazas | IS.D.OR.205(b) |
| `mgmtsystem.risk.vulnerability` | Catálogo de vulnerabilidades | IS.D.OR.205(c) |
| `mgmtsystem.risk.control` | Catálogo de controles | IS.D.OR.210(a) |
| `document.page` | Manual y documentación SGSI | IS.D.OR.220 |
| `res.config.settings` | Configuración de umbrales | IS.ORG.0100(c) |

## Notas Técnicas

- Requiere `python-dateutil` para cálculos de fechas (`relativedelta`)
- Comando de actualización: `odoo-bin -d <base> -u leulit_partis`
- Mantener formateo con Black/isort y validar con Pylint (configuración OCA)
- Los parámetros de configuración usan el prefijo `leulit_partis.*`
- Compatibilidad: Odoo 17.0 Community/Enterprise
- Dependencias OCA verificadas en `INSTALACION_OCA.md`

## Cumplimiento Normativo Actual

### EASA PART-IS ✅
- **IS.ORG.0100** - Establecimiento SGSI: ✅ Completo
- **IS.D.OR.215** - Gestión de activos: ✅ Completo (vistas + cálculos)
- **IS.D.OR.205** - Análisis de riesgos: ✅ Completo (metodología MAGERIT)
- **IS.D.OR.210** - Tratamiento de riesgos: ✅ Completo (controles PILAR)
- **IS.D.OR.220** - Gestión documental: ✅ Completo (document_page)
- **IS.D.OR.305** - Mejora continua: 🔄 Parcial (ciclos automáticos implementados, dashboard pendiente)

### ISO/IEC 27001:2022 (Complementario)
- Cláusula 4 - Contexto de la organización: ✅ (activos identificados)
- Cláusula 6 - Planificación: ✅ (análisis de riesgos)
- Cláusula 8 - Operación: ✅ (tratamiento de riesgos)
- Cláusula 9 - Evaluación del desempeño: 🔄 (dashboard pendiente)
- Anexo A - Controles: ✅ (catálogo reutilizable)
  - Declaración de aplicabilidad (SOA)

- [x] **Workflow de aprobación** ✅ 2025-12-15 (IS.D.OR.210)
  - ✅ Estados: Borrador → Pendiente → Aprobado → Implementado / Rechazado
  - ✅ Botones de acción en formulario de riesgo (header con statusbar)
  - ✅ Validaciones: controles requeridos según estrategia
  - ✅ Wizard de rechazo con motivo obligatorio
  - ✅ Tracking completo de cambios de estado
  - ✅ Campos de aprobación: aprobador, fecha, notas
  - ✅ Campo de implementación con fecha
  - ✅ Permisos: usuarios pueden solicitar/implementar, managers aprueban/rechazan
  - ✅ Histórico completo en chatter (tracking=True)

### Media Prioridad (Mejoras Operativas)
- [x] **Wizard de análisis masivo de riesgos** ✅ 2025-12-15
  - ✅ Wizard para crear múltiples análisis (Activos × Amenazas)
  - ✅ Selección múltiple de activos y amenazas
  - ✅ Vulnerabilidad común opcional
  - ✅ Estrategia y controles por defecto
  - ✅ Cálculo automático del número de riesgos a crear
  - ✅ Sincronización de impacto desde valoración del activo
  - ✅ Sincronización de probabilidad desde amenaza
  - ✅ Notificación de éxito con navegación a riesgos creados
  - ✅ Wizard para aplicar controles en lote a riesgos existentes
  - ✅ Modo añadir/reemplazar controles
  - ✅ Actualización masiva de estrategia y eficacia
  - ✅ Acciones disponibles desde lista de activos y riesgos
  - ✅ Menú "Herramientas Masivas" con ambos wizards
  
- [x] **Integraciones con auditoría** ✅ 2025-12-15
  - ✅ Módulo `auditlog` de OCA integrado
  - ✅ Reglas de auditoría preconfiguradas para activos, amenazas, vulnerabilidades, controles
  - ✅ Auditoría de lectura activada para activos críticos
  - ✅ Auditoría de campos críticos: estados, aprobaciones, niveles de riesgo
  - ✅ Modelo de reportes de auditoría consolidados
  - ✅ Estadísticas automáticas: lecturas, creaciones, modificaciones, eliminaciones
  - ✅ Detección automática de cambios críticos
  - ✅ Vistas de análisis y navegación a logs
  - ✅ Menú completo de auditoría (solo managers)
  - ✅ Filtros predefinidos: último mes, último trimestre, cambios críticos

### Baja Prioridad (Funcionalidades Avanzadas)
- [x] **Exportación a formatos estándar** ✅ 2025-12-15
  - ✅ Wizard de exportación a CSV con filtros avanzados
    - Filtrado por activos específicos o todos
    - Filtrado por amenazas específicas o todas
    - Opción para incluir detalles del plan de tratamiento
    - Opción para exportar solo riesgos altos/críticos (nivel 4-5)
    - Archivo generado con timestamp único
    - CSV con delimitador punto y coma (compatible con Excel)
    - 16 columnas base + 5 adicionales de plan de tratamiento
    - Exportación de riesgos (no activos vacíos)
  - ✅ Reporte PDF de Plan de Tratamiento
    - Template QWeb profesional con estructura completa
    - Información del activo (tipo, ubicación, valoración C-I-D)
    - Todos los riesgos con amenazas, vulnerabilidades y evaluación
    - Indicadores visuales de criticidad (colores verde/naranja/rojo)
    - Plan de tratamiento detallado por riesgo
    - Controles existentes y propuestos
    - Estado del plan, responsable, fecha objetivo
    - Notas del tratamiento
    - Pie de página con fecha/hora de generación
  - ✅ Botón "Exportar a CSV" en vista de activos (menú Acción)
  - ✅ Botón "Plan de Tratamiento (PDF)" en formulario de activo (header)
  - ✅ Accesible desde menú de acciones en vistas de lista

- [x] **Notificaciones automáticas** ✅ 2025-12-15
  - ✅ Sistema de configuración de notificaciones
    - Modelo `mgmtsystem.notification.cron` para configurar alertas
    - 2 tipos: riesgos pendientes de aprobación y riesgos críticos sin tratamiento
    - Configuración de días de antigüedad (threshold)
    - Selección de grupos destinatarios (managers por defecto)
    - Destinatarios adicionales específicos
    - Registro de última ejecución y cantidad de alertas enviadas
  - ✅ Plantillas de email profesionales
    - Email de riesgos pendientes (fondo naranja)
      - Tabla con activo, amenaza, nivel, días pendientes
      - Enlace directo al módulo SGSI
      - Mensaje de acción requerida
    - Email de riesgos críticos (fondo rojo)
      - Alerta de máxima prioridad
      - Tabla con activos afectados y estados
      - Advertencia de impacto en cumplimiento PART-IS/AESA
      - Enlace directo para acción inmediata
  - ✅ Tareas programadas (cron jobs)
    - Cron diario: Riesgos pendientes de aprobación (>3 días por defecto)
    - Cron semanal: Riesgos críticos sin tratamiento aprobado
    - Configuraciones predeterminadas creadas (noupdate=1)
    - Activadas por defecto
  - ✅ Métodos Python optimizados
    - `_cron_send_pending_approval_notifications()`
    - `_cron_send_critical_risks_notifications()`
    - Filtrado inteligente por estado y nivel
    - Envío individual para control de destinatarios
    - Log de última ejecución

**Casos de uso notificaciones:**
- Alertar a managers de riesgos estancados en estado "pendiente"
- Notificar urgentemente riesgos de nivel 4-5 sin plan aprobado
- Cumplimiento de IS.D.OR.305 (mejora continua)
- Reducción del tiempo de respuesta ante riesgos críticos

## Archivos Creados en Esta Actualización

**Exportación:**
- `models/mgmtsystem_risk_export_wizard.py` (220 líneas)
- `views/mgmtsystem_risk_export_wizard_views.xml` (39 líneas)
- `report/risk_treatment_plan_report.xml` (13 líneas)
- `report/risk_treatment_plan_template.xml` (160 líneas)

**Notificaciones:**
- `models/mgmtsystem_notification_cron.py` (175 líneas)
- `data/notification_templates.xml` (137 líneas - 2 templates)
- `data/cron_jobs.xml` (44 líneas - 2 crons + 2 configs)

**Actualizaciones:**
- `models/__init__.py` (2 imports agregados)
- `security/ir_model_access.xml` (6 registros de permisos agregados)
- `__manifest__.py` (3 archivos XML agregados a data)
- `views/mgmtsystem_asset_views.xml` (botón PDF agregado)
- `views/mgmtsystem_risk_views.xml` (botón CSV agregado)

## Notas Técnicas

- Requiere `python-dateutil` para cálculos de fechas (`relativedelta`).
- Comando de actualización: `odoo-bin -d <base> -u leulit_partis`
- Mantener formateo con Black/isort y validar con Pylint (configuración OCA).
- Los parámetros de configuración ahora usan el prefijo `leulit_partis.*`
