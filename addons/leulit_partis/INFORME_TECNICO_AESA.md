# **INFORME TÉCNICO PARA AESA**
## **Módulo Odoo: Leulit PART-IS - Sistema de Gestión de Seguridad de la Información**

### **DATOS DE IDENTIFICACIÓN**

| **Campo** | **Valor** |
|-----------|-----------|
| **Denominación** | Leulit PART-IS |
| **Versión** | 17.0.1.0.0 |
| **Licencia** | AGPL-3.0 |
| **Plataforma** | Odoo 17.0 (ERP Open Source) |
| **Marco Normativo** | Reglamento (UE) 2018/1139, EASA Part-IS, normativa AESA SGSI |
| **Metodología** | MAGERIT v3, PILAR (CCN-CERT) |
| **Desarrollador** | Leulit |

---

## **1. OBJETO Y ALCANCE**

### **1.1 Finalidad**

El módulo **Leulit PART-IS** constituye una herramienta informática diseñada para asistir a las organizaciones aeronáuticas en el **cumplimiento de los requisitos** establecidos en el **Reglamento EASA Part-IS** (Information Security) y la normativa complementaria de **AESA**, específicamente:

- **IS.ORG.0100** - Establecimiento del Sistema de Gestión de Seguridad de la Información (SGSI)
- **IS.D.OR.205** - Análisis y evaluación de riesgos de seguridad de la información
- **IS.D.OR.210** - Tratamiento de riesgos de seguridad de la información
- **IS.D.OR.215** - Gestión de activos de información
- **IS.D.OR.220** - Gestión documental del SGSI

### **1.2 Ámbito de Aplicación**

El sistema es aplicable a:

- ✈️ Operadores aéreos comerciales (AOC)
- 🚁 Operadores de helicópteros
- 🔧 Organizaciones de mantenimiento (Part-145, CAMO)
- 🏢 Organizaciones de gestión continuada de aeronavegabilidad
- 🎓 Centros de formación aeronáutica aprobados
- 🏭 Organizaciones de diseño y producción aeronáutica

---

## **2. ARQUITECTURA Y FUNDAMENTOS TÉCNICOS**

### **2.1 Base Tecnológica**

El módulo se integra en el **ERP Odoo** como extensión del framework **OCA Management System**, garantizando:

- **Trazabilidad completa** mediante base de datos PostgreSQL
- **Auditoría** de todas las operaciones (histórico de cambios)
- **Multi-empresa** para grupos aeronáuticos
- **Control de acceso** basado en roles y permisos
- **Integridad referencial** de datos críticos

### **2.2 Componentes del Sistema**

El módulo se estructura en **cuatro módulos funcionales** principales:

#### **A) Gestión de Activos de Información (IS.D.OR.215)**

**Modelo:** `mgmtsystem.hazard` (extendido para activos)

**Funcionalidades:**
- Inventario estructurado de activos críticos de información
- Clasificación según tipología (datos, servicios, sistemas, personal, instalaciones)
- **Valoración C-I-D** (Confidencialidad, Integridad, Disponibilidad):
  - Escala 1-5 según metodología MAGERIT
  - Cálculo automático del **índice de criticidad PART-IS**
  - Categorización automática: Residual, Bajo, Medio, Alto, Crítico
- Gestión del ciclo de revisión:
  - Periodicidad configurable (trimestral, semestral, anual)
  - Cálculo automático de **próxima fecha de revisión**
  - Alertas de vencimiento

**Cumplimiento normativo:**
- IS.D.OR.215(a) - Inventario de activos
- IS.D.OR.215(b) - Clasificación de activos
- IS.D.OR.215(c) - Responsabilidad sobre activos

**Inventario de Equipos IT (IS.D.OR.215):**

**Modelo:** `leulit.partis.equipment`

Complementa la gestión de activos con un inventario detallado del hardware
informático (ordenadores de sobremesa, portátiles, tablets, móviles, servidores,
equipos de red y periféricos). Cada equipo registra:

- Identificación: código de inventario único, fabricante, modelo y número de serie
- Asignación: usuario, departamento y ubicación física
- Ciclo de vida: fecha de compra, fin de garantía y estado (en servicio, almacén,
  reparación, retirado)
- Controles de seguridad SGSI: cifrado de disco, antivirus/EDR y estado de parcheo
- Vínculo opcional al activo de información SGSI (`mgmtsystem.hazard`) asociado

Aporta evidencia directa del inventario de equipos y del estado de sus controles
de seguridad, soportando los requisitos de gestión de activos PART-IS y la
identificación de equipos sin cifrado, sin antivirus o con garantía caducada.

