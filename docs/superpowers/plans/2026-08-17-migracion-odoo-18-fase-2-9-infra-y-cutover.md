# Migración Odoo 18 — Fases 2 a 8: stacks, preproducción y cutover de 24 h

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development o superpowers:executing-plans. Los pasos usan checkbox (`- [ ]`).

**Goal:** reorganizar el servidor en cuatro stacks con Traefik como proxy único, levantar preproducción Odoo 18 en la misma instancia, y ejecutar el cutover en menos de 24 h con rollback probado.

**Prerrequisito:** el plan de Fases 0-1 cumplido, en particular que los 28 módulos custom instalen en Odoo 18.

**Tech Stack:** EC2 `t3.xlarge` + EFS, Docker Compose v2, Traefik v3, Portainer CE con git-backed stacks, PostgreSQL 15, Odoo 18.0, OpenUpgrade 18.0, `odoo-bin neutralize`.

## Decisiones tomadas por el usuario

| Decisión | Elegido |
|---|---|
| Ubicación de preproducción | **Misma instancia**, contenedores y stacks separados |
| Gestión | **Portainer** con stacks, respaldados en git |
| Proxy | **Traefik** sustituye a nginx |
| Dimensionado | **`t3.xlarge`** (4 vCPU / 16 GB), todo encendido |
| PostgreSQL | **Uno por stack** |
| n8n y Metabase | **Stack `herramientas` aparte** |
| Metabase | **En el alcance:** es el frontend de KPIs y sus consultas deben seguir funcionando |

Cuatro stacks: `infra` (Traefik + Portainer), `produccion` (Odoo 17 + PG 15), `preproduccion` (Odoo 18 + PG 15), `herramientas` (n8n + Metabase).

**Traefik hace ACME dentro del proxy y sirve el certificado renovado sin recargar.** Eso elimina la causa de la caída del 2026-08-03 documentada en `produccion.md` (nginx 5 meses sin recargar sirviendo un certificado caducado, sin `--deploy-hook` posible entre contenedores separados), y con ella los contenedores `nginx` y `certbot` y el cron mensual del apaño.

**Portainer se usa con stacks desde git, no autorando el compose en su UI**, porque hoy `default.conf` y `odoo.conf` no están versionados y hacerlo en la UI repite el problema. Portainer tiene el socket de Docker (root en el host): va detrás de Traefik con TLS y restringido por IP.

**El cambio de proxy va antes del cutover**, sobre la producción de 17: es reversible en un minuto y evita no saber si un fallo de TLS dentro de la ventana es del proxy o de la migración.

## Global Constraints

- **Los dos entornos completos tienen que poder correr a la vez** — Odoo 17 + su PostgreSQL + su Metabase, y Odoo 18 + su PostgreSQL + su Metabase — para verificar la migración comparando lado a lado. Es criterio de aceptación, no una comodidad.
- **El Metabase de producción no se toca.** Ni fuente de datos nueva, ni red nueva, ni colecciones duplicadas. Sigue mostrando lo que muestra hoy contra Odoo 17. Lo que apunta al 18 es una instancia aparte.
- **Producción siempre gana bajo contención:** `cpu_shares` 2048 frente a 512, y tope duro de `cpus` en preproducción.
- **Producción sigue viva y cambiando** (datos y módulos custom) durante todo el proyecto. La Fase 7 existe para eso.
- **Ventana máxima: 24 h**, con puertas de decisión. Si una fase supera en más del 50 % su tiempo de ensayo, se aborta y se revierte.
- **Preproducción se neutraliza siempre. Producción JAMÁS** — la dejaría sin correo saliente ni crons.
- **Nada de credenciales en git.** `.env` fuera del repo.
- **`/efs/HELIPISTAS-ODOO-17/` no se toca en ningún momento.** Es el rollback.
- El servidor tiene `docker-compose` legacy (con guion); los ficheros de este plan usan el plugin v2 (`docker compose`). No mezclar en los runbooks.
- **`leulit_almacen` exige un `res_company` con `id=2`.**
- Antes de cualquier ventana, **backup EFS bajo demanda**: el plan diario de AWS Backup no basta.

## File Structure

| Fichero | Responsabilidad |
|---|---|
| `stacks/infra/docker-compose.yml` + `traefik/traefik.yml` + `traefik/dinamico.yml` | Traefik + Portainer. Único dueño de 80/443 |
| `stacks/produccion/docker-compose.yml` + `odoo.conf` | Odoo 17 + PG 15, sin nginx ni certbot |
| `stacks/preproduccion/docker-compose.yml` + `Dockerfile` + `odoo.conf` | Odoo 18 + PG 15, con límites reducidos |
| `stacks/herramientas/docker-compose.yml` | n8n + Metabase con dominio y TLS |
| `stacks/*/.env.example` | Plantillas. Los `.env` reales no van a git |
| `tools/migracion18/dump_produccion.sh` | `pg_dump` con verificación |
| `tools/migracion18/restore_preproduccion.sh` | Restaura en el PG de preproducción |
| `tools/migracion18/copiar_filestore.sh` | Copia del filestore: enlaces duros o rsync |
| `tools/migracion18/neutralizar_preproduccion.sh` | `neutralize` + comprobación de que nada sale |
| `tools/migracion18/migrar_17_a_18.sh` | Orquesta OpenUpgrade cronometrando cada fase |
| `tools/migracion18/verificar_migracion.py` | Compara recuentos por tabla origen vs destino |
| `tools/migracion18/metabase_exportar.sh` | Exporta preguntas por la API de Metabase |
| `tools/migracion18/metabase_analizar.py` | Cruza consultas con los cambios de esquema de OpenUpgrade |
| `addons/leulit/models/mail_mail.py` + `tests/test_neutralizacion_correo.py` | Cancela envíos si la base está neutralizada |
| `addons/leulit_ia/data/neutralize.sql`, `addons/leulit_meteo/data/neutralize.sql` | Cortan las llamadas a servicios externos |
| `docs/migracion-odoo-18-metabase.md` | Preguntas afectadas, veredicto y arreglo |
| `docs/metabase/consultas/*.sql` | SQL nativo versionado — Metabase no versiona nada |
| `docs/cutover-runbook.md` | Runbook con tiempos medidos y puertas |

### Redes Docker

- **`helipistas_proxy`** (externa): Traefik y todo lo publicado. Único contacto entre stacks.
- **`produccion_datos`** (externa): PG de producción, Odoo 17 y **Metabase** — que consulta SQL contra el esquema de Odoo y necesita alcanzarlo.
- **`preproduccion_datos`** (interna al stack): PG 18 y Odoo 18. Deliberadamente no alcanzable desde producción ni Metabase.

### Los dos entornos completos, en marcha a la vez

**Requisito:** tiene que poder ejecutarse **producción y preproducción simultáneamente**, cada una con su Odoo, su PostgreSQL y su Metabase, para poder verificar la migración comparando lado a lado.

| | Producción (Odoo 17) | Preproducción (Odoo 18) |
|---|---|---|
| PostgreSQL | `helipistas_postgres` → `/efs/HELIPISTAS-ODOO-17/postgres/pgdata` | `helipistas18_postgres` → `/efs/HELIPISTAS-ODOO-18/postgres/pgdata` |
| Odoo | `helipistas_odoo` → `erp.helipistas.com` | `helipistas18_odoo` → `${DOMINIO_PRE}` |
| Metabase | `metabase_app` → `metabase.helipistas.com` | `metabase_pre` → `${DOMINIO_METABASE_PRE}` |
| Red de datos | `produccion_datos` | `preproduccion_datos` |

Compartidos: `traefik`, `portainer`. **n8n sólo en producción**: clonarlo dispararía las automatizaciones por duplicado contra sistemas reales, así que sus workflows se prueban a mano contra preproducción (Task 14 paso 3).

Nada se solapa: PGDATA distintos, redes distintas, dominios distintos, contenedores con nombres distintos.

### Reparto de recursos en 16 GB

| Contenedor | `mem_limit` | `cpus` | `cpu_shares` |
|---|---|---|---|
| `traefik` | 256m | — | 1024 |
| `portainer` | 512m | — | 1024 |
| `pg_produccion` | 2500m | — | 2048 |
| `odoo17_produccion` | 2500m | — | 2048 |
| `metabase_app` (producción) | 2048m | — | 1024 |
| `n8n` | 512m | — | 512 |
| `pg_preproduccion` | 2500m | 2.0 | 512 |
| `odoo18_preproduccion` | 1500m | 2.0 | 512 |
| `metabase_pre` | 1536m (`-Xmx1g`) | 1.0 | 512 |
| **Suma de topes** | **≈14,0 GB** | | |

Quedan ~2 GB para sistema, Docker y la caché de página del kernel, de la que depende el rendimiento de PostgreSQL. **Es holgura ajustada**, y son topes, no reservas: los nueve no pican a la vez.

Dos palancas si aprieta, sin renunciar al requisito de que ambos entornos puedan convivir:

- Parar `metabase_pre` durante `pg_restore` y OpenUpgrade, que es cuando más hambre hay y menos falta hace: libera 1,5 GB con un botón en Portainer.
- Bajar `metabase_pre` a `1g` con `-Xmx768m` si sólo se usa para comparar cifras.

Si al medir (Task 1) resulta que la holgura real no llega, **la decisión de subir de instancia es del usuario**: aquí sólo están los números.

> **El `limit_memory_hard` de `odoo.conf` tiene que quedar por debajo del `mem_limit` del contenedor.** Si no, el kernel mata el contenedor antes de que Odoo aplique su límite, y en el log sólo queda un `Exited (137)`.

---

## FASE 2 — Preparar la instancia

### Task 1: Medir antes de tocar

**Files:** Modify `docs/migracion-odoo-18-hallazgos.md`

- [ ] **Step 1: Consumo real actual**

La tabla de reparto es estimación; estos son los datos.

```bash
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}'
free -h
nproc
```

- [ ] **Step 2: Tamaño de BD y filestore**

Determina el tiempo de `pg_dump`/`pg_restore`, que es el corazón del presupuesto de 24 h.

```bash
docker exec helipistas_postgres psql -U odoo -d productiu \
  -c "SELECT pg_size_pretty(pg_database_size('productiu'));"

docker exec helipistas_postgres psql -U odoo -d productiu -c "
SELECT relname, pg_size_pretty(pg_total_relation_size(c.oid)) AS total
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname='public' AND c.relkind='r'
 ORDER BY pg_total_relation_size(c.oid) DESC LIMIT 15;"

du -sh /efs/HELIPISTAS-ODOO-17/odoo/filestore/
find /efs/HELIPISTAS-ODOO-17/odoo/filestore/ -type f | wc -l   # esperado ~83.291
df -h /efs
```

- [ ] **Step 3: Throughput de EFS**

```bash
dd if=/dev/zero of=/efs/prueba.bin bs=1M count=2048 oflag=direct status=progress
rm -f /efs/prueba.bin
```

Y en CloudWatch, **`BurstCreditBalance`** de `fs-ec7152d9`. Si el EFS está en modo *Bursting* y el crédito va justo, un `pg_restore` puede agotarlo en mitad de la ventana. Pasar a *Elastic* tiene coste: es decisión del usuario.

- [ ] **Step 4: Anotar y commit**

```bash
git add docs/migracion-odoo-18-hallazgos.md
git commit -m "docs: medición de recursos, tamaño de BD/filestore y throughput de EFS"
```

---

### Task 2: IP fija antes de redimensionar

**Al parar una EC2 para cambiar de tipo, la IP pública cambia** si no es Elastic IP. `produccion.md` da `erp.helipistas.com (54.228.16.152)` pero no dice si lo es.

- [ ] **Step 1: Comprobarlo**

```bash
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 60")
curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id
curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4

aws ec2 describe-addresses --query 'Addresses[].{IP:PublicIp,Instancia:InstanceId}' --output table
```

Si `54.228.16.152` no aparece en `describe-addresses`, es IP normal y se pierde al parar.

- [ ] **Step 2: Asignar Elastic IP si no la hay**

```bash
aws ec2 allocate-address --domain vpc
aws ec2 associate-address --instance-id <i-xxxx> --allocation-id <eipalloc-xxxx>
```

> Asociar una Elastic IP a una instancia en marcha **cambia su IP pública en ese momento**: hay que actualizar el DNS y esperar propagación antes de seguir. Bajar el TTL a 60 s con 24-48 h de antelación.

- [ ] **Step 3: Verificar**

```bash
dig +short erp.helipistas.com
curl -o /dev/null -s -w '%{http_code}\n' https://erp.helipistas.com/web/login
```

- [ ] **Step 4: Documentar y commit**

Añadir la Elastic IP y su `allocation-id` a `docs/produccion.md`, o el siguiente que redimensione repite el problema.

```bash
git add docs/produccion.md
git commit -m "docs: Elastic IP de producción, requisito para redimensionar sin romper DNS"
```

---

### Task 3: Redimensionar a `t3.xlarge` y poner Compose v2

Ventana corta: parar, cambiar tipo, arrancar. El estado está en EFS, no se mueve nada.

- [ ] **Step 1: Backup bajo demanda**

```bash
aws backup start-backup-job --backup-vault-name <vault> \
  --resource-arn arn:aws:elasticfilesystem:eu-west-1:<cuenta>:file-system/fs-ec7152d9 \
  --iam-role-arn <rol>
```

