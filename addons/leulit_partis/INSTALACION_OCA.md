# Instalación de Dependencias OCA para leulit_partis

## Módulos OCA Requeridos

Este módulo requiere los siguientes módulos de OCA para Odoo 17:

### 1. Repositorio: OCA/management-system (branch 17.0)

**Módulos necesarios:**
- `mgmtsystem` - v17.0.1.1.1 (Base del sistema de gestión)
- `mgmtsystem_hazard` - v17.0.1.1.0 (Usado para activos de información)
- `mgmtsystem_hazard_risk` - v17.0.1.1.0 (Usado para análisis de riesgos SGSI)
- `mgmtsystem_manual` - v17.0.1.0.1 (Para documentación del SGSI)

**Clonar repositorio:**
```bash
cd ~/odoo17/addons  # Ajusta la ruta a tu instalación
git clone -b 17.0 https://github.com/OCA/management-system.git
```

### 2. Repositorio: OCA/knowledge (branch 17.0)

**Módulos necesarios:**
- `document_page` - v17.0 (Sistema de documentación para Manual SGSI, políticas y procedimientos)

**Clonar repositorio:**
```bash
cd ~/odoo17/addons  # Ajusta la ruta a tu instalación
git clone -b 17.0 https://github.com/OCA/knowledge.git
```

## Verificación de Instalación

Después de clonar los repositorios, verifica que los módulos están disponibles:

```bash
# Reinicia Odoo con actualización de lista de módulos
odoo-bin -c odoo.conf -u all --stop-after-init

# O actualiza la lista desde la interfaz web:
# Apps > Actualizar lista de aplicaciones
```

## Orden de Instalación

1. **mgmtsystem** (se instalará automáticamente como dependencia)
2. **mgmtsystem_hazard** (se instalará automáticamente)
3. **mgmtsystem_hazard_risk** (se instalará automáticamente)
4. **mgmtsystem_manual** (se instalará automáticamente)
5. **document_page** (se instalará automáticamente)
6. **leulit_partis** ← Tu módulo principal

## Instalación del Módulo

Una vez instaladas las dependencias OCA:

```bash
# Copiar leulit_partis a addons/
cp -r leulit_partis ~/odoo17/addons/

# Instalar el módulo
odoo-bin -c odoo.conf -d <nombre_bd> -i leulit_partis

# O desde la interfaz web:
# Apps > Buscar "Leulit PART-IS" > Instalar
```

## Estructura de Addons Recomendada

```
odoo17/
├── addons/
│   ├── management-system/
│   │   ├── mgmtsystem/
│   │   ├── mgmtsystem_hazard/
│   │   ├── mgmtsystem_hazard_risk/
│   │   └── mgmtsystem_manual/
│   ├── knowledge/
│   │   └── document_page/
│   └── leulit_partis/
│       ├── models/
│       ├── views/
│       ├── security/
│       └── __manifest__.py
```

## Mapeo Conceptual OCA → PART-IS

| Módulo OCA | Usado Como | Objetivo PART-IS/AESA |
|-----------|------------|----------------------|
| `mgmtsystem` | Base | Infraestructura de sistemas de gestión |
| `mgmtsystem.hazard` | **Activo + Riesgo SGSI** | Un único modelo representa tanto activos como riesgos con análisis |
| `mgmtsystem_hazard_risk` | Cálculos de riesgo | Añade campos de cálculo al modelo hazard (NO crea modelo nuevo) |
| `mgmtsystem_manual` | Manual SGSI | Documentación del sistema de gestión |
| `document.page` | Documentos PART-IS | Políticas, procedimientos, registros |

**IMPORTANTE**: 
- `mgmtsystem.hazard` es el modelo central (representa ACTIVOS)
- `mgmtsystem_hazard_risk` NO crea un modelo separado, **EXTIENDE** `mgmtsystem.hazard`
- Nuestro módulo añade dos extensiones a `mgmtsystem.hazard`:
  - Campos de ACTIVO (C-I-D, criticidad)
  - Campos de ANÁLISIS DE RIESGO (amenazas, vulnerabilidades, controles MAGERIT/PILAR)

## Soporte

Para más información sobre los módulos OCA:

- **Management System**: https://github.com/OCA/management-system
- **Knowledge**: https://github.com/OCA/knowledge
- **Documentación OCA**: https://odoo-community.org/

## Licencia

Todos los módulos OCA están bajo licencia AGPL-3.0
