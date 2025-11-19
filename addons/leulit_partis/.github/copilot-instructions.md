# Copilot Instructions: Leulit PART-IS

## 🚫 **Lo que  debe hacer el Agente (Inclusiones)**

* Proponer soluciones que no se alineen con las mejores prácticas de desarrollo de Odoo o con las directrices de OCA (Odoo Community Association).
* Proponer soluciones que cumplan con la documentación, modelos, vistas y flujos de odoo 17.
* Proponer soluciones que no consideren la compatibilidad con Odoo 16.
* Proponer soluciones que consideren las mejores prácticas de desarrollo de módulos Odoo, incluyendo el uso adecuado de decoradores, herencia de modelos y vistas, y gestión de permisos.
* Proponer soluciones que consideren la compatibilidad con las dependencias de OCA.
* Seguir en todo momentos los principios, directrices. convenciones de MAGERIT y PILAR para la gestión de riesgos en sistemas de información.
* Proponer soluciones que aseguren la integridad, confidencialidad y disponibilidad de la información gestionada en Odoo.
* Proponer soluciones que aseguren la correcta gestión de activos, riesgos y controles según los estándares de seguridad de la información.
* Seguir los principios y directrices de magerit y pilar y que el objetivo es dar complimiento a las directrices de EASA en su reglamento PART-IS 
* Seguir los principios y directrices de la normativa SGSI de AESA a la que demos dar complimiento.
* Proponer soluciones que contemplen el manejo de errores, la eficiencia en el procesamiento de datos
* Seguir los prinicipios SOLID y DRY en el desarrollo de código.
* Proponer soluciones que optimicen el rendimiento, la robustez y la usabilidad del módulo
* Seguir y utilizar siempre que sea posible modulos estandars de ODOO y OCA antes de crear nuevos.
* EL objetivo principal es crear un módulo Odoo que permita gestionar el SGSI (Sistema de Gestión de Seguridad de la Información) para dar cumplimiento a las normativas y directrices de EASA PART-IS y  SGSI (Sistema de Gestión de SEguridad de la Información en las compañías aéreas).
* Crear un Sistema de Gestión de Seguridad de la Información (SGSI) para compañías aéreas que cumpla con EASA PART-IS y AESA, utilizando MAGERIT y PILAR como herramientas metodológicas (no como el objetivo final).
* jeararquí de prioridades
1. EASA PART-IS (Regulación Europea de Seguridad de la Información en Aviación)
   └── Requisitos obligatorios para compañías aéreas
   
2. AESA - SGSI (Agencia Estatal de Seguridad Aérea)
   └── Normativa española para compañías aéreas
   
3. MAGERIT + PILAR (Metodologías de análisis de riesgos)
   └── Herramientas para IMPLEMENTAR los requisitos 1 y 2

   Funcionalidad Principal
* El módulo debe generar y mantener la documentación del SGSI que las compañías aéreas necesitan para:

✅ Auditorías EASA/AESA
✅ Certificaciones de seguridad
✅ Gestión continua del SGSI
✅ Trazabilidad de activos críticos
✅ Análisis de riesgos documentado
✅ Controles implementados y verificados


## 🚫 **Lo que NO debe hacer el Agente (Exclusiones)**

* Generar soluciones que violen los principios SOLID, DRY, comprometan el rendimiento, la robustez **o la usabilidad**.
* Implementar funcionalidades especulativas ("por si acaso" - YAGNI).
* Ignorar la estructura de directorios definida o las convenciones de nomenclatura.
* Asumir una solución de gestión de estado o persistencia si no ha sido especificada previamente.
* Producir código que no contemple el manejo de errores, la eficiencia en el procesamiento de datos geográficos **o que resulte en una experiencia de usuario deficiente.**
* Hacer propuestas que supongan errores de compilación o ejecución en el entorno Odoo.
* Hacer propuestas que puedan provocar errores en tiempo de ejecución debido a referencias incorrectas a modelos, campos o vistas en Odoo.
* Hacer propuestas que no sigan las mejores prácticas de desarrollo de módulos Odoo, incluyendo el uso adecuado de decoradores, herencia de modelos y vistas, y gestión de permisos.
* Hacer propuestas que no consideren la compatibilidad con las dependencias de OCA.
* Hacer propuestas que provoquen errores o pérdidas de datos en la base de datos de Odoo.
* Hacer propuestas que provoquen errores o pèrdidas de funcionalidad en los módulos/funcionalidades existentes.
* No modificar directamente los modelos base de OCA; siempre heredar y extender.

