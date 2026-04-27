# Módulo de Información Meteorológica — Documento de Conformidad Regulatoria

**Organización:** Leulit  
**Sistema:** ERP Leulit — módulo `leulit_meteo`  
**Versión del documento:** 1.0  
**Fecha:** 2026-04-27

---

## 1. Propósito del documento

Este documento describe el funcionamiento del módulo de información meteorológica integrado en el ERP Leulit, a efectos de auditoría interna y verificación de conformidad con los requisitos operacionales establecidos por AESA y EASA para operadores de aviación.

---

## 2. Descripción del sistema

El módulo `leulit_meteo` es una herramienta de gestión operacional que permite al personal de vuelo y de operaciones **consultar y registrar información meteorológica oficial** antes de cada vuelo o durante la planificación de operaciones.

El sistema **no es un proveedor de servicios meteorológicos certificado**. Su función es actuar como agregador de información proveniente de fuentes oficiales y presentarla de forma estructurada dentro del ERP operacional, facilitando la trazabilidad del proceso de toma de decisiones.

---

## 3. Fuentes de datos

| Fuente | Tipo de datos | Autoridad | Uso |
|---|---|---|---|
| **AEMET OpenData** | METAR, TAF, SIGMET oficiales | Agencia Estatal de Meteorología (AEMET) — organismo público adscrito al Ministerio para la Transición Ecológica | Aeródromos con servicio MET activo en España |
| **CheckWX** | METAR, TAF | Agregador de datos NOAA/ICAO de distribución global | Aeródromos sin servicio AEMET directo o fuera de España |

Los mensajes METAR y TAF se almacenan en el sistema **sin ninguna modificación** respecto al texto publicado por la fuente oficial. El campo `raw_metar` y `raw_taf` contienen el texto exacto recibido de AEMET u CheckWX y no puede ser editado por ningún usuario.

---

## 4. Integridad de los datos

- Los textos `raw_metar`, `raw_taf` y `raw_sigmet` son campos de **solo lectura** en la base de datos. No están expuestos a edición por el usuario en ninguna vista del sistema.
- Cada consulta genera un **registro único** en la tabla `leulit.meteo.metar` con marca de tiempo de la consulta (`fecha_consulta`) y hora de observación del mensaje (`observation_time`).
- Se registra el usuario que realizó la consulta (`user_id`) y el aeródromo solicitado (`icao_code`).
- El sistema almacena adicionalmente indicadores de **frescura del dato**: `edad_datos_minutos` y `estado_datos` (Actual < 90 min / Reciente 90–180 min / Antiguo > 180 min), que alertan al usuario sobre la vigencia de la información.

---

## 5. Trazabilidad operacional

Cuando el módulo de partes de vuelo (`leulit_vuelo`) está integrado con este módulo, cada parte de vuelo puede llevar asociado el registro METAR/TAF consultado en el momento de la planificación. Esto permite:

- Demostrar que se realizó consulta meteorológica previa al vuelo.
- Conocer las condiciones meteorológicas documentadas en el momento de la autorización del vuelo.
- Mantener el historial de consultas vinculado al expediente del vuelo, disponible para inspección por AESA u otros organismos competentes.

---

## 6. Limitaciones del sistema y responsabilidad del piloto/operador

El sistema `leulit_meteo` es una herramienta de apoyo a la gestión operacional. El operador y el piloto al mando son responsables de:

1. Verificar que la información meteorológica consultada es suficientemente reciente para la operación prevista, conforme a los mínimos establecidos en sus procedimientos operacionales aprobados (OM, OpsSpec o equivalente).
2. Contrastar la información del sistema con los servicios oficiales de información de vuelo (AIS España, METEOAVIATION o los servicios equivalentes habilitados por AEMET para briefings operacionales) cuando la operación así lo requiera.
3. Aplicar los mínimos meteorológicos establecidos en su Especificación de Operaciones (OpsSpec) o Manual de Operaciones, con independencia de lo que muestre el sistema.

**El sistema no sustituye al briefing meteorológico oficial exigido por la regulación para operaciones que así lo requieran.**

---

## 7. Normativa de referencia

| Norma | Descripción | Aplicación |
|---|---|---|
| Reglamento (UE) 2018/1139 | Marco normativo común en aviación civil de la Unión Europea | Marco general |
| Reglamento (UE) 2017/373 | Requisitos para los proveedores de servicios de gestión del tránsito aéreo e información meteorológica | Contextualiza qué es un proveedor MET certificado (este sistema no lo es) |
| Reglamento (UE) 2019/947 | Operaciones con UAS | Requisitos de información meteorológica para operaciones UAS |
| SERA.5005 (Reglamento (UE) 2016/1185) | Información meteorológica para planificación de vuelo | Obligación de consulta met previa |
| CAT.OP.MPA.175 | Condiciones meteorológicas mínimas de operación | Para operadores CAT |
| NCO.OP.135 | Condiciones meteorológicas — operaciones no comerciales | Para operaciones NCO |
| AIP España — ENR 1.10 | SIGMET / AIRMET — áreas FIR (LECM, LECB, GCCC) | Fuente de referencia para FIR |

---

## 8. Control de acceso

El acceso al módulo está controlado por el sistema de permisos de Odoo:

- **Lectura** de reportes METAR: perfil de usuario estándar (piloto, coordinador de operaciones).
- **Creación y consulta** de nuevos reportes: perfil de usuario estándar.
- **Configuración** (API keys, aeródromos de referencia): perfil de administrador únicamente.

Las API keys de acceso a AEMET y CheckWX se almacenan cifradas en la base de datos y no son accesibles desde la interfaz de usuario una vez guardadas.

---

## 9. Retención de datos

Los registros de consultas meteorológicas se conservan en la base de datos del ERP. La política de retención sigue la política general de retención de datos del operador, que debe ser coherente con los requisitos de documentación establecidos por AESA para el tipo de operación (generalmente un mínimo de 3 años para registros operacionales de vuelo).

---

## 10. Declaración de conformidad

El módulo `leulit_meteo` está diseñado para apoyar el cumplimiento de los requisitos de información meteorológica previa al vuelo establecidos por la normativa aplicable, mediante el acceso estructurado, registrado y trazable a información procedente de fuentes oficiales.

El sistema no constituye en sí mismo un servicio de información meteorológica aeronáutica (MET SP) según la definición del Reglamento (UE) 2017/373, y no requiere certificación como tal.

---

*Documento elaborado por el equipo de desarrollo de Leulit. Para consultas regulatorias contactar con el responsable de cumplimiento del operador.*
