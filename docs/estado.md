# Estado del proyecto
_Última actualización: 2026-09-28_

## Resumen
ERP Odoo 17 para Helipistas (operador de helicópteros): vuelos, mantenimiento/CAMO, escuela
de vuelo, calidad/seguridad, almacén Part-145. Lógica propia en módulos `leulit_*` sobre Odoo
estándar + ~350 módulos OCA vendorizados en `addons/third-party-addons/`.

## En curso
- Nada abierto identificado al iniciar esta sesión (repo sin tareas en curso registradas).

## Hecho recientemente
- Renombrado `leulit_ia` → `leulit_ai`; el chat lateral se sustituyó por búsqueda universal en IA.
- `leulit_ai`: eliminada dependencia externa `google.cloud.aiplatform`.
- Ajustes de `Dockerfile`/`docker-compose.yml` (dependencias y configuración).
- `leulit_reports`: nueva estructura y campos para informes de clases prácticas y teóricas.
- `leulit_tarea`: tabla semanal de tareas rehecha varias veces (agrupación por semana, orden,
  archivadas, ACL del menú).

## Bloqueos
- No hay Odoo/Postgres local en este entorno de desarrollo — no se puede ejecutar `odoo-bin`
  ni las pruebas de módulo aquí; solo hay entorno de producción (ver memoria del proyecto).

## Próximo paso
- Sin tarea concreta definida; a la espera de la siguiente petición del usuario.