#### **B) Análisis de Riesgos (IS.D.OR.205)**

**Modelo:** `mgmtsystem.hazard` (extendido para análisis de riesgos)

**Funcionalidades:**
- **Evaluación de riesgos intrínsecos:**
  - Selección de activo primario afectado
  - Identificación de amenaza (catálogo reutilizable)
  - Identificación de vulnerabilidad (catálogo corporativo)
  - Matriz **Probabilidad × Impacto** (escala 1-5 → resultado 1-25)
  - Categorización automática del nivel de riesgo

- **Trazabilidad metodológica:**
  - Referencias a catálogos normativos (ENS, ISO/IEC 27005, NIST)
  - Documentación de hipótesis y criterios
  - Histórico de valoraciones

- **Umbrales configurables:**
  - Definición de niveles de tolerancia al riesgo
  - Parametrización por tipo de operación aeronáutica
  - Alineación con apetito al riesgo organizacional

**Cumplimiento normativo:**
- IS.D.OR.205(a) - Identificación de riesgos
- IS.D.OR.205(b) - Análisis de riesgos
- IS.D.OR.205(c) - Evaluación de riesgos

#### **C) Tratamiento de Riesgos (IS.D.OR.210)**

**Funcionalidades:**
- **Definición de estrategias de tratamiento:**
  - Reducir (mitigación mediante controles)
  - Evitar (eliminación del riesgo)
  - Aceptar (asunción consciente)
  - Transferir (seguros, subcontratación)

- **Gestión de controles:**
  - Catálogo de controles corporativos (preventivos, detectivos, correctivos)
  - Vinculación múltiple de controles a cada riesgo
  - Referencias normativas (ISO/IEC 27002, ENS, NIST CSF)
  - Guías de implementación

- **Cálculo de riesgo residual:**
  - Evaluación de eficacia de controles (0-3)
  - Ajuste de probabilidad e impacto residuales
  - Valoración automática del riesgo post-tratamiento
  - Verificación de cumplimiento de umbrales

**Cumplimiento normativo:**
- IS.D.OR.210(a) - Selección de opciones de tratamiento
- IS.D.OR.210(b) - Plan de tratamiento de riesgos
- IS.D.OR.210(c) - Aprobación del plan
- IS.D.OR.210(d) - Implementación de controles

#### **D) Gestión Documental del SGSI (IS.D.OR.220)**

**Modelo:** `document.page` (extendido)

**Funcionalidades:**
- **Estructura documental normalizada:**
  - Manual del SGSI
  - Política de Seguridad de la Información
  - Procedimientos de seguridad
  - Registro de riesgos
  - Catálogo de controles
  - Informes de auditoría

- **Trazabilidad documental:**
  - Vinculación con activos, riesgos y controles
  - Control de versiones
  - Gestión de aprobaciones
  - Cálculo automático de fechas de revisión

- **Generación de evidencias:**
  - Exportación de registros para auditorías
  - Resúmenes ejecutivos automáticos
  - Listados de controles implementados

**Cumplimiento normativo:**
- IS.D.OR.220(a) - Documentación del SGSI
- IS.D.OR.220(b) - Control de documentos
- IS.D.OR.220(c) - Registros de seguridad

---

## **3. CATÁLOGOS CORPORATIVOS**

El módulo incorpora **tres catálogos reutilizables** que estandarizan el análisis:

### **3.1 Catálogo de Amenazas**
- Clasificación: Natural, Accidental, Deliberada, Entorno
- Probabilidad sugerida por defecto
- Referencias a marcos normativos
- Activo (permite habilitar/deshabilitar amenazas)

### **3.2 Catálogo de Vulnerabilidades**
- Referencias a vulnerabilidades conocidas (CVE, CERT)
- Recomendaciones de mitigación
- Vinculación con activos afectados
- Mantenimiento corporativo centralizado

### **3.3 Catálogo de Controles**
- Tipología: Preventivo, Detectivo, Correctivo
- Referencias normativas (ISO 27002, ENS, NIST)
- Objetivos de control
- Guías de implementación
- Estimación de costes

---

## **4. METODOLOGÍA DE ANÁLISIS**

### **4.1 Base Metodológica: MAGERIT v3**

El módulo implementa la metodología **MAGERIT** (Metodología de Análisis y Gestión de Riesgos de los Sistemas de Información), desarrollada por el **CCN-CERT** y reconocida por:

- Esquema Nacional de Seguridad (ENS)
- Administraciones públicas españolas
- Sector privado como buena práctica

