# Instalación en servidor (AWS EC2)

Este documento describe la instalación de producción del ERP en la instancia EC2 de AWS.

## Resumen

- **Orquestación:** Docker Compose
- **Almacenamiento persistente:** EFS montado en `/efs/HELIPISTAS-ODOO-17`
- **Definición de infraestructura en el repo:** [`dockerserver/`](../dockerserver) (`docker-compose.yml` + `Dockerfile`)

> `dockerserver/` es la configuración de **producción** (rutas `/efs/...`, nginx + certbot). No confundir con `docker/`, que es el entorno de desarrollo local (volúmenes Docker nombrados, sin nginx).

## Infraestructura AWS

- **Instancia EC2:** `erp.helipistas.com` (`54.228.16.152`), tipo `t3.medium`, región `eu-west-1` (AZ `eu-west-1b`). Security groups: consultar consola AWS, no versionados aquí.
- **Acceso SSH:** usuario `ec2-user`, key pair (`.pem`), directo a la IP anterior (sin bastion). La custodia de la clave privada no está documentada en este repo.
- **EFS:** `fs-ec7152d9` (`eu-west-1`), montaje directo por NFSv4.1 (sin access point) vía `/etc/fstab`:
  ```
  fs-ec7152d9.efs.eu-west-1.amazonaws.com:/ /efs nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport,_netdev 0 0
  ```
  `/efs/HELIPISTAS-ODOO-17/` es un subdirectorio de ese filesystem, montado en `/efs`; no hay un access point específico para él.
- **Backups:** plan de AWS Backup, diario, retención 7 días, sobre el EFS completo (cubre `postgres/` y `filestore/`).

## Ubicación de ficheros en el servidor

Todo el estado persistente vive en el EFS, bajo `/efs/HELIPISTAS-ODOO-17/`:

```
/efs/HELIPISTAS-ODOO-17/
├── docker-compose.yml                                    # copia desplegada de dockerserver/docker-compose.yml
├── postgres/                                              # datos de PostgreSQL (PGDATA)
├── odoo/
│   ├── conf/                                              # odoo.conf montado en /etc/odoo dentro del contenedor
│   ├── addons/
│   │   └── helipistas-erp-odoo-17/addons/                 # checkout de este repo (carpeta addons/) → /mnt/extra-addons
│   ├── filestore/                                         # ir.attachment / filestore de Odoo
│   └── sessiones/                                         # sesiones de usuario
├── nginx/
│   ├── conf/default.conf                                  # config de nginx (no versionada en el repo)
│   └── ssl/
├── certbot/
│   ├── www/                                                # webroot para el challenge HTTP-01
│   └── conf/                                               # certificados Let's Encrypt (/etc/letsencrypt)
```

## Contenedores

Definidos en [`dockerserver/docker-compose.yml`](../dockerserver/docker-compose.yml):

| Servicio | Imagen | Contenedor | Puertos | Descripción |
|---|---|---|---|---|
| `postgresOdoo16` | `postgres:15` | `helipistas_postgres` | `5432:5432` | Base de datos |
| `helipistas_odoo` | build local (`dockerserver/Dockerfile`, base `odoo:17.0`) | `helipistas_odoo` | `8069`, `8082`, `8072` | Odoo 17 |
| `nginx` | `nginx:latest` | `helipistas_nginx` | `80`, `443` | Proxy inverso / TLS |
| `certbot` | `certbot/certbot` | `helipistas_certbot` | — | Renovación automática de certificados (cada 12h) |
| `helipistas_n8n` | `helipistas/n8n:1.0.0` | `helipistas_n8n` | `5678` | Automatizaciones (n8n) — acceso directo por IP:5678, ver nota abajo |
| `metabase` | `metabase/metabase:latest` | `metabase_app` | `3000` | BI/analítica (Metabase) — acceso directo por IP:3000, ver nota abajo |

Todos los servicios comparten la red bridge `helipistas_network`.

### Imagen de Odoo (`dockerserver/Dockerfile`)

- Base: `odoo:17.0`
- Locale `es_ES.UTF-8` + fuentes `fonts-dejavu-core` (necesario para generación de PDFs/reports con caracteres en español)
- Paquetes Python adicionales: `pypdf`, `pyqrcode`, `pyotp`, `pypng`

### Variables de entorno del contenedor Odoo

Definidas directamente en `docker-compose.yml` (no hay `.env` en el repo para producción):

- `HOST=postgresOdoo16`, `USER=odoo`, `PASSWORD=<ver docker-compose.yml en el servidor>`
- `ODOO_LONGPOLLING_PORT=8072`
- `LANG=es_ES.UTF-8`, `LANGUAGE=es_ES:es`, `LC_ALL=es_ES.UTF-8`

