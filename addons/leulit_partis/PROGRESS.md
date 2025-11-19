# Diario de Progreso

> Última actualización: 2025-11-19

## Cambios Recientes

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

## Próximas Acciones

- [ ] Implementar vistas de dashboard para visualización de riesgos
- [ ] Añadir reportes QWeb para exportación de documentación SGSI
- [ ] Crear wizard para análisis masivo de riesgos
- [ ] Implementar workflow de aprobación para planes de tratamiento
- [ ] Añadir integraciones con módulos de auditoría

## Notas Técnicas

- Requiere `python-dateutil` para cálculos de fechas (`relativedelta`).
- Comando de actualización: `odoo-bin -d <base> -u leulit_partis`
- Mantener formateo con Black/isort y validar con Pylint (configuración OCA).
- Los parámetros de configuración ahora usan el prefijo `leulit_partis.*`