**Ventajas:**
✅ Metodología oficial española  
✅ Alineada con ISO/IEC 27005  
✅ Ampliamente auditada y validada  
✅ Permite cumplimiento dual EASA + ENS  

### **4.2 Herramienta de Análisis: PILAR**

Para el análisis cuantitativo se aplican los principios de **PILAR** (Procedimiento Informático Lógico de Análisis de Riesgos), complemento de MAGERIT que proporciona:

- Matrices de probabilidad e impacto
- Escalas de valoración 1-5
- Cálculo de severidad (1-25)
- Umbrales de tolerancia

### **4.3 Adaptación a PART-IS**

La implementación adapta MAGERIT/PILAR a los requisitos específicos de PART-IS mediante:

- Terminología aeronáutica
- Activos críticos del sector (sistemas ACARS, navegación, operaciones, etc.)
- Amenazas específicas (ciberseguridad aviación, sabotaje, etc.)
- Controles adaptados a entornos operacionales aeronáuticos
- Periodicidad de revisiones según criticidad

---

## **5. FLUJO OPERATIVO DEL SISTEMA**

### **Fase 1: Identificación de Activos**
1. Inventario de activos críticos de información
2. Clasificación según naturaleza y función operacional
3. Valoración C-I-D (1-5)
4. Cálculo automático de criticidad
5. Asignación de responsables

### **Fase 2: Análisis de Riesgos**
1. Selección de activo objeto de análisis
2. Identificación de amenazas potenciales (catálogo)
3. Identificación de vulnerabilidades existentes (catálogo)
4. Valoración de probabilidad intrínseca (1-5)
5. Valoración de impacto intrínseco (1-5, según C-I-D del activo)
6. Cálculo automático de severidad intrínseca (1-25)
7. Categorización del nivel de riesgo

### **Fase 3: Tratamiento**
1. Selección de estrategia (reducir/evitar/aceptar/transferir)
2. Asociación de controles del catálogo
3. Documentación del plan de implementación
4. Valoración de eficacia esperada
5. Cálculo de probabilidad e impacto residuales
6. Verificación de cumplimiento de umbrales de tolerancia

### **Fase 4: Documentación y Seguimiento**
1. Generación de documentos SGSI
2. Vinculación con activos, riesgos y controles
3. Programación de revisiones
4. Alertas automáticas de vencimiento
5. Preparación de evidencias para auditorías

---

## **6. CAPACIDADES DE REPORTING Y AUDITORÍA**

### **6.1 Exportaciones Disponibles**

- 📊 **Inventario de activos** con valoración C-I-D
- ⚠️ **Registro de riesgos** con nivel intrínseco y residual
- 🛡️ **Catálogo de controles** implementados
- 📈 **Dashboards** de estado del SGSI
- 📋 **Matriz de riesgos** (heatmap)
- 📄 **Manual del SGSI** con trazabilidad

### **6.2 Trazabilidad para Auditorías AESA**

El sistema proporciona evidencia documental de:

✅ Inventario completo de activos críticos (IS.D.OR.215)  
✅ Análisis de riesgos sistemático (IS.D.OR.205)  
✅ Planes de tratamiento documentados (IS.D.OR.210)  
✅ Controles implementados con responsables  
✅ Ciclos de revisión y mejora continua  
✅ Histórico de decisiones (cambios auditados)  
✅ Gestión documental completa del SGSI  

---

## **7. CUMPLIMIENTO NORMATIVO**

### **7.1 Requisitos EASA Part-IS Cubiertos**

| **Requisito** | **Artículo** | **Cobertura** |
|---------------|--------------|---------------|
| Establecimiento SGSI | IS.ORG.0100 | ✅ Completo |
| Gestión de activos | IS.D.OR.215 | ✅ Completo |
| Análisis de riesgos | IS.D.OR.205 | ✅ Completo |
| Tratamiento de riesgos | IS.D.OR.210 | ✅ Completo |
| Gestión documental | IS.D.OR.220 | ✅ Completo |
| Mejora continua | IS.D.OR.305 | ✅ Ciclos automáticos |

### **7.2 Estándares y Marcos de Referencia**

- ✅ **ISO/IEC 27001:2022** - Sistema de Gestión de Seguridad de la Información
- ✅ **ISO/IEC 27005:2022** - Gestión de riesgos de seguridad de la información
- ✅ **MAGERIT v3** - Metodología oficial española
- ✅ **ENS** - Esquema Nacional de Seguridad (opcional)
- ✅ **NIST Cybersecurity Framework** - Controles complementarios