- [ ] **Step 2: Parada ordenada**

```bash
cd /efs/HELIPISTAS-ODOO-17
docker-compose down          # binario legacy: es el que hay hoy
aws ec2 stop-instances --instance-ids <i-xxxx>
aws ec2 wait instance-stopped --instance-ids <i-xxxx>
```

- [ ] **Step 3: Cambiar tipo y arrancar**

```bash
aws ec2 modify-instance-attribute --instance-id <i-xxxx> --instance-type t3.xlarge
aws ec2 start-instances --instance-ids <i-xxxx>
aws ec2 wait instance-running --instance-ids <i-xxxx>
```

- [ ] **Step 4: Comprobar recursos y montaje de EFS**

```bash
nproc            # esperado: 4
free -h          # esperado: ~16 Gi
df -h /efs && mount | grep efs
```

> Si `/efs` no monta, **no arrancar nada**: los bind mounts crearían directorios vacíos sobre el punto de montaje y Odoo levantaría sin filestore.

- [ ] **Step 5: Instalar el plugin Compose v2**

```bash
sudo yum install -y docker-compose-plugin || {
  DEST=/usr/libexec/docker/cli-plugins
  sudo mkdir -p "$DEST"
  sudo curl -sSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
    -o "$DEST/docker-compose"
  sudo chmod +x "$DEST/docker-compose"
}
docker compose version      # sin guion
```

- [ ] **Step 6: Levantar producción y confirmar**

```bash
cd /efs/HELIPISTAS-ODOO-17 && docker-compose up -d
curl -o /dev/null -s -w '%{http_code}\n' https://erp.helipistas.com/web/login
```

- [ ] **Step 7: Subir los workers de producción**

`produccion.md` anota que `workers = 2` «implica como mucho 2 requests concurrentes reales; revisar si da para el pico». Con 4 vCPU, 4 workers es razonable. Editar `/efs/HELIPISTAS-ODOO-17/odoo/conf/odoo.conf`, `docker-compose restart helipistas_odoo`, y comprobar con `docker stats`.

- [ ] **Step 8: Commit**

```bash
git add docs/produccion.md
git commit -m "docs: instancia redimensionada a t3.xlarge, Compose v2 y workers=4"
```

---

### Task 4: Estructura en EFS y redes

- [ ] **Step 1: Directorios**

```bash
sudo mkdir -p /efs/HELIPISTAS-INFRA/{traefik,portainer}
sudo mkdir -p /efs/HELIPISTAS-ODOO-18/{postgres,odoo/{conf,filestore,sessiones},openupgrade}
sudo mkdir -p /efs/HELIPISTAS-HERRAMIENTAS/{n8n,metabase}
sudo mkdir -p /efs/dumps

sudo touch /efs/HELIPISTAS-INFRA/traefik/acme.json
sudo chmod 600 /efs/HELIPISTAS-INFRA/traefik/acme.json
```

> `acme.json` en 600 o Traefik no arranca. Contiene claves privadas: no va a git.

- [ ] **Step 2: Redes externas**

```bash
docker network create helipistas_proxy
docker network create produccion_datos
docker network ls | grep -E 'helipistas_proxy|produccion_datos'
```

- [ ] **Step 3: Clonar el repo para la rama 18**

```bash
sudo git clone -b migracion-odoo-18 <url-del-repo> \
  /efs/HELIPISTAS-ODOO-18/odoo/addons/helipistas-erp-odoo-18
```

- [ ] **Step 4: Verificar si EFS soporta enlaces duros**

Decide si el filestore se copia en minutos o en horas (Task 11).

```bash
cd /efs/dumps && echo prueba > a.txt && ln a.txt b.txt \
  && [ "$(stat -c %h a.txt)" = "2" ] && echo "ENLACES DUROS: OK" || echo "ENLACES DUROS: NO"
rm -f a.txt b.txt
```

Anotar el resultado en la bitácora.

---

## FASE 3 — Stacks `infra`, `produccion` y `herramientas`

### Task 5: Traefik y Portainer

**Files:** Create `stacks/infra/docker-compose.yml`, `traefik/traefik.yml`, `traefik/dinamico.yml`, `.env.example`

- [ ] **Step 1: Config estática**

`stacks/infra/traefik/traefik.yml`:

```yaml
api:
  dashboard: true

entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
  websecure:
    address: ":443"
    http:
      middlewares:
        - seguridad@file

providers:
  docker:
    exposedByDefault: false     # nada se publica salvo que lo pida con etiquetas
    network: helipistas_proxy
  file:
    filename: /etc/traefik/dinamico.yml

certificatesResolvers:
  le:
    acme:
      email: "{{ env \"ACME_EMAIL\" }}"
      storage: /acme/acme.json
      httpChallenge:
        entryPoint: web

log:
  level: INFO
accessLog: {}
```

`stacks/infra/traefik/dinamico.yml`:

```yaml
http:
  middlewares:
    seguridad:
      headers:
        stsSeconds: 63072000          # equivalente al HSTS que ponía nginx
        stsIncludeSubdomains: false
        contentTypeNosniff: true
        frameDeny: false              # Odoo usa iframes propios: no bloquear
    solo-oficina:
      ipAllowList:
        sourceRange:
          - "0.0.0.0/32"              # AJUSTAR al rango real antes de desplegar
```

- [ ] **Step 2: El stack**

`stacks/infra/docker-compose.yml`:

```yaml
services:
  traefik:
    image: traefik:v3.1
    container_name: helipistas_traefik
    restart: unless-stopped
    mem_limit: 256m
    cpu_shares: 1024
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik/traefik.yml:/etc/traefik/traefik.yml:ro
      - ./traefik/dinamico.yml:/etc/traefik/dinamico.yml:ro
      - /efs/HELIPISTAS-INFRA/traefik/acme.json:/acme/acme.json
    environment:
      - ACME_EMAIL=${ACME_EMAIL}
    networks: [helipistas_proxy]
    logging:
      driver: json-file
      options: {max-size: "10m", max-file: "3"}

  portainer:
    image: portainer/portainer-ce:latest
    container_name: helipistas_portainer
    restart: unless-stopped
    mem_limit: 512m
    cpu_shares: 1024
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /efs/HELIPISTAS-INFRA/portainer:/data
    networks: [helipistas_proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.portainer.rule=Host(`${DOMINIO_PORTAINER}`)
      - traefik.http.routers.portainer.entrypoints=websecure
      - traefik.http.routers.portainer.tls.certresolver=le
      - traefik.http.services.portainer.loadbalancer.server.port=9000
      # Portainer manda sobre el socket de Docker = root en el host
      - traefik.http.routers.portainer.middlewares=solo-oficina@file
    logging:
      driver: json-file
      options: {max-size: "10m", max-file: "3"}

networks:
  helipistas_proxy:
    external: true
```

`stacks/infra/.env.example`:

```dotenv
ACME_EMAIL=sistemas@helipistas.com
DOMINIO_PORTAINER=portainer.helipistas.com
```

- [ ] **Step 3: Ventana corta — parar nginx y levantar Traefik**

nginx tiene 80/443 y hay que liberarlos.

```bash
docker stop helipistas_nginx helipistas_certbot
cd /efs/HELIPISTAS-ODOO-18/odoo/addons/helipistas-erp-odoo-18/stacks/infra
cp .env.example .env && "${EDITOR:-vi}" .env
docker compose up -d
docker logs helipistas_traefik 2>&1 | grep -iE 'error|acme|certificate' | tail -20
```

Todavía no hay router para Odoo (eso es la Task 6): `erp.helipistas.com` dará 404 de Traefik. Es lo esperado.

**Rollback (menos de un minuto):**

```bash
docker compose down && docker start helipistas_nginx helipistas_certbot
```

- [ ] **Step 4: Cerrar Portainer por IP**

```bash
curl -s https://checkip.amazonaws.com     # el /32 para dinamico.yml
```

Poner el rango real en `solo-oficina`, `docker compose up -d`, y comprobar desde fuera que da **403**:

```bash
curl -o /dev/null -s -w '%{http_code}\n' "https://${DOMINIO_PORTAINER}/"
```

- [ ] **Step 5: Commit**

```bash
git add stacks/infra/
git commit -m "infra: stack Traefik + Portainer, sustituye nginx+certbot"
```

---

### Task 6: Stack `produccion` detrás de Traefik

**Files:** Create `stacks/produccion/docker-compose.yml`, `odoo.conf`, `.env.example`

- [ ] **Step 1: Versionar `odoo.conf` sin secretos**

```bash
cp /efs/HELIPISTAS-ODOO-17/odoo/conf/odoo.conf stacks/produccion/odoo.conf
```

Cambios respecto al de hoy:

- Quitar `db_password` y `admin_passwd` → entran por entorno.
- `workers = 4` (había 2).
- `limit_memory_hard` por debajo del `mem_limit` de 2500m.
- Mantener `proxy_mode = True`: sigue habiendo proxy delante.
- **Evaluar `list_db = False`.** Hoy está en `True` y deja `/web/database/manager` accesible, con `admin_passwd` igual a `db_password`. Riesgo abierto en `produccion.md`.

- [ ] **Step 2: El stack**

```yaml
services:
  pg_produccion:
    image: postgres:15
    container_name: helipistas_postgres
    restart: unless-stopped
    mem_limit: 2500m
    cpu_shares: 2048
    environment:
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=postgres
      - PGDATA=/var/lib/postgresql/data/pgdata
    volumes:
      # OJO: se monta en /var/lib/postgresql/data, NO en .../data/pgdata.
      # El cluster real vive en /efs/HELIPISTAS-ODOO-17/postgres/pgdata, tal como
      # lo dejó dockerserver/docker-compose.yml. Montarlo un nivel más abajo hace
      # que PGDATA apunte al directorio padre, postgres lo vea no vacío (contiene
      # `pgdata`) y se niegue a arrancar.
      - /efs/HELIPISTAS-ODOO-17/postgres:/var/lib/postgresql/data
    networks: [produccion_datos]
    logging:
      driver: json-file
      options: {max-size: "10m", max-file: "3"}

  odoo17:
    build:
      context: ../../dockerserver
    image: helipistas/odoo:17.0
    container_name: helipistas_odoo
    restart: unless-stopped
    mem_limit: 2500m
    cpu_shares: 2048
    depends_on: [pg_produccion]
    environment:
      - HOST=pg_produccion
      - USER=odoo
      - PASSWORD=${POSTGRES_PASSWORD}
      - ADMIN_PASSWD=${ODOO_ADMIN_PASSWD}
      - LANG=es_ES.UTF-8
      - LANGUAGE=es_ES:es
      - LC_ALL=es_ES.UTF-8
    volumes:
      - ./odoo.conf:/etc/odoo/odoo.conf:ro
      - /efs/HELIPISTAS-ODOO-17/odoo/addons/helipistas-erp-odoo-17/addons:/mnt/extra-addons
      - /efs/HELIPISTAS-ODOO-17/odoo/filestore:/var/lib/odoo/filestore
      - /efs/HELIPISTAS-ODOO-17/odoo/sessiones:/var/lib/odoo/sessions
    networks: [produccion_datos, helipistas_proxy]
    labels:
      - traefik.enable=true
      - traefik.docker.network=helipistas_proxy
      - traefik.http.routers.odoo17.rule=Host(`${DOMINIO_ERP}`)
      - traefik.http.routers.odoo17.entrypoints=websecure
      - traefik.http.routers.odoo17.tls.certresolver=le
      - traefik.http.routers.odoo17.service=odoo17-http
      - traefik.http.services.odoo17-http.loadbalancer.server.port=8069
      # Odoo sirve el websocket en 8072: router propio con prioridad mayor.
      # Equivalente al `location /websocket` de nginx.
      - traefik.http.routers.odoo17-ws.rule=Host(`${DOMINIO_ERP}`) && PathPrefix(`/websocket`)
      - traefik.http.routers.odoo17-ws.entrypoints=websecure
      - traefik.http.routers.odoo17-ws.tls.certresolver=le
      - traefik.http.routers.odoo17-ws.priority=100
      - traefik.http.routers.odoo17-ws.service=odoo17-ws
      - traefik.http.services.odoo17-ws.loadbalancer.server.port=8072
    logging:
      driver: json-file
      options: {max-size: "10m", max-file: "3"}

networks:
  produccion_datos:
    external: true
  helipistas_proxy:
    external: true
```

`stacks/produccion/.env.example`:

```dotenv
DOMINIO_ERP=erp.helipistas.com
# La de hoy está en claro en dockerserver/docker-compose.yml. Aprovechar para rotarla.
POSTGRES_PASSWORD=cambiame
# Hoy es la MISMA que db_password, y es un riesgo anotado en produccion.md
ODOO_ADMIN_PASSWD=cambiame-y-que-sea-distinta
```

> Si se rota `POSTGRES_PASSWORD`, hay que cambiarla también **dentro** de PostgreSQL (`ALTER USER odoo WITH PASSWORD ...`), no sólo en el `.env`: la variable `POSTGRES_PASSWORD` sólo se aplica al inicializar un cluster nuevo, y éste ya existe.

- [ ] **Step 3: Cambio ordenado — el orden importa**

