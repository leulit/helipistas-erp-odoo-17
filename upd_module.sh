#!/bin/bash
#
# Actualiza (-u) o instala (--install, -i) un módulo de Odoo en el entorno indicado.
#
# Un `git pull` + `docker-compose up -d` NO actualiza un módulo: Odoo solo crea columnas
# y carga los ficheros XML durante un -u/-i. Sin esto, un campo nuevo queda en el registry
# sin columna en la base de datos y la primera lectura revienta con UndefinedColumn.
#
# Por defecto el ERP NO se para: el -u va en un proceso aparte dentro del contenedor vivo.
# Con --stop se para el contenedor y la actualizacion va en un clon de usar y tirar, que es
# lo unico que funciona cuando el -u tiene que hacer ALTER TABLE. Ver la ayuda (-h) y
# docs/produccion.md, seccion "Despliegue / actualización".

set -u

SCRIPT_NAME=$(basename "$0")

if [ $# -lt 2 ] || [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    echo "================================================================="
    echo " Odoo Module Updater — HELIPISTAS ERP 17"
    echo "================================================================="
    echo ""
    echo "Uso:"
    echo "  ./$SCRIPT_NAME <modulo> <entorno> [--install] [--stop] [--backup]"
    echo ""
    echo "Entornos:"
    echo "  dev  -> contenedor 'helipistas_odoo_17'  (docker/docker-compose.yml, local)"
    echo "  prod -> contenedor 'helipistas_odoo'     (dockerserver/, EC2 + EFS)"
    echo ""
    echo "Modos:"
    echo "  (por defecto)  El ERP sigue en marcha. El -u se ejecuta dentro del contenedor"
    echo "                 vivo. Al terminar, Odoo avisa a los workers por la secuencia"
    echo "                 base_registry_signaling y recargan solos: no hay que reiniciar."
    echo "                 Vale para cambios de solo XML: vistas, menus, informes, permisos."
    echo ""
    echo "  --install      Primera instalacion del modulo (-i en vez de -u). Un -u sobre"
    echo "                 un modulo que aun no esta instalado no hace nada: Odoo lo ignora."
    echo "                 Solo hace falta una vez; despues se actualiza en modo normal."
    echo ""
    echo "  --stop         Para el contenedor y actualiza en un clon efimero. Obligatorio"
    echo "                 cuando el modulo añade o quita campos: un ALTER TABLE necesita"
    echo "                 ACCESS EXCLUSIVE sobre la tabla y cualquier consulta viva lo"
    echo "                 cancela con 'canceling statement due to lock timeout'."
    echo "                 El ERP queda caido hasta que acabe."
    echo ""
    echo "  --backup       pg_dump antes de actualizar. NO es el comportamiento por defecto:"
    echo "                 tarda mucho en la base de produccion y ya hay copia diaria del"
    echo "                 EFS. Usalo solo para un cambio de esquema grande o irreversible."
    echo ""
    echo "Ejemplos:"
    echo "  ./$SCRIPT_NAME leulit_almacen dev"
    echo "  ./$SCRIPT_NAME leulit_ventas dev --install        # modulo nuevo, primera vez"
    echo "  ./$SCRIPT_NAME leulit_almacen prod                 # solo XML, sin cortar servicio"
    echo "  ./$SCRIPT_NAME leulit_operaciones prod --stop      # el modulo añade campos"
    echo "  ./$SCRIPT_NAME leulit_almacen prod --stop --backup"
    echo "================================================================="
    exit 1
fi

MODULO="$1"
ENTORNO="$2"
shift 2

PARAR=0
BACKUP_ANTES=0
INSTALAR=0
for arg in "$@"; do
    case "$arg" in
        --stop)    PARAR=1 ;;
        --backup)  BACKUP_ANTES=1 ;;
        --install) INSTALAR=1 ;;
        *) echo "❌ Opción '$arg' no reconocida. Usa --install, --stop y/o --backup."; exit 1 ;;
    esac
done

# -i para un modulo nuevo, -u para uno ya instalado. Odoo actualiza la lista de modulos
# al arrancar con -i/-u, asi que no hace falta un "Actualizar lista de aplicaciones" previo.
if [ "$INSTALAR" -eq 1 ]; then
    ACCION="-i"; VERBO="Instalando";   PARTICIPIO="instalado";   SUGERENCIA=" --install"
else
    ACCION="-u"; VERBO="Actualizando"; PARTICIPIO="actualizado"; SUGERENCIA=""
fi

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

echo "⏱️  $VERBO '$MODULO' en '$BASE' ($ENTORNO, contenedor $CONTENEDOR)..."
echo "-----------------------------------------------------------------"