> La contraseña de PostgreSQL está en claro en el `docker-compose.yml`. Pendiente de mover a secret/`.env` si se quiere endurecer.

## Addons

El volumen `/efs/HELIPISTAS-ODOO-17/odoo/addons/helipistas-erp-odoo-17/addons` en el servidor corresponde a la carpeta [`addons/`](../addons) de este repositorio (checkout de la rama desplegada), montado en `/mnt/extra-addons` dentro del contenedor.

Módulos propios: `leulit`, `leulit_actividad`, `leulit_almacen`, `leulit_calidad`, `leulit_camo`, `leulit_comercial`, `leulit_crm_team`, `leulit_encuestas`, `leulit_escuela`, `leulit_esignature`, `leulit_groups_manager`, `leulit_hide_menus`, `leulit_ia`, `leulit_meteo`, `leulit_nda`, `leulit_operaciones`, `leulit_parte_145`, `leulit_partis`, `leulit_planificacion`, `leulit_seguridad`, `leulit_taller`, `leulit_tarea`, `leulit_trabajador_externo`, `leulit_user_impersonate`, más `maintenance_equipment_changes` y `third-party-addons/`.

## Configuración de Odoo (`odoo.conf`)

`/efs/HELIPISTAS-ODOO-17/odoo/conf/odoo.conf` (no versionado en el repo, montado en `/etc/odoo` dentro del contenedor):

```ini
[options]
# Database settings
db_host = postgresOdoo16
db_port = 5432
db_user = odoo
db_password = <ver odoo.conf en el servidor>
db_template = template0
db_name = productiu
dbfilter = ^productiu$

# Server settings
http_port = 8069
longpolling-port = 8072
workers = 2
max_cron_threads = 1
admin_passwd = <ver odoo.conf en el servidor>   # password maestro: NO versionar
lang = es_ES.UTF-8

# File paths
addons_path = /mnt/extra-addons,/mnt/extra-addons/third-party-addons,/usr/lib/python3/dist-packages/odoo/addons
data_dir = /var/lib/odoo

# Logging
log_level = info
log_handler = :INFO

# Security
list_db = True

# Performance
limit_memory_hard = 1677721600
limit_memory_soft = 1342177280
limit_request = 8192
limit_time_cpu = 600
limit_time_real = 1200

# Proxy mode (for Nginx)
proxy_mode = True

# Session
session_dir = /var/lib/odoo/sessions
```

`proxy_mode = True` es obligatorio con nginx delante (hace que Odoo confíe en `X-Forwarded-*` en vez de en la conexión directa). `workers = 2` + 1 gunicorn/master implica como mucho 2 requests HTTP concurrentes reales (más cron/longpolling aparte); revisar si da para el pico de uso actual.

**⚠️ Riesgo pendiente:** `admin_passwd` (contraseña maestra que protege `/web/database/manager` — crear/duplicar/restaurar/eliminar bases de datos) está en claro en el fichero y es la **misma** que `db_password`. Además `list_db = True` deja el listado/gestor de bases de datos accesible. `dbfilter` limita lo que se ve en el selector de login, pero no bloquea `/web/database/manager` en sí. Pendiente: `admin_passwd` distinta y fuerte (o vacía + `list_db = False` si el manager no se usa en producción), y mover credenciales a secret/`.env` (mismo pendiente ya anotado para `db_password` en la sección de variables de entorno).

## nginx: dominios servidos

`nginx/conf/default.conf` (no versionado en el repo) solo tiene virtual host para `erp.helipistas.com`, con redirect HTTP→HTTPS y proxy a Odoo (`8069`) + websocket (`8072`):

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name erp.helipistas.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS configuration with Let's Encrypt
server {
    listen 443 ssl;
    server_name erp.helipistas.com;

    client_max_body_size 100M;

    ssl_certificate /etc/letsencrypt/live/erp.helipistas.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/erp.helipistas.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    add_header Strict-Transport-Security "max-age=63072000" always;

    location / {
        proxy_pass http://helipistas_odoo:8069;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_connect_timeout 720s;
        proxy_send_timeout 720s;
        proxy_read_timeout 720s;
    }

    location /websocket {
        proxy_pass http://helipistas_odoo:8072;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    location ~* /web/static/ {
        proxy_pass http://helipistas_odoo:8069;
        proxy_cache_valid 200 60m;
        proxy_buffering on;
        expires 864000;
    }
}
```

`erp17.helipistas.com` no tiene virtual host propio pese a estar mencionado como dominio de la app en otros sitios del repo/histórico.

**⚠️ Riesgo pendiente:** `helipistas_n8n` (env `N8N_HOST=n8n.helipistas.com`, `WEBHOOK_URL=https://n8n.helipistas.com/`) y `metabase` (`MB_SITE_URL=https://metabase.helipistas.com`) están configurados como si fueran a exponerse por nginx con dominio y TLS, pero en la práctica se acceden hoy directamente por `http://54.228.16.152:5678` y `http://54.228.16.152:3000` — HTTP plano, sin certificado, con el puerto abierto en el security group. Pendiente: darles virtual host + TLS en nginx (y cerrar el puerto directo), o al menos ajustar esas env vars a la realidad actual.