Aquí, y **sólo aquí**, hay dos definiciones de PostgreSQL apuntando al mismo cluster: la del stack desplegado hoy en `/efs/HELIPISTAS-ODOO-17/docker-compose.yml` y la nueva de `stacks/produccion`. Las dos montan `/efs/HELIPISTAS-ODOO-17/postgres`. Producción y preproducción **no** comparten `PGDATA` en ningún momento — son `/efs/HELIPISTAS-ODOO-17/postgres` y `/efs/HELIPISTAS-ODOO-18/postgres` — así que el riesgo es exclusivamente de esta transición.

En la práctica hay una red de seguridad, pero es accidental: ambas definiciones usan `container_name: helipistas_postgres`, y Docker se niega a crear un segundo contenedor con un nombre en uso. El `docker compose up -d` daría error en vez de arrancar. **No conviene apoyarse en eso**: si alguien quita el `container_name` para que compose lo autonombre, la red desaparece. Y la protección propia de PostgreSQL (`postmaster.pid`) tampoco es fiable entre contenedores, porque los namespaces de PID son distintos y el segundo puede concluir que el lock es de un proceso muerto y arrancar igual.

Por eso el paso empieza comprobándolo de forma explícita:

```bash
# 0. Pre-flight: que no quede NADA sirviendo el PGDATA de producción
cd /efs/HELIPISTAS-ODOO-17 && docker-compose down
docker ps --format '{{.Names}}' | grep -q '^helipistas_postgres$' \
  && { echo "ABORTAR: helipistas_postgres sigue en marcha"; exit 1; }
docker ps -q --filter volume=/efs/HELIPISTAS-ODOO-17/postgres \
  | grep -q . && { echo "ABORTAR: algún contenedor sigue montando ese PGDATA"; exit 1; }
echo "OK: el PGDATA de producción no lo sirve nadie"

# 1. Levantar el stack nuevo
cd .../stacks/produccion
cp .env.example .env && "${EDITOR:-vi}" .env
docker compose up -d
docker compose logs -f odoo17 | head -50
```

- [ ] **Step 3b: Confirmar que PostgreSQL encontró el cluster existente, no uno nuevo**

Es la comprobación que detecta el error de montaje: si `PGDATA` apuntara al directorio equivocado, postgres habría creado un cluster vacío o se habría negado a arrancar, y en ambos casos los datos «desaparecen» a ojos de Odoo.

```bash
docker exec helipistas_postgres psql -U odoo -d productiu -tAc \
  "SELECT count(*) FROM ir_module_module WHERE state='installed';"   # esperado: ~275
docker exec helipistas_postgres psql -U odoo -l | head
docker exec helipistas_postgres sh -c 'cat $PGDATA/PG_VERSION'       # esperado: 15
```

Si `productiu` no aparece en el listado de bases, **parar y no tocar nada más**: el montaje está mal, no los datos.

- [ ] **Step 4: Verificar, incluido el websocket**

```bash
echo | openssl s_client -connect "${DOMINIO_ERP}":443 -servername "${DOMINIO_ERP}" 2>/dev/null \
  | openssl x509 -noout -dates -subject
curl -o /dev/null -s -w '%{http_code}\n' "https://${DOMINIO_ERP}/web/login"
```

Y a mano, porque no hay comando que lo cubra: entrar, abrir un registro con chatter y comprobar que llegan mensajes en vivo. El websocket es lo que se rompe si el router de `/websocket` está mal, y no da error en el log del servidor.

- [ ] **Step 5: Retirar el cron del apaño**

```bash
sudo crontab -l | grep -v 'nginx -s reload' | sudo crontab -
```

- [ ] **Step 6: Actualizar `docs/produccion.md`**

Reescribir «nginx: dominios servidos» y **borrar** «Certificados TLS: renovación y recarga de nginx», que describe un problema que ya no existe, dejando nota histórica con la fecha de la caída.

- [ ] **Step 7: Commit**

```bash
git add stacks/produccion/ docs/produccion.md
git commit -m "infra: producción como stack propio detrás de Traefik"
```

---

### Task 7: Stack `herramientas`

Cierra el riesgo de n8n y Metabase en HTTP plano por `IP:5678` e `IP:3000`.

**Files:** Create `stacks/herramientas/docker-compose.yml`, `.env.example`

- [ ] **Step 1: Averiguar de dónde saca los datos Metabase**

```bash
docker inspect metabase_app --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -iE 'MB_DB|SITE_URL'
docker inspect metabase_app --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'
```

> Si `MB_DB_TYPE` no está definido, Metabase guarda su configuración en H2 **dentro del contenedor**: las preguntas están a un `docker rm` de perderse, con o sin migración.

Si es el caso, mover el H2 al volumen **antes** de recrear el contenedor, con Metabase parado para que el fichero quede consistente:

```bash
docker stop metabase_app
docker cp metabase_app:/metabase.db /efs/HELIPISTAS-HERRAMIENTAS/metabase-h2-backup
ls -la /efs/HELIPISTAS-HERRAMIENTAS/metabase-h2-backup   # debe contener metabase.db.mv.db
sudo cp -a /efs/HELIPISTAS-HERRAMIENTAS/metabase-h2-backup/. /efs/HELIPISTAS-HERRAMIENTAS/metabase/
```

Al levantar el stack nuevo con `MB_DB_FILE=/metabase-data/metabase.db`, Metabase debe encontrar todas las preguntas de antes. Si aparece el asistente de instalación inicial, **no seguir**: no ha encontrado el H2 y crearía uno vacío.

- [ ] **Step 2: El stack**

```yaml
services:
  n8n:
    image: helipistas/n8n:1.0.0
    container_name: helipistas_n8n
    restart: unless-stopped
    mem_limit: 512m
    cpu_shares: 512
    environment:
      - N8N_HOST=${DOMINIO_N8N}
      - WEBHOOK_URL=https://${DOMINIO_N8N}/
      - N8N_PROTOCOL=https
    volumes:
      - /efs/HELIPISTAS-HERRAMIENTAS/n8n:/home/node/.n8n
    networks: [helipistas_proxy]
    labels:
      - traefik.enable=true
      - traefik.docker.network=helipistas_proxy
      - traefik.http.routers.n8n.rule=Host(`${DOMINIO_N8N}`)
      - traefik.http.routers.n8n.entrypoints=websecure
      - traefik.http.routers.n8n.tls.certresolver=le
      - traefik.http.services.n8n.loadbalancer.server.port=5678

  metabase:
    image: metabase/metabase:latest
    container_name: metabase_app
    restart: unless-stopped
    mem_limit: 2g
    cpu_shares: 1024
    environment:
      - MB_SITE_URL=https://${DOMINIO_METABASE}
      - JAVA_TOOL_OPTIONS=-Xmx1500m
      # Sin MB_DB_FILE, Metabase guarda su H2 en /metabase.db DENTRO del
      # contenedor y el volumen no sirve de nada. Hay que apuntarlo al volumen.
      - MB_DB_FILE=/metabase-data/metabase.db
    volumes:
      - /efs/HELIPISTAS-HERRAMIENTAS/metabase:/metabase-data
    # produccion_datos porque consulta SQL contra el esquema de Odoo
    networks: [helipistas_proxy, produccion_datos]
    labels:
      - traefik.enable=true
      - traefik.docker.network=helipistas_proxy
      - traefik.http.routers.metabase.rule=Host(`${DOMINIO_METABASE}`)
      - traefik.http.routers.metabase.entrypoints=websecure
      - traefik.http.routers.metabase.tls.certresolver=le
      - traefik.http.services.metabase.loadbalancer.server.port=3000

networks:
  helipistas_proxy:
    external: true
  produccion_datos:
    external: true
```

`stacks/herramientas/.env.example`:

```dotenv
DOMINIO_N8N=n8n.helipistas.com
DOMINIO_METABASE=metabase.helipistas.com
```

> Esos dos dominios ya están puestos en las variables de entorno de los contenedores actuales (`N8N_HOST`, `MB_SITE_URL`) pese a que hoy se accede por `IP:puerto` — es el riesgo que anota `produccion.md`. Ahora pasan a ser verdad.

> `-Xmx1500m` no es decorativo: una JVM sin `-Xmx` dimensiona su heap según la RAM que ve **del host**, no según el `mem_limit`. Sin eso, Metabase crecería hacia 16 GB y el kernel lo mataría con `Exited (137)`.

- [ ] **Step 3: Verificar y cerrar los puertos directos**

```bash
docker compose up -d
curl -o /dev/null -s -w '%{http_code}\n' "https://${DOMINIO_N8N}/"
curl -o /dev/null -s -w '%{http_code}\n' "https://${DOMINIO_METABASE}/"
docker exec metabase_app sh -c 'nc -z pg_produccion 5432 && echo "PG alcanzable"'
```

Comprobar que las preguntas y los workflows siguen ahí. **Después**, cerrar 5678 y 3000 en el security group:

```bash
curl -m 5 -o /dev/null -s -w '%{http_code}\n' http://54.228.16.152:5678/ || echo "cerrado, correcto"
```

- [ ] **Step 4: Commit**

```bash
git add stacks/herramientas/ docs/produccion.md
git commit -m "infra: n8n y Metabase a stack propio con dominio y TLS"
```

---

## FASE 4 — Stack `preproduccion` (Odoo 18)

### Task 8: Levantar Odoo 18

**Files:** Create `stacks/preproduccion/docker-compose.yml`, `Dockerfile`, `odoo.conf`, `.env.example`

- [ ] **Step 1: Imagen**

```dockerfile
FROM odoo:18.0

USER root

# Locale y fuentes: PDFs con acentos (igual que la imagen de 17)
RUN apt-get update \
 && apt-get install -y --no-install-recommends locales fonts-dejavu-core \
 && sed -i 's/# es_ES.UTF-8 UTF-8/es_ES.UTF-8 UTF-8/' /etc/locale.gen \
 && locale-gen \
 && rm -rf /var/lib/apt/lists/*

# CLAUDE.md + external_dependencies de leulit_esignature, leulit_almacen,
# leulit_ia y leulit_partis
RUN pip3 install --no-cache-dir --break-system-packages \
        pypdf pyqrcode pypng pyotp anthropic requests python-dateutil

ENV LANG=es_ES.UTF-8 LANGUAGE=es_ES:es LC_ALL=es_ES.UTF-8

USER odoo
```

- [ ] **Step 2: `odoo.conf`**

```ini
[options]
db_host = pg_preproduccion
db_port = 5432
db_user = odoo
db_template = template0
db_name = productiu
dbfilter = ^productiu$

http_port = 8069
gevent_port = 8072
; menos que producción: no debe competir por recursos
workers = 2
max_cron_threads = 1
lang = es_ES.UTF-8

addons_path = /mnt/extra-addons,/mnt/extra-addons/third-party-addons,/usr/lib/python3/dist-packages/odoo/addons
data_dir = /var/lib/odoo
session_dir = /var/lib/odoo/sessions

log_level = info
log_handler = :INFO
list_db = False

; por debajo del mem_limit de 1500m
limit_memory_hard = 1200000000
limit_memory_soft = 1000000000
limit_request = 8192
limit_time_cpu = 900
limit_time_real = 1800

proxy_mode = True
```

> `gevent_port` es el nombre desde Odoo 16/17; en la config de 17 aparece como `longpolling-port`. Confirmarlo en el paso 4.

- [ ] **Step 3: El stack**

```yaml
services:
  pg_preproduccion:
    image: postgres:15
    container_name: helipistas18_postgres
    restart: unless-stopped
    mem_limit: 2500m
    cpus: 2.0                  # tope duro: un pg_restore no se come la máquina
    cpu_shares: 512            # bajo contención, producción gana
    environment:
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=postgres
      - PGDATA=/var/lib/postgresql/data/pgdata
    volumes:
      # Misma forma que producción: el cluster queda en
      # /efs/HELIPISTAS-ODOO-18/postgres/pgdata. Mantenerla idéntica importa,
      # porque este stack pasa a ser producción en el cutover.
      - /efs/HELIPISTAS-ODOO-18/postgres:/var/lib/postgresql/data
    networks: [preproduccion_datos]
    logging:
      driver: json-file
      options: {max-size: "10m", max-file: "3"}

  odoo18:
    build: .
    image: helipistas/odoo:18.0
    container_name: helipistas18_odoo
    restart: unless-stopped
    mem_limit: 1500m
    cpus: 2.0
    cpu_shares: 512
    depends_on: [pg_preproduccion]
    environment:
      - HOST=pg_preproduccion
      - USER=odoo
      - PASSWORD=${POSTGRES_PASSWORD}
      - ADMIN_PASSWD=${ODOO_ADMIN_PASSWD}
    volumes:
      - ./odoo.conf:/etc/odoo/odoo.conf:ro
      - /efs/HELIPISTAS-ODOO-18/odoo/addons/helipistas-erp-odoo-18/addons:/mnt/extra-addons
      - /efs/HELIPISTAS-ODOO-18/odoo/filestore:/var/lib/odoo/filestore
      - /efs/HELIPISTAS-ODOO-18/odoo/sessiones:/var/lib/odoo/sessions
      - /efs/HELIPISTAS-ODOO-18/openupgrade:/mnt/openupgrade
    networks: [preproduccion_datos, helipistas_proxy]
    labels:
      - traefik.enable=true
      - traefik.docker.network=helipistas_proxy
      - traefik.http.routers.odoo18.rule=Host(`${DOMINIO_PRE}`)
      - traefik.http.routers.odoo18.entrypoints=websecure
      - traefik.http.routers.odoo18.tls.certresolver=le
      - traefik.http.routers.odoo18.service=odoo18-http
      - traefik.http.services.odoo18-http.loadbalancer.server.port=8069
      - traefik.http.routers.odoo18-ws.rule=Host(`${DOMINIO_PRE}`) && PathPrefix(`/websocket`)
      - traefik.http.routers.odoo18-ws.entrypoints=websecure
      - traefik.http.routers.odoo18-ws.tls.certresolver=le
      - traefik.http.routers.odoo18-ws.priority=100
      - traefik.http.routers.odoo18-ws.service=odoo18-ws
      - traefik.http.services.odoo18-ws.loadbalancer.server.port=8072
      # Datos reales: no debe ser pública ni indexable
      - traefik.http.routers.odoo18.middlewares=solo-oficina@file
    logging:
      driver: json-file
      options: {max-size: "10m", max-file: "3"}

networks:
  preproduccion_datos:
    name: preproduccion_datos     # interna: producción no la alcanza
  helipistas_proxy:
    external: true
```