# La salida no va a `docker logs` (ese solo captura el proceso principal del contenedor),
# asi que en los dos modos se guarda en $LOG o se pierde al cerrar la terminal.
if [ "$PARAR" -eq 1 ]; then
    # Un ALTER TABLE necesita ACCESS EXCLUSIVE sobre la tabla: con el Odoo que sirve
    # peticiones vivo, cualquier consulta abierta la bloquea y Postgres cancela el -u. Por
    # eso se para el contenedor y la actualizacion va en uno de usar y tirar clonado de el:
    # misma imagen, misma red, mismas variables y mismos volumenes (ahi esta /etc/odoo y
    # /mnt/extra-addons), sin publicar puertos.
    IMAGEN=$(docker inspect -f '{{.Image}}' "$CONTENEDOR")
    RED=$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' "$CONTENEDOR" | awk '{print $1}')
    ENV_FILE=$(mktemp)
    docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$CONTENEDOR" > "$ENV_FILE"

    # Pase lo que pase (error, Ctrl-C), el ERP tiene que volver a levantarse.
    trap 'rm -f "$ENV_FILE"; docker start "$CONTENEDOR" >/dev/null 2>&1' EXIT

    echo "⏸️  Parando '$CONTENEDOR': el ERP queda caido hasta que acabe el script."
    docker stop "$CONTENEDOR" >/dev/null

    docker run --rm --network "$RED" --env-file "$ENV_FILE" --volumes-from "$CONTENEDOR" \
        "$IMAGEN" odoo -d "$BASE" "$ACCION" "$MODULO" --no-http --stop-after-init 2>&1 | tee "$LOG"
    RESULTADO=${PIPESTATUS[0]}
else
    # Segundo proceso Odoo dentro del contenedor vivo. --no-http para que no pelee por el
    # puerto con el que esta sirviendo. Sin -t en el exec: un TTY rompe el pipe a tee.
    echo "▶️  El ERP sigue sirviendo peticiones; el -u va en un proceso aparte."
    docker exec -i "$CONTENEDOR" \
        odoo -d "$BASE" "$ACCION" "$MODULO" --no-http --stop-after-init 2>&1 | tee "$LOG"
    RESULTADO=${PIPESTATUS[0]}
fi

echo "-----------------------------------------------------------------"
echo "📄 Log: $LOG"

if [ "$RESULTADO" -ne 0 ]; then
    echo "❌ El comando terminó con error (código $RESULTADO). La base queda como estaba:"
    echo "   Odoo hace el -u en una transacción y la deshace entera si algo revienta."
    if grep -q "lock timeout" "$LOG"; then
        if [ "$PARAR" -eq 0 ]; then
            echo "   Es un bloqueo de Postgres. Este módulo toca el esquema (añade o quita"
            echo "   campos) y el ALTER TABLE no puede con el ERP en marcha. Repite con --stop:"
            echo "   ./$SCRIPT_NAME $MODULO $ENTORNO$SUGERENCIA --stop"
        else
            echo "   Es un bloqueo de Postgres aun con el ERP parado: alguien más tiene la tabla"
            echo "   cogida (Metabase, n8n, una sesión psql abierta). Míralo con:"
            echo "   docker exec -i $PSQL psql -U odoo -d $BASE -c \"select pid, state, query from pg_stat_activity where pid <> pg_backend_pid()\""
        fi
    fi
    [ -n "${BACKUP:-}" ] && echo "   Copia de seguridad en $BACKUP"
    [ "$PARAR" -eq 1 ] && echo "🔄 Arrancando '$CONTENEDOR' de nuevo..."
    exit "$RESULTADO"
fi

# Odoo puede acabar con código 0 y aun así haber tragado errores por el camino.
if grep -qiE "^.* (ERROR|CRITICAL) " "$LOG"; then
    echo "⚠️  Terminó con código 0 pero el log tiene líneas ERROR/CRITICAL:"
    grep -iE "^.* (ERROR|CRITICAL) " "$LOG" | head -20
    echo "   Revísalo antes de dar el despliegue por bueno."
fi

echo "✅ Módulo '$MODULO' $PARTICIPIO en $ENTORNO."

if [ "$PARAR" -eq 1 ]; then
    echo "🔄 Arrancando '$CONTENEDOR' con el registry nuevo..."
    docker start "$CONTENEDOR" >/dev/null && echo "   Hecho. Log: docker logs -f $CONTENEDOR"
else
    echo "   El ERP no se ha parado. Los workers recargan el registry solos en la siguiente"
    echo "   petición (base_registry_signaling); si algo no se refleja, F5 con caché limpia."
fi