## Certificados TLS: renovación y recarga de nginx

El contenedor `certbot` renueva el certificado de `erp.helipistas.com` cada 12h (`certbot renew` en bucle, ver entrypoint en `dockerserver/docker-compose.yml`); no hay certificados emitidos para `erp17.helipistas.com` ni `metabase.helipistas.com` (ver riesgo pendiente arriba). Certbot **no lleva `--deploy-hook`**: al renovar solo actualiza los ficheros en `/efs/HELIPISTAS-ODOO-17/certbot/conf`, no le avisa a nginx. nginx solo lee el certificado al arrancar o al recargar (`nginx -s reload`), así que si el contenedor `helipistas_nginx` lleva mucho tiempo sin reiniciarse, sigue sirviendo el certificado **viejo** aunque haya uno nuevo válido en disco.

Esto causó una caída real: el 2026-08-03, con `helipistas_nginx` con 5 meses de uptime sin recargar, el certificado servido (emitido el 2026-05-05, válido 90 días) caducó mientras el certificado ya renovado en disco (válido hasta 2026-10-02) esperaba sin usarse → `ERR_CERT_DATE_INVALID` en el navegador de los usuarios, pese a que `docker exec helipistas_certbot certbot certificates` mostraba el certificado en regla.

**Diagnóstico** (repetible ante cualquier aviso de certificado):
```bash
# Certificado que certbot tiene en disco (fuente de verdad)
docker exec helipistas_certbot certbot certificates

# Certificado que nginx está sirviendo de verdad ahora mismo (desde fuera, con openssl moderno, NO desde el propio EC2 que tiene uno antiguo)
echo | openssl s_client -connect erp.helipistas.com:443 -servername erp.helipistas.com 2>/dev/null | openssl x509 -noout -dates
```
Si las fechas no coinciden, nginx necesita recargar.

**Arreglo inmediato** (sin downtime, no reinicia el contenedor):
```bash
docker exec helipistas_nginx nginx -s reload
```

**Arreglo estructural**: como `certbot` y `nginx` son contenedores separados sin socket de Docker compartido, no hay `--deploy-hook` directo. Se ha añadido un cron en el host (fuera del repo, en el crontab de root de la instancia EC2) que recarga nginx una vez al mes, con margen de sobra frente a la ventana de renovación de Let's Encrypt (~30 días antes de caducar):
```bash
0 3 1 * * docker exec helipistas_nginx nginx -s reload
```

## Despliegue / actualización

Desde el servidor, dentro de `/efs/HELIPISTAS-ODOO-17/`:

```bash
# actualizar código (repo desplegado dentro de odoo/addons/helipistas-erp-odoo-17)
cd odoo/addons/helipistas-erp-odoo-17
git pull

# reconstruir imagen de Odoo si cambió el Dockerfile o requirements
cd /efs/HELIPISTAS-ODOO-17
docker-compose build helipistas_odoo

# recrear contenedores
docker-compose up -d
```

> El servidor tiene el binario legacy `docker-compose` (con guion), no el plugin v2 `docker compose`.

### Si el cambio toca modelos, vistas, permisos o datos de un módulo

`git pull` + `up -d` **no basta**: Odoo solo crea columnas y carga los ficheros XML durante un
`-u`/`-i`. En un arranque normal se salta `init_models`, así que un campo nuevo queda en el
registry sin columna en la base de datos y la primera lectura revienta con `UndefinedColumn`.

```bash
# 1. parar el Odoo que sirve peticiones. No es opcional: un ALTER TABLE necesita ACCESS
#    EXCLUSIVE y cualquier consulta viva sobre la tabla cancela el -u con
#    "canceling statement due to lock timeout".
docker stop helipistas_odoo

# 2. actualizar en un contenedor de usar y tirar clonado del parado (misma imagen, red,
#    variables y volúmenes), guardando la salida
docker run --rm --network helipistas-odoo-17_helipistas_network \
  --volumes-from helipistas_odoo \
  -e HOST=postgresOdoo16 -e USER=odoo -e PASSWORD=<ver docker-compose.yml> \
  <imagen de helipistas_odoo> odoo -d productiu -u <modulo> --no-http --stop-after-init 2>&1 \
  | tee /efs/HELIPISTAS-ODOO-17/upd-<modulo>-$(date +%F-%H%M).log

# 3. arrancar de nuevo
docker start helipistas_odoo
docker logs -f helipistas_odoo
```