- [ ] **Step 4: Levantar y verificar**

`stacks/preproduccion/.env.example`:

```dotenv
# Dominios de preproducción. Los dos necesitan registro DNS apuntando a la
# Elastic IP antes de levantar el stack, o Traefik no emite certificado.
DOMINIO_PRE=pre.helipistas.com
DOMINIO_METABASE_PRE=metabase-pre.helipistas.com
POSTGRES_PASSWORD=cambiame
# Distinta de POSTGRES_PASSWORD: en producción hoy son la misma, y es un riesgo
ODOO_ADMIN_PASSWD=cambiame-y-que-sea-distinta
```

Comprobar el DNS antes de arrancar, que es el fallo más común y su error en el log de Traefik es poco explícito:

```bash
for d in "$DOMINIO_PRE" "$DOMINIO_METABASE_PRE"; do
  printf '%-32s %s\n' "$d" "$(dig +short "$d" | tail -1)"
done   # las dos deben devolver la Elastic IP
```

```bash
cd stacks/preproduccion
cp .env.example .env && "${EDITOR:-vi}" .env
docker compose up -d --build

docker exec helipistas18_odoo odoo --version        # Odoo Server 18.0
docker exec helipistas18_odoo python3 -c \
  "import pypdf, pyqrcode, png, pyotp, anthropic, requests, dateutil; print('deps OK')"
docker exec helipistas18_odoo odoo --help 2>&1 | grep -iE 'gevent-port|longpolling'
docker exec helipistas18_odoo locale | grep LANG
```

- [ ] **Step 5: Confirmar aislamiento y límites**

```bash
# Preproducción NO debe alcanzar la BD de producción
docker exec helipistas18_odoo sh -c 'nc -z -w2 pg_produccion 5432' \
  && echo "FALLO: preprod alcanza la BD de producción" || echo "OK: aislado"

docker inspect helipistas18_postgres --format \
  'mem={{.HostConfig.Memory}} cpus={{.HostConfig.NanoCpus}} shares={{.HostConfig.CpuShares}}'
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}'
```

> Si `mem=0`, los límites **no** se aplicaron: el compose se desplegó con el binario legacy en vez de v2.

- [ ] **Step 6: Verificar que los dos entornos completos conviven**

Es el criterio de aceptación de la arquitectura, así que se comprueba explícitamente y no de oído.

```bash
echo "=== contenedores en marcha ==="
docker ps --format 'table {{.Names}}\t{{.Status}}' | sort

echo "=== los dos Odoo responden a la vez ==="
for h in "${DOMINIO_ERP}" "${DOMINIO_PRE}"; do
  printf '%-30s ' "$h"
  curl -o /dev/null -s -w '%{http_code}  %{time_total}s\n' "https://$h/web/login"
done

echo "=== los dos PostgreSQL sirven su propia base ==="
docker exec helipistas_postgres   psql -U odoo -d productiu -tAc "SELECT 'prod 17: '||count(*) FROM ir_module_module WHERE state='installed';"
docker exec helipistas18_postgres psql -U odoo -d productiu -tAc "SELECT 'pre  18: '||count(*) FROM ir_module_module WHERE state='installed';"

echo "=== y cada uno sobre su PGDATA, que no es el del otro ==="
docker inspect helipistas_postgres   --format '{{range .Mounts}}{{.Source}}{{end}}'
docker inspect helipistas18_postgres --format '{{range .Mounts}}{{.Source}}{{end}}'

echo "=== memoria ==="
free -h
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}'
```

Tiene que salir: los dos Odoo con `200`, los dos PostgreSQL con su recuento, y **dos rutas de PGDATA distintas**. Si las dos rutas coinciden, parar todo: es el error de montaje de la Task 6.

Con `metabase_pre` levantado (Task 15), la comprobación se repite añadiendo los dos Metabase:

```bash
for h in "${DOMINIO_METABASE}" "${DOMINIO_METABASE_PRE}"; do
  printf '%-30s ' "$h"
  curl -o /dev/null -s -w '%{http_code}\n' "https://$h/"
done
```

- [ ] **Step 7: Commit**

```bash
git add stacks/preproduccion/
git commit -m "infra: stack preproducción Odoo 18 con límites y prioridad reducidos"
```

---

### Task 8B: Segundo MCP de Odoo, apuntando a preproducción

Con un MCP por entorno se pueden consultar los dos desde la misma sesión y comparar recuentos y registros sin entrar por la UI. Y, más importante, **los nombres de las herramientas quedan distintos** (`mcp__odoo__*` frente a `mcp__odoo_pre__*`), lo que hace difícil consultar —o escribir en— el entorno equivocado.

El servidor existente se configura entero por variables de entorno, así que el segundo es el mismo script con otras variables:

```
Command: python3 /Users/emiloalvarez/Work/PROYECTOS/HELIPISTAS/ROLES/odoo-mcp/server.py
Environment: ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD
```

- [ ] **Step 1: Renombrar el actual para que no haya ambigüedad**

Con dos entornos, un servidor llamado `odoo` a secas no dice a cuál apunta.

```bash
claude mcp remove odoo -s user
claude mcp add odoo-prod -s user \
  -e ODOO_URL=https://erp.helipistas.com \
  -e ODOO_DB=productiu \
  -e ODOO_USERNAME='<usuario>' \
  -e ODOO_PASSWORD='<contraseña>' \
  -- python3 /Users/emiloalvarez/Work/PROYECTOS/HELIPISTAS/ROLES/odoo-mcp/server.py
```

- [ ] **Step 2: Añadir el de preproducción**

Las credenciales son las mismas: preproducción es una copia restaurada de producción y `base/data/neutralize.sql` no toca `res_users`.

```bash
claude mcp add odoo-pre -s user \
  -e ODOO_URL=https://pre.helipistas.com \
  -e ODOO_DB=productiu \
  -e ODOO_USERNAME='<usuario>' \
  -e ODOO_PASSWORD='<contraseña>' \
  -- python3 /Users/emiloalvarez/Work/PROYECTOS/HELIPISTAS/ROLES/odoo-mcp/server.py
```

> `pre.helipistas.com` está tras el middleware `solo-oficina` (restricción por IP). El MCP corre desde la máquina de trabajo, así que su IP tiene que estar en el rango permitido o no conectará.

- [ ] **Step 3: Verificar que cada uno apunta donde debe**

```bash
claude mcp list | grep -E 'odoo-prod|odoo-pre'
claude mcp get odoo-pre
```

Y desde una sesión, la comprobación que importa: que los dos devuelvan **versiones distintas de Odoo**. Si coinciden, uno de los dos apunta al sitio equivocado.

- [ ] **Step 4: Usarlo para verificar la migración**

Es lo que justifica la tarea: con los dos MCP se comparan recuentos por modelo entre 17 y 18 sin salir de la sesión, complementando a `verificar_migracion.py`, que compara por tabla. Los dos ángulos no son redundantes: el script ve el esquema, el MCP ve lo que el ORM expone de verdad — que es lo que ven los usuarios.

- [ ] **Step 5: Anotarlo**

Añadir a `docs/produccion.md` que hay dos servidores MCP y cuál apunta a cada entorno, para que nadie asuma que `odoo` es el de pruebas.

> **Aviso de credenciales:** la configuración MCP guarda `ODOO_PASSWORD` **en claro**. Ya ocurre con el servidor actual. Además, la herramienta `odoo_execute_kw` da acceso de escritura como admin sobre el entorno al que apunte. Conviene valorar un usuario de Odoo con permisos limitados para la conexión de producción — es el mismo tipo de riesgo que `produccion.md` ya anota para `db_password` y `admin_passwd`.

---

### Task 9: Los cuatro stacks en Portainer, desde git

- [ ] **Step 1: Dar de alta cada stack**

**Stacks → Add stack → Repository**, uno por cada uno:

| Stack | Compose path |
|---|---|
| `infra` | `stacks/infra/docker-compose.yml` |
| `produccion` | `stacks/produccion/docker-compose.yml` |
| `preproduccion` | `stacks/preproduccion/docker-compose.yml` |
| `herramientas` | `stacks/herramientas/docker-compose.yml` |

Reference: `refs/heads/migracion-odoo-18` (después `main`). Las variables del `.env` van en *Environment variables* de Portainer, que las cifra.

> `infra` con cuidado: al redesplegarlo se recrea Traefik y hay corte de segundos en todo.

- [ ] **Step 2: Probar el ciclo git → redeploy**

Cambio trivial y verificable, commit, *Redeploy*:

```bash
docker exec helipistas18_odoo grep workers /etc/odoo/odoo.conf
```

Si el cambio no aparece, el stack no lee de git: **pararse aquí**, es el mecanismo de despliegue del resto del plan.

- [ ] **Step 3: Documentar y commit**

Sustituir en `docs/produccion.md` la sección «Despliegue / actualización» por el ciclo con Portainer.

```bash
git add docs/produccion.md
git commit -m "docs: despliegue por Portainer con stacks respaldados en git"
```

---

## FASE 5 — Pipeline de copia producción → preproducción

Al estar todo en la misma instancia y el mismo EFS, no hay copias por red.

### Task 10: Volcado y restauración

**Files:** Create `tools/migracion18/dump_produccion.sh`, `restore_preproduccion.sh`

- [ ] **Step 1: Volcado**

```bash
#!/usr/bin/env bash
# pg_dump de producción. Mismo host que el destino: se escribe a EFS, sin red.
set -euo pipefail

DB="${DB:-productiu}"
CONTENEDOR="${CONTENEDOR:-helipistas_postgres}"
SALIDA="${SALIDA:-/efs/dumps/${DB}-$(date -u +%Y%m%dT%H%M%SZ).dump}"

mkdir -p "$(dirname "$SALIDA")"
echo "== inicio $(date -u +%FT%TZ)"
docker exec "$CONTENEDOR" pg_dump -U odoo -Fc -Z6 "$DB" > "$SALIDA"
echo "== fin $(date -u +%FT%TZ)"
ls -lh "$SALIDA"

echo "-- verificando que el dump es legible (no restaura nada)"
docker exec -i "$CONTENEDOR" pg_restore --list < "$SALIDA" > /tmp/dump-toc.txt
echo "   objetos: $(wc -l < /tmp/dump-toc.txt)"
grep -qE 'TABLE DATA.*ir_module_module' /tmp/dump-toc.txt \
  || { echo "ERROR: el dump no contiene ir_module_module"; exit 1; }
sha256sum "$SALIDA" | tee "${SALIDA}.sha256"
```

- [ ] **Step 2: Restauración**

```bash
#!/usr/bin/env bash
# Restaura un dump en el PostgreSQL de PREPRODUCCIÓN.
set -euo pipefail

DUMP="${1:?uso: $0 <fichero.dump>}"
DB="${DB:-productiu}"
CONTENEDOR="${CONTENEDOR:-helipistas18_postgres}"
JOBS="${JOBS:-2}"      # el contenedor tiene tope de 2 CPU

# Salvaguarda: nunca contra el PostgreSQL de producción
case "$CONTENEDOR" in
  *18*) ;;
  *) echo "ABORTADO: '$CONTENEDOR' no parece de preproducción"; exit 1 ;;
esac

[ -f "${DUMP}.sha256" ] && sha256sum -c "${DUMP}.sha256"

echo "== recreando $DB en $CONTENEDOR"
docker exec "$CONTENEDOR" psql -U odoo -d postgres \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB';" || true
docker exec "$CONTENEDOR" psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS $DB;"
docker exec "$CONTENEDOR" psql -U odoo -d postgres \
  -c "CREATE DATABASE $DB TEMPLATE template0 ENCODING 'UTF8';"

echo "== pg_restore -j $JOBS  inicio $(date -u +%FT%TZ)"
docker exec -i "$CONTENEDOR" pg_restore -U odoo -d "$DB" -j "$JOBS" --no-owner --no-acl < "$DUMP"
echo "== fin $(date -u +%FT%TZ)"

docker exec "$CONTENEDOR" psql -U odoo -d "$DB" -tAc \
  "SELECT count(*) FROM ir_module_module WHERE state='installed';" \
  | xargs -I{} echo "   módulos instalados: {} (esperado ~275)"
```

