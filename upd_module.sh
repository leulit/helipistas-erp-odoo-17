#!/bin/bash
#
# Actualiza un módulo de Odoo (-u) en el entorno indicado.
#
# Un `git pull` + `docker-compose up -d` NO actualiza un módulo: Odoo solo crea columnas
# y carga los ficheros XML durante un -u/-i. Sin esto, un campo nuevo queda en el registry
# sin columna en la base de datos y la primera lectura revienta con UndefinedColumn.
#
# Ver docs/produccion.md, sección "Despliegue / actualización".

set -u

SCRIPT_NAME=$(basename "$0")

if [ $# -lt 2 ] || [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    echo "================================================================="
    echo " Odoo Module Updater — HELIPISTAS ERP 17"
    echo "================================================================="
    echo ""
    echo "Uso:"
    echo "  ./$SCRIPT_NAME <modulo> <entorno> [--backup]"
    echo ""
    echo "Entornos:"
    echo "  dev  -> contenedor 'helipistas_odoo_17'  (docker/docker-compose.yml, local)"
    echo "  prod -> contenedor 'helipistas_odoo'     (dockerserver/, EC2 + EFS)"
    echo ""
    echo "Ejemplos:"
    echo "  ./$SCRIPT_NAME leulit_almacen dev"
    echo "  ./$SCRIPT_NAME leulit_almacen prod"
    echo "  ./$SCRIPT_NAME leulit_almacen prod --backup"
    echo ""
    echo "--backup hace un pg_dump antes de actualizar. NO es el comportamiento por"
    echo "defecto: tarda mucho en la base de produccion y ya hay copia diaria del EFS."
    echo "Usalo solo para un cambio de esquema grande o irreversible."
    echo "================================================================="
    exit 1
fi

MODULO="$1"
ENTORNO="$2"
BACKUP_ANTES=0
[ "${3:-}" == "--backup" ] && BACKUP_ANTES=1
BASE="productiu"

case "$ENTORNO" in
    dev)  CONTENEDOR="helipistas_odoo_17"; PSQL="helipistas_psql_15"; BACKUP_DIR="" ;;
    prod) CONTENEDOR="helipistas_odoo";    PSQL="helipistas_postgres"; BACKUP_DIR="/efs/HELIPISTAS-ODOO-17" ;;
    *)    echo "❌ Entorno '$ENTORNO' no válido. Usa 'dev' o 'prod'."; exit 1 ;;
esac

if ! docker inspect "$CONTENEDOR" >/dev/null 2>&1; then
    echo "❌ El contenedor '$CONTENEDOR' no existe en esta máquina."
    echo "   ¿Estás en el servidor correcto? dev = tu portátil, prod = la EC2."
    exit 1
fi

# El pg_dump NO va por defecto: en la base de produccion tarda muchisimo y ya hay copia
# diaria del EFS. Solo con --backup, para un cambio de esquema que no quieras arriesgar.
if [ "$BACKUP_ANTES" -eq 1 ]; then
    BACKUP="${BACKUP_DIR:-/tmp}/backup-$(date +%F-%H%M).dump"
    echo "💾 Copia de seguridad -> $BACKUP (esto puede tardar bastante)"
    if ! docker exec "$PSQL" pg_dump -U odoo -Fc "$BASE" > "$BACKUP"; then
        echo "❌ Falló el pg_dump. No se actualiza nada."
        rm -f "$BACKUP"
        exit 1
    fi
    echo "   $(du -h "$BACKUP" | cut -f1)"
fi

LOG="${BACKUP_DIR:-/tmp}/upd-$MODULO-$(date +%F-%H%M).log"

echo "⏱️  Actualizando '$MODULO' en '$BASE' ($ENTORNO, contenedor $CONTENEDOR)..."
echo "-----------------------------------------------------------------"

# -i y no -it: sin TTY la salida se puede redirigir. Con -it docker asigna un terminal y
# el fichero se llena de códigos de control.
# docker exec NO escribe en `docker logs`, que solo captura el proceso principal del
# contenedor: si no se guarda aquí, esta salida se pierde al cerrar la terminal.
docker exec -i "$CONTENEDOR" odoo -d "$BASE" -u "$MODULO" --stop-after-init 2>&1 | tee "$LOG"
RESULTADO=${PIPESTATUS[0]}

echo "-----------------------------------------------------------------"
echo "📄 Log: $LOG"

if [ "$RESULTADO" -ne 0 ]; then
    echo "❌ El comando terminó con error (código $RESULTADO). NO se reinicia el contenedor."
    [ -n "${BACKUP:-}" ] && echo "   Copia de seguridad en $BACKUP"
    exit "$RESULTADO"
fi

# Odoo puede acabar con código 0 y aun así haber tragado errores por el camino.
if grep -qiE "^.* (ERROR|CRITICAL) " "$LOG"; then
    echo "⚠️  Terminó con código 0 pero el log tiene líneas ERROR/CRITICAL:"
    grep -iE "^.* (ERROR|CRITICAL) " "$LOG" | head -20
    echo "   Revísalo antes de dar el despliegue por bueno."
fi

echo "✅ Módulo '$MODULO' actualizado en $ENTORNO."

# Con workers > 1 hay procesos vivos con el registry anterior en memoria. Odoo suele
# recargarlos solo por la secuencia base_registry_signaling, pero reiniciar lo garantiza.
echo "🔄 Reiniciando '$CONTENEDOR' para que los workers recarguen el registry..."
docker restart "$CONTENEDOR" >/dev/null && echo "   Hecho. Log: docker logs -f $CONTENEDOR"