Si Postgres cancela el paso 2 por bloqueo aun con el ERP parado, hay otro cliente con la tabla
cogida (Metabase, n8n, una sesión `psql` abierta):

```bash
docker exec -i helipistas_postgres psql -U odoo -d productiu \
  -c "select pid, state, query from pg_stat_activity where pid <> pg_backend_pid()"
```

O directamente `./upd_module.sh <modulo> prod` desde el checkout, que hace los tres pasos
(y saca la red, la imagen y las variables del propio contenedor) y avisa si el log trae
`ERROR`/`CRITICAL`.

**Copia de seguridad:** no se hace en cada actualización. La base de producción es grande y un
`pg_dump` tarda demasiado para ponerlo en el camino habitual; el respaldo de referencia es la
copia diaria del EFS. Para un cambio de esquema que no quieras arriesgar, `--backup` fuerza el
volcado antes de actualizar:

```bash
./upd_module.sh <modulo> prod --backup
```

Ojo con lo que cubre cada cosa: la copia del EFS es a nivel de sistema de ficheros sobre un
Postgres en marcha, así que es *crash-consistent* — se restaura como si se hubiera ido la luz,
y Postgres reconstruye con el WAL. Un `pg_dump` es un volcado lógico consistente. Para el día
a día la del EFS vale; para una migración de datos, mejor el dump.

El contenedor de producción es `helipistas_odoo`, no `helipistas_odoo_17` (ese es el de
desarrollo local). La base de datos es `productiu`.

El ERP está caído entre el paso 1 y el 3, así que esto se hace cuando no hay nadie
trabajando. `upd_module.sh` arranca el contenedor pase lo que pase (`trap`), también si el
`-u` falla o si cortas con Ctrl-C.

Si el `-u` falla, la base queda como estaba: Odoo lo hace todo en una transacción y la
deshace entera.

### Cómo verificar que un módulo se actualizó de verdad

No hay ningún fichero que lo diga: el estado del módulo está en la base de datos. En disco
solo puedes confirmar que **el código llegó**, que es otra cosa.

```bash
# el código llegó y el contenedor lo ve (el fallo típico es hacer git pull en otro directorio)
cd /efs/HELIPISTAS-ODOO-17/odoo/addons/helipistas-erp-odoo-17 && git log -1 --oneline
docker exec helipistas_odoo ls -l /mnt/extra-addons/<modulo>/

# el log del paso 2: 0 líneas con ERROR/CRITICAL y un "Modules loaded." al final
grep -iE "error|critical|traceback" /efs/HELIPISTAS-ODOO-17/upd-<modulo>-*.log
```

La comprobación que de verdad vale es en la base de datos: si los xmlid del módulo existen,
sus ficheros de datos se cargaron.

```bash
docker exec -i helipistas_postgres psql -U odoo -d productiu -c \
  "SELECT module, name, write_date FROM ir_model_data
    WHERE module = '<modulo>' ORDER BY write_date DESC LIMIT 10;"
```

Un `write_date` reciente en esas filas = el `-u` pasó por ahí. Para un campo nuevo, además:

```bash
docker exec -i helipistas_postgres psql -U odoo -d productiu -c \
  "SELECT column_name FROM information_schema.columns
    WHERE table_name = 'stock_lot' AND column_name = 'fecha_inventario';"
```

Cero filas = el código está en disco pero el módulo **no** se actualizó.

No hay pipeline de CI/CD: el repo no tiene `.github/workflows/` ni scripts de despliegue. El `git pull` + `docker-compose build` + `docker-compose up -d` de arriba se ejecuta a mano en el servidor.

## Pendiente

- Exponer `n8n.helipistas.com` y `metabase.helipistas.com` por nginx con TLS y cerrar el acceso directo por IP:puerto (ver riesgo en la sección de nginx).
- `admin_passwd` de Odoo: distinta de `db_password` y fuerte, o desactivar `list_db` si el gestor de BD no se usa en producción (ver riesgo en la sección de `odoo.conf`).
- Security groups de la EC2: no versionados aquí, consultar consola AWS.
- Custodia de la clave SSH del equipo: no documentada aquí por decisión explícita.
