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

# Un ALTER TABLE necesita ACCESS EXCLUSIVE sobre la tabla: con el Odoo que sirve peticiones
# vivo, cualquier consulta abierta la bloquea y Postgres cancela el -u con "canceling
# statement due to lock timeout". Por eso se para el contenedor y la actualizacion va en uno
# de usar y tirar clonado de el: misma imagen, misma red, mismas variables y mismos volumenes
# (ahi esta /etc/odoo y /mnt/extra-addons), sin publicar puertos.
IMAGEN=$(docker inspect -f '{{.Image}}' "$CONTENEDOR")
RED=$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' "$CONTENEDOR" | awk '{print $1}')
ENV_FILE=$(mktemp)
docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$CONTENEDOR" > "$ENV_FILE"

# Pase lo que pase (error, Ctrl-C), el ERP tiene que volver a levantarse.
trap 'rm -f "$ENV_FILE"; docker start "$CONTENEDOR" >/dev/null 2>&1' EXIT

echo "⏸️  Parando '$CONTENEDOR': el ERP queda caido hasta que acabe el script."
docker stop "$CONTENEDOR" >/dev/null

# La salida no va a `docker logs` (ese solo captura el proceso principal del contenedor de
# produccion), asi que se guarda aqui o se pierde al cerrar la terminal.
docker run --rm --network "$RED" --env-file "$ENV_FILE" --volumes-from "$CONTENEDOR" \
    "$IMAGEN" odoo -d "$BASE" -u "$MODULO" --no-http --stop-after-init 2>&1 | tee "$LOG"
RESULTADO=${PIPESTATUS[0]}

echo "-----------------------------------------------------------------"
echo "📄 Log: $LOG"

if [ "$RESULTADO" -ne 0 ]; then
    echo "❌ El comando terminó con error (código $RESULTADO). La base queda como estaba:"
    echo "   Odoo hace el -u en una transacción y la deshace entera si algo revienta."
    if grep -q "lock timeout" "$LOG"; then
        echo "   Es un bloqueo de Postgres: alguien más tiene la tabla cogida (Metabase, n8n,"
        echo "   una sesión psql abierta). Míralo con:"
        echo "   docker exec -i $PSQL psql -U odoo -d $BASE -c \"select pid, state, query from pg_stat_activity where pid <> pg_backend_pid()\""
    fi
    [ -n "${BACKUP:-}" ] && echo "   Copia de seguridad en $BACKUP"
    echo "🔄 Arrancando '$CONTENEDOR' de nuevo..."
    exit "$RESULTADO"
fi

# Odoo puede acabar con código 0 y aun así haber tragado errores por el camino.
if grep -qiE "^.* (ERROR|CRITICAL) " "$LOG"; then
    echo "⚠️  Terminó con código 0 pero el log tiene líneas ERROR/CRITICAL:"
    grep -iE "^.* (ERROR|CRITICAL) " "$LOG" | head -20
    echo "   Revísalo antes de dar el despliegue por bueno."
fi

echo "✅ Módulo '$MODULO' actualizado en $ENTORNO."

echo "🔄 Arrancando '$CONTENEDOR' con el registry nuevo..."
docker start "$CONTENEDOR" >/dev/null && echo "   Hecho. Log: docker logs -f $CONTENEDOR"