- [ ] **Step 3: Ejecutar y cronometrar**

```bash
chmod +x tools/migracion18/{dump_produccion.sh,restore_preproduccion.sh}
time ./tools/migracion18/dump_produccion.sh
time ./tools/migracion18/restore_preproduccion.sh /efs/dumps/productiu-*.dump
```

Ambas duraciones van al presupuesto. `pg_dump` sobre la BD viva es consistente pero añade carga: primer ensayo fuera de horario, midiendo el impacto con `docker stats`.

- [ ] **Step 4: Commit**

```bash
git add tools/migracion18/dump_produccion.sh tools/migracion18/restore_preproduccion.sh
git commit -m "tools: volcado y restauración de la BD, local al host"
```

---

### Task 11: Copia del filestore

50 GB y ~83.291 ficheros: el mayor consumidor de tiempo del cutover.

**Files:** Create `tools/migracion18/copiar_filestore.sh`

- [ ] **Step 1: Verificar el supuesto de los enlaces duros**

El filestore de Odoo nombra cada fichero por el sha1 de su contenido: se escribe una vez y no se modifica en el sitio; el borrado lo hace un recolector que sólo desenlaza. Si eso se cumple, `cp -al` crea el árbol en minutos y sin espacio extra, y sigue siendo seguro porque si un lado borra, el enlace del otro sobrevive.

Dos cosas que hay que comprobar: que EFS soporta enlaces duros (Task 4 paso 4), y que nada reescribe ficheros del filestore en el sitio:

```bash
grep -rn --include='*.py' --exclude-dir=third-party-addons \
  -E "_full_path|filestore|open\(.*'wb'\)" addons/ | head -20
```

Si algo escribe sobre una ruta existente del filestore, **usar `rsync`**.

- [ ] **Step 2: El script con las dos estrategias**

```bash
#!/usr/bin/env bash
# Copia el filestore de producción a preproducción, en el mismo host.
#
# MODO=enlaces  -> cp -al: minutos, sin espacio extra. Requiere los supuestos
#                  verificados en el paso 1.
# MODO=copia    -> rsync: lento y ocupa otros 50 GB, sin supuestos.
set -euo pipefail

ORIGEN="${ORIGEN:-/efs/HELIPISTAS-ODOO-17/odoo/filestore/}"
DESTINO="${DESTINO:-/efs/HELIPISTAS-ODOO-18/odoo/filestore/}"
MODO="${MODO:-copia}"

mkdir -p "$DESTINO"
echo "== modo=$MODO  inicio $(date -u +%FT%TZ)"

case "$MODO" in
  enlaces) cp -aluv "$ORIGEN". "$DESTINO" 2>&1 | tail -5 ;;
  copia)   rsync -a --info=progress2 --partial --delete "$ORIGEN" "$DESTINO" ;;
  *) echo "MODO debe ser 'enlaces' o 'copia'"; exit 1 ;;
esac

echo "== fin $(date -u +%FT%TZ)"

O=$(find "$ORIGEN" -type f | wc -l | tr -d ' ')
D=$(find "$DESTINO" -type f | wc -l | tr -d ' ')
echo "   origen: $O   destino: $D"
[ "$O" = "$D" ] || { echo "ERROR: recuentos distintos"; exit 1; }

if [ "$MODO" = "enlaces" ]; then
  MUESTRA=$(find "$DESTINO" -type f | head -1)
  echo "   enlaces de la muestra: $(stat -c %h "$MUESTRA") (debe ser >= 2)"
fi
echo "   OK"
```

- [ ] **Step 3: Cronometrar las dos estrategias**

```bash
chmod +x tools/migracion18/copiar_filestore.sh
MODO=enlaces time ./tools/migracion18/copiar_filestore.sh
DESTINO=/efs/pruebas/filestore-rsync/ MODO=copia time ./tools/migracion18/copiar_filestore.sh
```

La diferencia entre ambas es probablemente la diferencia entre una ventana cómoda y una apretada.

- [ ] **Step 4: Comprobar que Odoo 18 lee el filestore enlazado**

No basta con que los ficheros estén.

```bash
docker exec -ti helipistas18_odoo odoo shell -d productiu --no-http
```

```python
a = env['ir.attachment'].sudo().search([('res_model','!=',False),('type','=','binary')], limit=20)
ok = err = 0
for r in a:
    try:
        _ = r.datas and len(r.datas)
        ok += 1
    except Exception as e:
        err += 1
        print('FALLO', r.id, r.name, e)
print(f'legibles: {ok}  fallidos: {err}')
assert err == 0, 'hay adjuntos ilegibles: la copia del filestore no es válida'
```

- [ ] **Step 5: Commit**

```bash
git add tools/migracion18/copiar_filestore.sh
git commit -m "tools: copia del filestore con enlaces duros o rsync"
```

---

### Task 12: Neutralizar preproducción

Una copia con datos reales sin neutralizar manda correos a clientes, dispara webhooks y podría enviar facturas de prueba a la AEAT.

**Files:** Create `tools/migracion18/neutralizar_preproduccion.sh`, `addons/leulit_ia/data/neutralize.sql`, `addons/leulit_meteo/data/neutralize.sql`

- [ ] **Step 1: Qué cubre Odoo de serie**

`odoo-bin neutralize` lee `<módulo>/data/neutralize.sql`. El que hace el trabajo es **`base`**, verificado en 18.0: desactiva todos los `ir_mail_server` **e inserta uno falso apuntando a `invalid:1025`** para impedir el fallback por línea de comandos; **desactiva todos los `ir_cron`** salvo el autovacuum; neutraliza los webhooks (`ir_act_server` con `state='webhook'`); y marca `database.is_neutralized`.

Eso corta de raíz los **15 módulos custom que envían correo** (27 ficheros con `mail.template`, 36 `send_mail(`) y los **19 `ir.cron`**, varios de aviso automático (`check_rojos` de escuela, `notify_expiration_date` de almacén, `actividad_aerea_excedida`, `alerta_tripulacion`, 8 plantillas de planificación).

Traen `neutralize.sql` propio: `mail` (que sólo pone `mail_template.mail_server_id = NULL` — **no es el que protege**), `iap`, `payment`, `website` y **`l10n_es_edi_verifactu`**.

```bash
docker exec helipistas18_odoo sh -c \
  'ls /usr/lib/python3/dist-packages/odoo/addons/*/data/neutralize.sql | wc -l'
docker exec helipistas18_odoo sh -c \
  'ls /usr/lib/python3/dist-packages/odoo/addons/l10n_es_edi_verifactu/data/neutralize.sql'
```

Lo que no cubre: llamadas HTTP directas desde Python (`leulit_ia`, `leulit_meteo`), que se disparan desde acciones de usuario o campos calculados.

- [ ] **Step 2: Nombres REALES de los parámetros**

Inventarlos deja la neutralización sin efecto.

```bash
grep -rn --include='*.py' -E "ir\.config_parameter|get_param|set_param" \
  addons/leulit_meteo addons/leulit_ia
```

- [ ] **Step 3: Los `neutralize.sql`**

`addons/leulit_meteo/data/neutralize.sql` — ajustar las claves a lo visto arriba:

```sql
-- Borra las API keys de meteorología: una copia no productiva no debe consumir
-- cuota de OpenAIP/CheckWX ni llamar a servicios externos.
DELETE FROM ir_config_parameter
      WHERE key LIKE 'leulit_meteo.%key%'
         OR key LIKE 'leulit_meteo.%token%';
```

`addons/leulit_ia/data/neutralize.sql`:

```sql
-- Corta el asistente de IA: sin endpoint ni clave no puede llamar a
-- ai-service, helipistas-mcp, litellm-proxy ni a la API de Anthropic.
DELETE FROM ir_config_parameter WHERE key LIKE 'leulit_ia.%';
```

- [ ] **Step 4: Script con confirmación y verificación**

```bash
#!/usr/bin/env bash
# Neutraliza la BD de PREPRODUCCIÓN. Nunca ejecutar contra producción.
set -euo pipefail

DB="${DB:-productiu}"
CONTENEDOR="${CONTENEDOR:-helipistas18_odoo}"
PG="${PG:-helipistas18_postgres}"

case "$CONTENEDOR" in
  *18*) ;;
  *) echo "ABORTADO: '$CONTENEDOR' no parece de preproducción"; exit 1 ;;
esac

echo "== SQL que se va a aplicar"
docker exec "$CONTENEDOR" odoo neutralize -d "$DB" --stdout | tee /tmp/neutralize.sql
echo
read -r -p "¿Aplicar a '$DB' de PREPRODUCCIÓN? (escribe SI): " ok
[ "$ok" = "SI" ] || { echo "cancelado"; exit 1; }

docker exec "$CONTENEDOR" odoo neutralize -d "$DB"

echo "== verificación"
q(){ docker exec "$PG" psql -U odoo -d "$DB" -tAc "$1"; }
q "SELECT 'servidores de correo activos: '||count(*) FROM ir_mail_server WHERE active;"
q "SELECT 'crons activos: '||count(*) FROM ir_cron WHERE active;"
q "SELECT 'params IA/meteo: '||count(*) FROM ir_config_parameter
     WHERE key LIKE 'leulit_ia.%' OR key LIKE 'leulit_meteo.%key%';"
q "SELECT 'marca de neutralización: '||coalesce(max(value),'AUSENTE')
     FROM ir_config_parameter WHERE key='database.is_neutralized';"
q "SELECT 'url base: '||coalesce(max(value),'(sin definir)')
     FROM ir_config_parameter WHERE key='web.base.url';"
```

- [ ] **Step 5: Ejecutar y comprobar a mano**

```bash
chmod +x tools/migracion18/neutralizar_preproduccion.sh
./tools/migracion18/neutralizar_preproduccion.sh
```

Esperado: `database.is_neutralized` presente y 0 servidores activos. Después, a mano: que aparezca el banner de base neutralizada; enviar un correo de prueba y confirmar que **no sale**; y que `web.base.url` apunte a `${DOMINIO_PRE}` y no a `erp.helipistas.com`, o los enlaces de los correos llevarían a producción.

- [ ] **Step 6: Commit**

```bash
git add tools/migracion18/neutralizar_preproduccion.sh addons/leulit_ia/data addons/leulit_meteo/data
git commit -m "tools: neutralización de preproducción (correo, crons, IA y meteo)"
```

---

### Task 12B: Blindaje de correo en el código custom

La protección de `base` depende del **estado de la base**, y el estado se puede cambiar: basta que alguien configure un SMTP en la copia y los 36 `send_mail(` de los 15 módulos vuelven a salir a Internet contra datos reales de clientes. Un override lo cierra para siempre.

**Files:** Create `addons/leulit/models/mail_mail.py`, `addons/leulit/tests/test_neutralizacion_correo.py`; Modify `addons/leulit/models/__init__.py`

**Interfaces:** override de `mail.mail.send()` que cancela si `database.is_neutralized`. Aplica a todo el proyecto sin tocar ningún punto de llamada.

- [ ] **Step 1: Test primero**

```python
from odoo.tests.common import TransactionCase


class TestNeutralizacionCorreo(TransactionCase):
    """En una base neutralizada, ningún correo debe salir."""

    def _crear_correo(self):
        return self.env["mail.mail"].create({
            "subject": "prueba",
            "email_from": "a@example.com",
            "email_to": "b@example.com",
            "body_html": "<p>x</p>",
        })

    def test_no_envia_si_neutralizada(self):
        self.env["ir.config_parameter"].sudo().set_param("database.is_neutralized", "True")
        correo = self._crear_correo()
        correo.send()
        self.assertEqual(correo.state, "cancel",
                         "en una base neutralizada el correo debe quedar cancelado")

    def test_si_envia_si_no_neutralizada(self):
        # Sin la marca, el override no debe interferir: delega en super() y el
        # correo queda en 'exception' porque no hay SMTP en los tests.
        self.env["ir.config_parameter"].sudo().set_param("database.is_neutralized", "False")
        correo = self._crear_correo()
        correo.send()
        self.assertNotEqual(correo.state, "cancel",
                            "sin neutralizar, el override no debe cancelar nada")
```

- [ ] **Step 2: Ejecutar y ver que falla**

```bash
docker exec helipistas18_odoo odoo -d test18 -u leulit \
  --test-enable --test-tags=/leulit:TestNeutralizacionCorreo --stop-after-init 2>&1 | tail -20
```

- [ ] **Step 3: El override**

```python
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

VERDADEROS = ("True", "true", "1", "t")


class MailMail(models.Model):
    """Impide que una copia no productiva envíe correo a direcciones reales.

    `base/data/neutralize.sql` ya desactiva los servidores SMTP y los crons, pero
    esa protección se pierde si alguien configura un servidor en la copia. Este
    override no depende de la configuración SMTP: mira la marca de la base.

    Cubre de una vez los 36 puntos de envío de los 15 módulos que mandan correo.
    """

    _inherit = "mail.mail"

    @api.model
    def _leulit_base_neutralizada(self) -> bool:
        valor = self.env["ir.config_parameter"].sudo().get_param("database.is_neutralized")
        return str(valor) in VERDADEROS

    def send(self, auto_commit=False, raise_exception=False):
        if self._leulit_base_neutralizada():
            _logger.warning(
                "Base neutralizada: se cancelan %d correo(s). Destinatarios: %s",
                len(self), ", ".join(filter(None, self.mapped("email_to")))[:500],
            )
            self.write({"state": "cancel", "failure_reason": "Base de datos neutralizada"})
            return True
        return super().send(auto_commit=auto_commit, raise_exception=raise_exception)
```