---

## **8. SEGURIDAD Y CONTROL DE ACCESO**

### **8.1 Gestión de Permisos**

El módulo implementa **control de acceso basado en roles**:

- **Responsable SGSI** - Acceso completo, gestión de configuración
- **Analista de Riesgos** - Creación y edición de análisis
- **Auditor** - Solo lectura, acceso a evidencias
- **Usuario** - Consulta de activos asignados

### **8.2 Integridad de Datos**

- ✅ Validaciones de datos obligatorios
- ✅ Restricciones de integridad referencial
- ✅ Histórico completo de modificaciones (audit trail)
- ✅ Copias de seguridad automáticas (responsabilidad de Odoo)
- ✅ Exportaciones con firma digital (módulos adicionales)

---

## **9. DEPENDENCIAS TÉCNICAS**

### **9.1 Módulos OCA Requeridos**

El sistema requiere los siguientes módulos de la **Odoo Community Association**:

- `mgmtsystem` - Framework base de sistemas de gestión
- `mgmtsystem_hazard` - Gestión de peligros/activos
- `mgmtsystem_hazard_risk` - Análisis de riesgos
- `mgmtsystem_manual` - Documentación de sistemas
- `document_page` - Gestión documental
- `hr` - Recursos humanos (responsables)

### **9.2 Dependencias Externas**

- **Python:** `python-dateutil` (cálculos de fechas)
- **Base de datos:** PostgreSQL 12+
- **Plataforma:** Odoo Community/Enterprise 17.0

---

## **10. MANTENIMIENTO Y EVOLUCIÓN**

### **10.1 Actualizaciones**

El módulo sigue el ciclo de lanzamiento de **Odoo** y **OCA**, garantizando:

- Compatibilidad con versiones LTS de Odoo
- Corrección de errores mediante parches
- Evolución según cambios normativos
- Migración a futuras versiones de Odoo

### **10.2 Soporte Técnico**

- Documentación completa en formato RST
- Ejemplos de uso en README
- Tests automatizados de validación
- Comunidad OCA para incidencias

---

## **11. CASOS DE USO TÍPICOS**

### **Caso 1: Compañía Aérea con AOC**

**Activos críticos:**
- Sistemas de reservas
- Sistemas de operaciones de vuelo
- Datos de pasajeros
- Sistemas ACARS
- Bases de datos de mantenimiento

**Riesgos principales:**
- Ciberataques a sistemas operacionales
- Pérdida de datos personales (RGPD + PART-IS)
- Sabotaje de sistemas de navegación
- Indisponibilidad de sistemas críticos

**Controles implementados:**
- Cifrado de comunicaciones
- Autenticación multifactor
- Copias de seguridad cifradas
- Monitorización 24/7
- Plan de respuesta a incidentes

### **Caso 2: Centro de Mantenimiento Part-145**

**Activos críticos:**
- Documentación técnica aeronáutica
- Sistemas de trazabilidad de componentes
- Registros de mantenimiento
- Acceso a redes del fabricante

**Controles específicos:**
- Control de acceso físico a documentación
- Trazabilidad de cambios en registros
- Segregación de redes
- Formación específica en ciberseguridad

---

## **12. CONCLUSIONES**

El módulo **Leulit PART-IS** constituye una **solución integral y automatizada** para el cumplimiento de los requisitos de seguridad de la información establecidos por **EASA** y **AESA**, proporcionando:

✅ **Cumplimiento normativo verificable** de IS.D.OR.205, IS.D.OR.210 y IS.D.OR.215  
✅ **Metodología reconocida** (MAGERIT/PILAR) compatible con ISO 27001  
✅ **Trazabilidad completa** para auditorías AESA  
✅ **Automatización** de cálculos y revisiones periódicas  
✅ **Integración** en sistemas ERP existentes (Odoo)  
✅ **Escalabilidad** para organizaciones de cualquier tamaño  
✅ **Gestión documental** completa del SGSI  

El sistema ha sido diseñado siguiendo las **mejores prácticas** de desarrollo de módulos Odoo (estándares OCA) y puede ser **auditado por AESA** para verificar su conformidad con los requisitos del Reglamento Part-IS.

---

**Información de contacto:**  
**Leulit**  
Web: https://leulit.com  
Versión del módulo: 17.0.1.0.0  
Fecha de documento: 15 de diciembre de 2025  

---

*Este documento técnico puede ser presentado a AESA como parte de la documentación del SGSI de la organización, evidenciando las herramientas empleadas para el cumplimiento de los requisitos normativos.*
