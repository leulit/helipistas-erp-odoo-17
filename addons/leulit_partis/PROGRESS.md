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

### 2025-12-15: Revisión Completa y Vistas Finales
- ✅ **Completadas todas las vistas necesarias** para gestión SGSI PART-IS
- ✅ **Agregadas vistas Tree personalizadas** para Activos y Riesgos
- ✅ **Agregadas vistas Search avanzadas** con filtros por criticidad y niveles de riesgo
- ✅ **Implementados filtros de búsqueda** en todos los catálogos (Amenazas, Vulnerabilidades, Controles)
- ✅ **Creado menú de Activos de Información** independiente
- ✅ **Creado menú de Análisis de Riesgos** independiente
- ✅ **Agregado menú de Panel de Control** para dashboard futuro
- ✅ **Agregado menú de Configuración** con acceso a umbrales MAGERIT
- ✅ **Indicadores visuales** (decoraciones de color) para identificación rápida de criticidad
- ✅ **Corregidos errores** de instalación y traducción en Odoo 17
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

## Próximas Acciones (Prioridad PART-IS)

### Alta Prioridad (Requisitos PART-IS)
- [ ] **Dashboard de indicadores SGSI** (IS.D.OR.305 - Mejora continua)
  - Gráficos de activos por criticidad
  - Matriz de riesgos (heatmap)
  - KPIs de cumplimiento
  - Alertas de revisiones pendientes
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

- [ ] **Workflow de aprobación** (IS.D.OR.210)
  - Estado de planes de tratamiento (borrador/aprobado/implementado)
  - Aprobaciones por responsable SGSI
  - Histórico de decisiones

### Media Prioridad (Mejoras Operativas)
- [ ] **Wizard de análisis masivo de riesgos**
  - Evaluar múltiples amenazas sobre un activo
  - Aplicar controles en lote
  
- [ ] **Integraciones con auditoría**
  - Módulo `auditlog` de OCA
  - Registro de accesos a información crítica

### Baja Prioridad (Funcionalidades Avanzadas)
- [ ] **Exportación a formatos estándar**
  - CSV para análisis externo
  - PDF con firma digital
  
- [ ] **Notificaciones automáticas**
  - Email de revisiones pendientes
  - Alertas de riesgos críticos sin tratar

## Notas Técnicas

- Requiere `python-dateutil` para cálculos de fechas (`relativedelta`).
- Comando de actualización: `odoo-bin -d <base> -u leulit_partis`
- Mantener formateo con Black/isort y validar con Pylint (configuración OCA).
- Los parámetros de configuración ahora usan el prefijo `leulit_partis.*`