Registrarlo en `addons/leulit/models/__init__.py`:

```python
from . import mail_mail
```

> Se cancela en vez de dejarlo en cola: un `mail.mail` en `outgoing` que falla se reintenta y llena el log. `cancel` es terminal y deja rastro de qué se habría enviado.

- [ ] **Step 4: Test en verde**

```bash
docker exec helipistas18_odoo odoo -d test18 -u leulit \
  --test-enable --test-tags=/leulit:TestNeutralizacionCorreo --stop-after-init 2>&1 | tail -20
```

- [ ] **Step 5: Comprobarlo sobre la copia real**

```bash
docker exec -ti helipistas18_odoo odoo shell -d productiu --no-http
```

```python
print('neutralizada:', env['ir.config_parameter'].sudo().get_param('database.is_neutralized'))
pendientes = env['mail.mail'].sudo().search([('state', '=', 'outgoing')])
print('en cola:', len(pendientes))
pendientes.send()
print('en cola tras send():', env['mail.mail'].sudo().search_count([('state','=','outgoing')]))
print('cancelados:', env['mail.mail'].sudo().search_count([('state','=','cancel')]))
```

Esperado: la cola queda a 0, los cancelados suben, **cero correos salidos**.

- [ ] **Step 6: Commit**

```bash
git add addons/leulit/models/mail_mail.py addons/leulit/models/__init__.py \
        addons/leulit/tests/test_neutralizacion_correo.py
git commit -m "leulit: cancelar el envío de correo en bases neutralizadas"
```

---

## FASE 6 — Ensayos cronometrados

### Task 13: Orquestar el salto 17 → 18

**Files:** Create `tools/migracion18/migrar_17_a_18.sh`, `verificar_migracion.py`

- [ ] **Step 1: Traer OpenUpgrade 18.0**

```bash
sudo git clone --depth 1 -b 18.0 https://github.com/OCA/OpenUpgrade.git \
  /efs/HELIPISTAS-ODOO-18/openupgrade
ls /efs/HELIPISTAS-ODOO-18/openupgrade/openupgrade_scripts/scripts | wc -l   # ~429
less /efs/HELIPISTAS-ODOO-18/openupgrade/README.md   # contrastar el mecanismo de la rama 18
```

- [ ] **Step 2: El orquestador**

```bash
#!/usr/bin/env bash
# Migración 17 -> 18 con OpenUpgrade, cronometrando cada fase.
# La salida de tiempos ES el entregable: alimenta el presupuesto del cutover.
set -euo pipefail

DB="${DB:-productiu}"
ODOO="${ODOO:-helipistas18_odoo}"
PG="${PG:-helipistas18_postgres}"
LOG="${LOG:-/efs/HELIPISTAS-ODOO-18/migracion-$(date -u +%Y%m%dT%H%M%SZ).log}"

case "$ODOO" in *18*) ;; *) echo "ABORTADO: '$ODOO' no es preproducción"; exit 1;; esac

fase() {
  local nombre="$1"; shift
  local t0 t1; t0=$(date +%s)
  echo "=== [$nombre] inicio $(date -u +%FT%TZ)" | tee -a "$LOG"
  "$@" >>"$LOG" 2>&1
  t1=$(date +%s)
  printf '=== [%s] FIN en %d s (%d min)\n' "$nombre" "$((t1-t0))" "$(((t1-t0)/60))" | tee -a "$LOG"
}

q(){ docker exec "$PG" psql -U odoo -d "$DB" -tAc "$1"; }

echo "### módulos instalados antes: $(q "SELECT count(*) FROM ir_module_module WHERE state='installed';")"

fase "openupgrade-17-18" \
  docker exec "$ODOO" odoo \
    -d "$DB" -u all --stop-after-init \
    --load=base,web,openupgrade_framework \
    --addons-path="/mnt/openupgrade/openupgrade_scripts/scripts,/mnt/extra-addons,/mnt/extra-addons/third-party-addons,/usr/lib/python3/dist-packages/odoo/addons"

echo "### módulos instalados después: $(q "SELECT count(*) FROM ir_module_module WHERE state='installed';")"
echo "### módulos en estado raro:"
q "SELECT name||' -> '||state FROM ir_module_module
    WHERE state NOT IN ('installed','uninstalled','uninstallable');"

echo "### TIEMPOS"; grep '^=== \[' "$LOG" | grep FIN
```

- [ ] **Step 3: Verificación por recuentos**

```python
#!/usr/bin/env python3
"""Compara recuentos por tabla entre la BD de origen (17) y la migrada (18).

Primera ejecución: guarda los recuentos de ORIGEN. Segunda: compara.
"""
import json
import pathlib
import subprocess
import sys

PG = "helipistas18_postgres"
DB = "productiu"
ORIGEN = pathlib.Path("/efs/HELIPISTAS-ODOO-18/recuentos-origen.json")

TABLAS = [
    "res_partner", "res_users", "account_move", "account_move_line",
    "ir_attachment", "leulit_vuelo", "leulit_checklist", "leulit_helicoptero",
    "leulit_piloto", "leulit_alumno", "leulit_anomalia", "leulit_parte_escuela",
    "stock_lot", "stock_picking", "maintenance_request", "maintenance_equipment",
    "mgmtsystem_nonconformity", "mgmtsystem_audit", "project_task",
    "hr_employee", "hr_expense",
]


def cuenta(tabla: str) -> int | None:
    r = subprocess.run(
        ["docker", "exec", PG, "psql", "-U", "odoo", "-d", DB, "-tAc",
         f"SELECT count(*) FROM {tabla};"],
        capture_output=True, text=True,
    )
    return None if r.returncode != 0 else int(r.stdout.strip())


def main() -> int:
    actual = {t: cuenta(t) for t in TABLAS}

    if not ORIGEN.exists():
        ORIGEN.write_text(json.dumps(actual, indent=2))
        print(f"Recuentos de ORIGEN guardados en {ORIGEN}.")
        for t, n in actual.items():
            print(f"  {t:32} {n if n is not None else 'AUSENTE'}")
        return 0

    origen = json.loads(ORIGEN.read_text())
    fallos = []
    print(f"{'tabla':32} {'origen':>10} {'destino':>10}  veredicto")
    for t in TABLAS:
        o, a = origen.get(t), actual.get(t)
        if o is None and a is None:
            v = "ausente en ambos"
        elif o is None:
            v = "NUEVA en destino"
        elif a is None:
            v = "PERDIDA en destino"; fallos.append(t)
        elif a == o:
            v = "OK"
        elif a > o:
            v = f"crecio +{a - o}"
        else:
            v = f"PERDIO {o - a}"; fallos.append(t)
        print(f"{t:32} {str(o):>10} {str(a):>10}  {v}")

    if fallos:
        print(f"\nFALLO: pérdida en {len(fallos)} tabla(s): {', '.join(fallos)}")
        return 1
    print("\nOK: ninguna tabla de negocio perdió registros")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Primer ensayo de punta a punta**

```bash
./tools/migracion18/dump_produccion.sh
./tools/migracion18/restore_preproduccion.sh /efs/dumps/productiu-<fecha>.dump
python3 tools/migracion18/verificar_migracion.py       # guarda ORIGEN
MODO=enlaces ./tools/migracion18/copiar_filestore.sh
./tools/migracion18/neutralizar_preproduccion.sh
time ./tools/migracion18/migrar_17_a_18.sh
python3 tools/migracion18/verificar_migracion.py       # compara
```

El primer ensayo **va a fallar**: su función es producir la lista de lo que rompe.

- [ ] **Step 5: Iterar hasta que sea repetible**

Repetir desde copia fresca hasta lograr **dos ejecuciones seguidas sin intervención manual** y verificación en verde. Cada iteración: fallo, causa y arreglo en `docs/cutover-runbook.md`.

Regla dura: **si un arreglo consiste en tocar la BD a mano, no vale.** Va al script.

Y vigilar producción durante cada ensayo, que es lo nuevo de tenerlo todo en una máquina:

```bash
while true; do
  printf '%s  ' "$(date +%T)"
  curl -o /dev/null -s -w 'prod=%{http_code} %{time_total}s\n' "https://${DOMINIO_ERP}/web/login"
  sleep 30
done
```

> Los `cpu_shares` sólo actúan sobre contención de **CPU**; la contención de **I/O** sobre EFS no la limitan. Si producción se degrada por I/O, las palancas son `JOBS` en `pg_restore`, los enlaces duros y ensayar fuera de horario.

- [ ] **Step 6: Commit**

```bash
git add tools/migracion18/migrar_17_a_18.sh tools/migracion18/verificar_migracion.py docs/cutover-runbook.md
git commit -m "tools: orquestador cronometrado 17->18 y verificación por recuentos"
```

---

### Task 14: Validación funcional y n8n

**Files:** Modify `docs/migracion-odoo-18-permisos.md`, `docs/cutover-runbook.md`

- [ ] **Step 1: Matriz de permisos sobre datos reales**

Repetir la comprobación por rol de la Task 12 del plan de Fases 0-1, ahora contra la copia real, donde salen los casos que los datos de prueba no tienen.

- [ ] **Step 2: Recorrido por áreas**

Vuelos, taller/CAMO, escuela, seguridad/calidad, almacén, contabilidad. Para cada una: listado, abrir registro, editar, **imprimir un PDF** (verifica locale y fuentes) y ejecutar el flujo principal.

- [ ] **Step 3: n8n**

Automatiza por API contra modelos que cambian de nombre. Inventariar workflows, probarlos y anotar `OK` / `ROTO` / arreglo.

```bash
docker exec helipistas_n8n sh -c \
  'sqlite3 /home/node/.n8n/database.sqlite "SELECT id, name, active FROM workflow_entity;"' \
  || echo "n8n con otra BD: exportar los workflows desde la UI"
```

- [ ] **Step 4: Rendimiento comparado**

```bash
for h in "${DOMINIO_ERP}" "${DOMINIO_PRE}"; do
  printf '%-28s ' "$h"
  curl -o /dev/null -s -w '%{http_code}  %{time_total}s\n' "https://$h/web/login"
done
```

Preproducción tiene `workers=2` y tope de 2 CPU: será más lenta y eso es esperado. Lo que hay que detectar es una diferencia **desproporcionada**, que indicaría una consulta degradada por la migración.

- [ ] **Step 5: Commit**

```bash
git add docs/migracion-odoo-18-permisos.md docs/cutover-runbook.md
git commit -m "docs: validación funcional, n8n y rendimiento en preproducción"
```

---

## FASE 6B — Metabase

Metabase es el frontend de KPIs y consulta SQL directamente contra el esquema de Odoo. Dos modos de fallo, y el segundo es peor: una columna inexistente **da error** y se ve; un `JOIN` que deja de casar **devuelve menos filas y un número equivocado, sin aviso**.

Caso confirmado en `upgrade_analysis.txt` de `account` en OpenUpgrade 18.0:

```
account / account.account / company_id (many2one)  : DEL relation: res.company, required
account / account.account / company_ids (many2many): NEW relation: res.company, ...
```

`account_account.company_id` desaparece y pasa a many2many con tabla puente.

### Task 15: Inventariar y analizar el impacto

**Files:** Create `tools/migracion18/metabase_exportar.sh`, `metabase_analizar.py`, `docs/migracion-odoo-18-metabase.md`

**Interfaces:** `cambios_esquema(ruta_openupgrade) -> {'modelos_obsoletos': set, 'campos_eliminados': set[(modelo, campo)]}`.

- [ ] **Step 1: Dónde vive la configuración de Metabase**

Ya comprobado en la Task 7 paso 1. Si es H2 dentro del contenedor, sacarlo a EFS **antes** de seguir.

- [ ] **Step 2: Exportar las preguntas por la API**

Más fiable que leer H2 y sirve con cualquier backend.

```bash
#!/usr/bin/env bash
# Exporta preguntas y dashboards de Metabase por su API REST.
set -euo pipefail

MB_URL="${MB_URL:?exporta MB_URL}"
MB_USER="${MB_USER:?exporta MB_USER}"
SALIDA="${SALIDA:-/efs/HELIPISTAS-ODOO-18/metabase}"

mkdir -p "$SALIDA"
read -r -s -p "Contraseña de $MB_USER: " MB_PASS; echo

TOKEN=$(curl -sS -X POST "$MB_URL/api/session" \
  -H 'Content-Type: application/json' \
  -d "$(printf '{"username":"%s","password":"%s"}' "$MB_USER" "$MB_PASS")" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
[ -n "$TOKEN" ] || { echo "ERROR: no se obtuvo token"; exit 1; }

for r in card dashboard database; do
  curl -sS "$MB_URL/api/$r" -H "X-Metabase-Session: $TOKEN" > "$SALIDA/metabase-$r.json"
  echo "  $r: $(python3 -c "import json;print(len(json.load(open('$SALIDA/metabase-$r.json'))))")"
done
```

- [ ] **Step 3: Cruzar con los cambios de esquema**

```python
#!/usr/bin/env python3
"""Cruza las consultas de Metabase con los cambios de esquema de OpenUpgrade 18.

¿Qué preguntas guardadas tocan una tabla o columna que 18 elimina?

    python3 metabase_analizar.py --openupgrade <ruta> --cards <metabase-card.json>
"""
import argparse
import json
import pathlib
import re
import sys

# 'account / account.account / company_id (many2one) : DEL relation: ...'
RE_CAMPO = re.compile(
    r"^\s*\S+\s*/\s*(?P<modelo>[\w.]+)\s*/\s*(?P<campo>\w+)\s*\([^)]*\)\s*:\s*(?P<accion>DEL|NEW)\b"
)
RE_MODELO_OBSOLETO = re.compile(r"^\s*obsolete model\s+(?P<modelo>[\w.]+)")


def tabla(modelo: str) -> str:
    """Nombre de tabla de un modelo Odoo: los puntos pasan a guiones bajos."""
    return modelo.replace(".", "_")


def cambios_esquema(raiz: pathlib.Path) -> dict:
    modelos_obsoletos: set[str] = set()
    campos_eliminados: set[tuple[str, str]] = set()

    ficheros = list(raiz.rglob("upgrade_analysis.txt"))
    if not ficheros:
        sys.exit(f"No se encontró ningún upgrade_analysis.txt bajo {raiz}")

    for f in ficheros:
        for linea in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if m := RE_MODELO_OBSOLETO.match(linea):
                modelos_obsoletos.add(m.group("modelo"))
            elif m := RE_CAMPO.match(linea):
                if m.group("accion") == "DEL":
                    campos_eliminados.add((m.group("modelo"), m.group("campo")))

    return {"ficheros": len(ficheros), "modelos_obsoletos": modelos_obsoletos,
            "campos_eliminados": campos_eliminados}


def sql_de_card(card: dict) -> str:
    """SQL nativo de una pregunta, o '' si es una pregunta gráfica."""
    q = card.get("dataset_query") or {}
    return (q.get("native") or {}).get("query") or "" if q.get("type") == "native" else ""


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--openupgrade", required=True, type=pathlib.Path)
    p.add_argument("--cards", required=True, type=pathlib.Path)
    a = p.parse_args()

    c = cambios_esquema(a.openupgrade)
    print(f"upgrade_analysis.txt leídos : {c['ficheros']}")
    print(f"modelos obsoletos           : {len(c['modelos_obsoletos'])}")
    print(f"campos eliminados           : {len(c['campos_eliminados'])}\n")

    tablas_muertas = {tabla(m) for m in c["modelos_obsoletos"]}
    cols_muertas: dict[str, set[str]] = {}
    for modelo, campo in c["campos_eliminados"]:
        cols_muertas.setdefault(tabla(modelo), set()).add(campo)

    afectadas, nativas, graficas = [], 0, 0
    for card in json.loads(a.cards.read_text()):
        if card.get("archived"):
            continue
        sql = sql_de_card(card)
        if not sql:
            graficas += 1
            continue
        nativas += 1
        bajo = sql.lower()
        motivos = []

        for t in tablas_muertas:
            if re.search(rf"\b{re.escape(t)}\b", bajo):
                motivos.append(f"tabla eliminada: {t}")

        for t, cols in cols_muertas.items():
            if not re.search(rf"\b{re.escape(t)}\b", bajo):
                continue
            for col in cols:
                if re.search(rf"\b{re.escape(col)}\b", bajo):
                    motivos.append(f"columna eliminada: {t}.{col}")

        if motivos:
            afectadas.append((card.get("id"), card.get("name"), sorted(set(motivos))))

    print(f"preguntas nativas (SQL)     : {nativas}")
    print(f"preguntas gráficas          : {graficas}  <- revisar aparte (paso 5)")
    print(f"preguntas AFECTADAS         : {len(afectadas)}\n")

    for cid, nombre, motivos in sorted(afectadas, key=lambda x: -len(x[2])):
        print(f"[{cid}] {nombre}")
        for m in motivos:
            print(f"      {m}")

    assert c["campos_eliminados"] or c["modelos_obsoletos"], \
        "el análisis no encontró ningún cambio: revisar el formato de upgrade_analysis.txt"
    return 1 if afectadas else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Ejecutar**

```bash
chmod +x tools/migracion18/metabase_exportar.sh
MB_URL=https://metabase.helipistas.com MB_USER=<usuario> ./tools/migracion18/metabase_exportar.sh

python3 tools/migracion18/metabase_analizar.py \
  --openupgrade /efs/HELIPISTAS-ODOO-18/openupgrade \
  --cards /efs/HELIPISTAS-ODOO-18/metabase/metabase-card.json \
  | tee docs/migracion-odoo-18-metabase.md
```

- [ ] **Step 5: Metabase de preproducción, en un contenedor aparte**

**El Metabase de producción no se toca en ningún momento**: ni se le añade una fuente de datos, ni se le conecta otra red, ni se le duplican colecciones. Sigue mostrando exactamente lo que muestra hoy, apuntando al Odoo 17.

Para probar contra el 18 se levanta un **segundo Metabase**, sembrado con una copia de la configuración del de producción, de modo que **todas las preguntas existan ya** — incluidas las gráficas, que no se pueden duplicar entre fuentes a mano porque su tabla origen está atada a una base concreta.

Añadir al stack `preproduccion`:

```yaml
  metabase_pre:
    image: metabase/metabase:latest
    container_name: metabase_pre
    restart: unless-stopped
    mem_limit: 2g
    cpu_shares: 512
    environment:
      - MB_SITE_URL=https://${DOMINIO_METABASE_PRE}
      - JAVA_TOOL_OPTIONS=-Xmx1500m
      - MB_DB_FILE=/metabase-data/metabase.db
    volumes:
      - /efs/HELIPISTAS-ODOO-18/metabase:/metabase-data
    networks: [preproduccion_datos, helipistas_proxy]
    labels:
      - traefik.enable=true
      - traefik.docker.network=helipistas_proxy
      - traefik.http.routers.metabase-pre.rule=Host(`${DOMINIO_METABASE_PRE}`)
      - traefik.http.routers.metabase-pre.entrypoints=websecure
      - traefik.http.routers.metabase-pre.tls.certresolver=le
      - traefik.http.services.metabase-pre.loadbalancer.server.port=3000
      - traefik.http.routers.metabase-pre.middlewares=solo-oficina@file
```

Sembrarlo con la configuración de producción, con el Metabase de producción **parado** para que el H2 quede consistente:

```bash
sudo mkdir -p /efs/HELIPISTAS-ODOO-18/metabase
docker stop metabase_app
sudo cp -a /efs/HELIPISTAS-HERRAMIENTAS/metabase/. /efs/HELIPISTAS-ODOO-18/metabase/
docker start metabase_app          # producción vuelve enseguida
cd stacks/preproduccion && docker compose up -d metabase_pre
```

- [ ] **Step 6: Cortarle el correo al clon — antes de abrirlo a nadie**

El clon hereda la configuración SMTP y **las suscripciones de dashboard** de producción. Sin esto, enviaría los mismos informes por correo a los mismos destinatarios reales, duplicados y con datos de una copia.

En `https://${DOMINIO_METABASE_PRE}`, y en este orden:

1. **Admin → Email:** borrar el host SMTP y guardar. Sin host no puede enviar, hagas lo que hagas después.
2. **Admin → Troubleshooting → Subscriptions** (o revisando cada dashboard): borrar todas las suscripciones y alertas.

Verificar que no queda nada configurado:

```bash
docker exec metabase_pre sh -c \
  'grep -ao "email-smtp-host" /metabase-data/metabase.db.mv.db | head -1' \
  && echo "revisar a mano en Admin -> Email" || echo "sin rastro de SMTP"
```

> La comprobación por `grep` sobre el H2 es orientativa, no concluyente. La que vale es la de la UI. Y si al abrir el clon aparece el asistente de instalación inicial, la siembra falló: no ha encontrado el H2 copiado.

- [ ] **Step 7: Repuntar la fuente de datos del clon y comparar**

En el clon, **Admin → Databases → (la de Odoo) → Edit**: cambiar el host a `pg_preproduccion` y guardar. Después **Sync database schema now** y **Re-scan field values**.

Al reapuntar la misma fuente en lugar de añadir una nueva, todas las preguntas —nativas y gráficas— siguen colgando de ella y se ejecutan contra el 18 sin tocarlas.

```bash
docker exec metabase_pre sh -c 'nc -z pg_preproduccion 5432 && echo alcanzable'
```

Ejecutar **todas** las preguntas y anotar en `docs/migracion-odoo-18-metabase.md`:

| Pregunta | Tipo | Resultado en 18 | Cifra en 17 | Cifra en 18 | Acción |
|---|---|---|---|---|---|

Con los dos Metabase vivos en paralelo se comparan las cifras **lado a lado en dos pestañas**, que es exactamente lo que hace falta y lo que el enfoque de una sola instancia no permitía.

> El valor peligroso de la columna «Resultado» es **«cifra distinta»**: no da error, sólo un KPI equivocado. Las diferencias esperadas son sólo por los datos entrados entre el dump y ahora; cualquier otra es un fallo de la consulta.

- [ ] **Step 8: Commit**

```bash
git add stacks/preproduccion/docker-compose.yml \
        tools/migracion18/metabase_exportar.sh tools/migracion18/metabase_analizar.py \
        docs/migracion-odoo-18-metabase.md
git commit -m "metabase: instancia de preproducción aparte, sin tocar la de producción

Clon sembrado con la config de producción y reapuntado a pg_preproduccion, con
SMTP y suscripciones desactivadas. Permite comparar KPIs lado a lado."
```

---

### Task 16: Arreglar las consultas y prepararlas para el cutover

**Files:** Modify `docs/migracion-odoo-18-metabase.md`; Create `docs/metabase/consultas/*.sql`

- [ ] **Step 1: Corregir cada consulta afectada**

Patrón del caso confirmado:

```sql
-- Antes (17)
SELECT a.code, a.name FROM account_account a WHERE a.company_id = 2;

-- Después (18): hay tabla puente
SELECT a.code, a.name
  FROM account_account a
  JOIN account_account_res_company_rel r ON r.account_account_id = a.id
 WHERE r.res_company_id = 2;
```

**El nombre de la tabla puente se verifica, no se deduce:**

```bash
docker exec helipistas18_postgres psql -U odoo -d productiu -c "\dt *account*company*"
docker exec helipistas18_postgres psql -U odoo -d productiu -c "\d account_account"
```

- [ ] **Step 2: Versionar el SQL corregido**

Metabase no versiona nada: si sus preguntas viven sólo en su base, el trabajo se pierde con un `docker rm`.

```bash
mkdir -p docs/metabase/consultas
python3 - <<'PY'
import json, pathlib, re
cards = json.loads(pathlib.Path('/efs/HELIPISTAS-ODOO-18/metabase/metabase-card.json').read_text())
dest = pathlib.Path('docs/metabase/consultas'); dest.mkdir(parents=True, exist_ok=True)
n = 0
for c in cards:
    q = c.get('dataset_query') or {}
    if q.get('type') != 'native':
        continue
    sql = (q.get('native') or {}).get('query') or ''
    if not sql.strip():
        continue
    slug = re.sub(r'[^a-z0-9]+', '-', (c.get('name') or 'sin-nombre').lower()).strip('-')
    (dest / f"{c['id']:04d}-{slug}.sql").write_text(sql.rstrip() + '\n')
    n += 1
print(f'{n} consultas nativas volcadas a {dest}')
PY
```

- [ ] **Step 3: Verificar cifra a cifra contra producción**

Para cada KPI que devuelva un número: ejecutarlo en producción (17) y en la copia migrada (18) y comparar. Diferencias esperadas sólo por los datos entrados entre el dump y ahora; cualquier otra es un fallo de la consulta corregida.

- [ ] **Step 4: Decidir qué Metabase queda como el de producción**

Tras el cutover la base está en `helipistas18_postgres`. Hay dos formas de que `metabase.helipistas.com` la sirva, y hay que elegir **antes** de la ventana:

**Opción A — repuntar el Metabase de producción (recomendada).** Se le añade la red del stack nuevo y se cambia el host de su fuente de datos a `helipistas18_postgres`. Conserva su H2, o sea **todas las preguntas creadas desde que se sembró el clon**, y los usuarios siguen entrando por la misma URL.

**Opción B — promover `metabase_pre`.** Apuntar `metabase.helipistas.com` al clon. Más rápido, pero **descarta cualquier pregunta o dashboard creado en el Metabase de producción después de la siembra**, y hay que reponerle el SMTP y las suscripciones que se le quitaron en el paso 6.

Recomendación: **A**, precisamente por eso. El clon existe para verificar, no para heredar.

Comprobar cuánto se ha movido el Metabase de producción desde la siembra, que es el dato que decide:

```bash
docker exec metabase_app sh -c \
  'ls -la --time-style=+%F /metabase-data/metabase.db.mv.db'
```

Anotar la opción elegida en `docs/cutover-runbook.md`.

- [ ] **Step 5: Commit**

```bash
git add docs/metabase/consultas docs/migracion-odoo-18-metabase.md
git commit -m "metabase: consultas corregidas para el esquema de 18 y versionadas"
```

---

## FASE 7 — Gestión de la deriva

### Task 17: Deriva de código

**Files:** Create `docs/migracion-odoo-18-deriva.md`

- [ ] **Step 1: Rebase semanal, sin excepción**

```bash
git checkout migracion-odoo-18
git fetch origin && git rebase origin/main
# Conflictos en ficheros ya migrados (<list>, chatter, name_get): resolver
# MANTENIENDO la forma de 18 e incorporando el cambio funcional.
python3 tools/migracion18/test_inventario.py
docker exec helipistas18_odoo python3 -m compileall -q /mnt/extra-addons
```

- [ ] **Step 2: Detectar si producción reintrodujo patrones de 17**

```bash
BASE=$(git merge-base origin/main migracion-odoo-18)
git diff --name-only "$BASE" origin/main -- addons/ | tee /tmp/cambios-prod.txt
grep -l -E '<tree[ >]|oe_chatter|name_get|kanban-box' $(cat /tmp/cambios-prod.txt) 2>/dev/null
```

Cualquier resultado del segundo comando es una regresión.

- [ ] **Step 3: Congelación con fechas**

En `docs/migracion-odoo-18-deriva.md`, acordado con el equipo:

- **T−14 días:** congelación blanda. Sólo correcciones. Cada cambio que entre en `main` se aplica a `migracion-odoo-18` **el mismo día** y se re-prueba.
- **T−2 días:** congelación dura. Sólo incidencias críticas, con aprobación explícita y re-ensayo completo después.
- **Durante la ventana:** `main` bloqueado.

Sin congelación no hay ventana de 24 h: cada cambio de última hora invalida el ensayo que la respaldaba.

- [ ] **Step 4: Commit**

```bash
git add docs/migracion-odoo-18-deriva.md
git commit -m "docs: política de congelación y control de deriva de código"
```

---

### Task 18: Ensayo final y presupuesto de la ventana

**Files:** Modify `docs/cutover-runbook.md`

- [ ] **Step 1: Lo que no se puede pre-migrar**

La BD no: el volcado consistente exige producción parada. Por eso va dentro de la ventana y por eso su duración tiene que conocerse con precisión. Lo que sí sale fuera es el filestore (Task 11).

- [ ] **Step 2: Ensayo final con datos del día anterior**

A T−3 días, ciclo completo con datos de menos de 24 h. **Es el que produce los números definitivos.**

- [ ] **Step 3: Rellenar el presupuesto**

| # | Fase | Medido | ×1,5 | Acumulado |
|---|---|---|---|---|
| 1 | Aviso y parada de Odoo 17 | | | |
| 2 | `pg_dump` de producción | | | |
| 3 | Copia final del filestore (delta) | | | |
| 4 | `pg_restore` en preproducción | | | |
| 5 | OpenUpgrade 17→18 | | | |
| 6 | `verificar_migracion.py` | | | |
| 7 | Pruebas de humo y matriz de roles | | | |
| 8 | Cambio de routers de Traefik + Metabase | | | |

**El acumulado con margen ×1,5 tiene que caber en menos de 24 h con holgura.** Si no cabe: subir `JOBS`, usar enlaces duros, o revisar el throughput de EFS. Y volver a ensayar.

- [ ] **Step 4: Ensayar el rollback**

Un rollback sin ensayar no es un rollback. Simular el fallo y ejecutar la vuelta atrás completa, cronometrada. **Por debajo de 1 hora.**

- [ ] **Step 5: Commit**

```bash
git add docs/cutover-runbook.md
git commit -m "docs: presupuesto de la ventana con tiempos medidos y rollback ensayado"
```

---

## FASE 8 — Cutover

### Task 19: La ventana de 24 h

**Requisito de entrada:** dos ensayos seguidos limpios, presupuesto ×1,5 por debajo de 24 h, rollback ensayado por debajo de 1 h, congelación dura activa, backup EFS bajo demanda hecho.

- [ ] **Step 1: T−1 día**

```bash
aws backup start-backup-job --backup-vault-name <vault> \
  --resource-arn arn:aws:elasticfilesystem:eu-west-1:<cuenta>:file-system/fs-ec7152d9 \
  --iam-role-arn <rol>

MODO=enlaces ./tools/migracion18/copiar_filestore.sh   # deja el delta en mínimos
```

- [ ] **Step 2: T+00:00 — parar producción**

```bash
# Avisar por los canales acordados. Parar SOLO Odoo: PostgreSQL sigue vivo
# para el volcado.
docker stop helipistas_odoo
docker ps --filter name=helipistas_odoo
```

Traefik responderá 502. Decidir **antes** si se quiere página de mantenimiento con un middleware `errors`.

- [ ] **Step 3: Volcado y copia final**

```bash
./tools/migracion18/dump_produccion.sh
MODO=enlaces ./tools/migracion18/copiar_filestore.sh
```

> **Puerta 1:** si aquí se ha consumido más del 25 % de la ventana, parar y evaluar. Continuar sólo si el resto del presupuesto cabe.

- [ ] **Step 4: Restaurar y migrar**

```bash
./tools/migracion18/restore_preproduccion.sh /efs/dumps/productiu-<fecha>.dump
python3 tools/migracion18/verificar_migracion.py    # recuentos de ORIGEN
time ./tools/migracion18/migrar_17_a_18.sh
```

**No se neutraliza.** Esta base va a ser producción; neutralizarla la dejaría sin correo ni crons.

Y como preproducción pasa a ser producción, **subirle los recursos** antes de abrir a usuarios: `mem_limit` y `cpu_shares` como los de producción, `workers = 4`, y redeploy desde Portainer.

> **Puerta 2:** si OpenUpgrade supera en más del 50 % su tiempo de ensayo, **abortar y hacer rollback**. No se depura dentro de la ventana.

- [ ] **Step 5: Verificar antes de dejar entrar a nadie**

```bash
python3 tools/migracion18/verificar_migracion.py
```

Tiene que decir «ninguna tabla de negocio perdió registros». Después, pruebas de humo con la matriz de roles y, sin excepción: un vuelo se abre y se edita; un PDF sale con acentos correctos; el chatter recibe en vivo; un usuario de cada rol ve lo que debe; Metabase y n8n funcionan.

> **Puerta 3 — punto de no retorno.** Hasta aquí el rollback es limpio: `/efs/HELIPISTAS-ODOO-17/` está intacto y su BD sólo se ha leído. En cuanto los usuarios metan datos en 18, volver atrás pierde ese trabajo. **Se decide explícitamente y se anota la hora.**

- [ ] **Step 6: Cambiar el tráfico al 18**

Mismo host: no hay cambio de DNS, se cambian los routers de Traefik. En `stacks/preproduccion/docker-compose.yml`, `DOMINIO_PRE` → `DOMINIO_ERP` y quitar el middleware `solo-oficina`. Commit y redeploy.

```bash
curl -o /dev/null -s -w '%{http_code}\n' "https://erp.helipistas.com/web/login"
docker exec helipistas18_postgres psql -U odoo -d productiu -tAc \
  "SELECT value FROM ir_config_parameter WHERE key='web.base.url';"
```

Esa URL base tiene que decir `erp.helipistas.com`, o los enlaces de los correos saldrán mal.

- [ ] **Step 7: Reconectar Metabase**

Según lo decidido en la Task 16 paso 4. Con la **opción A**, que es la recomendada:

```bash
# 1. Dar al Metabase de producción acceso a la red del stack que ahora es producción
docker network connect preproduccion_datos metabase_app
docker exec metabase_app sh -c 'nc -z helipistas18_postgres 5432 && echo alcanzable'
```

2. En la UI de `metabase.helipistas.com`: **Admin → Databases → (la de Odoo) → Edit**, cambiar el host a `helipistas18_postgres`, guardar, y **Sync database schema now**.

3. Comprobar los KPIs contra las cifras anotadas en la Task 16 paso 3.

```bash
# 4. Y quitarle el acceso a la base vieja, para que no haya forma de leerla por error
docker network disconnect produccion_datos metabase_app
```

> El paso 4 no es cosmético: mientras Metabase alcance las dos bases, un error de configuración le hace servir la vieja **sin dar ningún error**, mostrando cifras desactualizadas que parecen correctas. Cortar el acceso convierte ese fallo silencioso en un error visible.

Comprobar que ya no la alcanza:

```bash
docker exec metabase_app sh -c 'nc -z -w2 helipistas_postgres 5432' \
  && echo "FALLO: sigue alcanzando la base de 17" || echo "OK: sólo ve la nueva"
```

- [ ] **Step 8: Vigilancia**

```bash
docker logs -f helipistas18_odoo 2>&1 | grep -iE 'error|traceback'
docker stats --no-stream
```

Primeras horas: log, crons corriendo, correo saliendo, n8n y Metabase vivos.

**No borrar nada de `/efs/HELIPISTAS-ODOO-17/` hasta pasadas dos semanas.** Ojo con los enlaces duros: si el filestore de 18 son enlaces al de 17, borrar el árbol de 17 no libera espacio mientras 18 los referencie —eso es bueno—, pero tampoco es un backup independiente.

- [ ] **Step 9: Rollback, si toca**

Válido sólo antes de la Puerta 3:

```bash
# 1. Devolver el router de erp.helipistas.com al stack de producción (redeploy)
# 2. Arrancar Odoo 17, que nunca se tocó
docker start helipistas_odoo
curl -o /dev/null -s -w '%{http_code}\n' https://erp.helipistas.com/web/login
```

La BD de producción no se modificó: sólo se le hizo `pg_dump`.

- [ ] **Step 10: Cerrar**

```bash
git add docs/cutover-runbook.md docs/produccion.md
git commit -m "docs: bitácora del cutover a Odoo 18 y estado final de producción"
git checkout main && git merge migracion-odoo-18
```

Y renombrar los stacks en Portainer: `preproduccion` pasa a `produccion`, o en tres meses nadie sabrá cuál es cuál.

---

## Criterio de salida

1. **Los dos entornos completos corren a la vez y se verifican lado a lado:** Odoo 17 + su PostgreSQL + su Metabase, y Odoo 18 + su PostgreSQL + `metabase_pre` apuntando al 18. Comprobado con la Task 8 paso 6, incluidas las dos rutas de PGDATA distintas.
2. **El Metabase de producción no se ha modificado** en ningún momento antes del cutover.
3. Instancia en `t3.xlarge` con Elastic IP documentada y Compose v2 instalado.
4. Cuatro stacks desplegados desde git vía Portainer, con Portainer cerrado por IP.
5. Producción por Traefik, sin nginx ni certbot y sin el cron del apaño.
6. n8n y Metabase con dominio y TLS, y los puertos 5678/3000 cerrados.
7. El H2 de Metabase fuera del contenedor, en EFS, con `MB_DB_FILE` apuntándolo.
8. Límites de cgroup verificados (`docker inspect` devuelve `mem` y `cpus` ≠ 0) y producción sin degradarse durante un ensayo.
9. Dos ensayos consecutivos de `migrar_17_a_18.sh` sin intervención manual y `verificar_migracion.py` en verde.
10. Presupuesto de la ventana con margen ×1,5 por debajo de 24 h.
11. Rollback ensayado por debajo de 1 h.
12. n8n inventariado y probado.
13. **Metabase:** preguntas inventariadas, las afectadas corregidas y **comparadas cifra a cifra entre las dos instancias**, el SQL nativo versionado, `metabase_pre` sin SMTP ni suscripciones, y decidido cuál queda como el de producción.
14. Preproducción neutralizada, con el override de `mail.mail.send()` y verificado que **no sale ningún correo**.
15. `odoo.conf` y la config del proxy **versionados**, y los secretos fuera de git.

---

## Riesgos abiertos

1. **El I/O de EFS no lo limitan los `cpu_shares`.** Producción y preproducción comparten el mismo NFS: un `pg_restore` pesado puede degradar producción por I/O aunque la CPU esté controlada. Palancas: `JOBS`, enlaces duros, ensayos fuera de horario. Si el EFS está en *Bursting* con crédito justo, hay que cambiar de modo, y tiene coste.
2. **Un solo host es un solo dominio de fallo.** Un problema del host para producción *y* preproducción a la vez, y el rollback depende de que el mismo host esté sano. Es la contrapartida aceptada de la decisión de una instancia.
3. **La opción de enlaces duros depende de un supuesto verificable pero no verificado**: que nada reescriba ficheros del filestore en el sitio. Si falla, la ventana se alarga con `rsync`.
4. **Credenciales heredadas débiles**: `admin_passwd` = `db_password`, en claro, con `list_db = True`. Los stacks nuevos lo estructuran mejor, pero **rotar las contraseñas reales sigue pendiente**.
5. **No hay CI.** Todo se apoya en que alguien ejecute los scripts y lea la salida. Un CI mínimo que haga `compileall` sobre la rama ahorraría sorpresas.
6. **Metabase puede guardar sus preguntas en H2 dentro del contenedor**, a un `docker rm` de perderse. Riesgo que existe hoy y que esta migración obliga a mirar.
7. **El análisis estático de Metabase no cubre las preguntas gráficas**, y el fallo peligroso (cifra equivocada sin error) sólo lo detecta la comparación cifra a cifra.
