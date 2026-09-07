# Metabase por HTTPS — `metabase.helipistas.com`

Cómo queda Metabase publicado en `https://metabase.helipistas.com` en lugar del
`http://54.228.16.152:3000/` que se usaba antes, y los pasos para llegar ahí.

Contexto general de la instalación de producción: [`produccion.md`](produccion.md).
Alta de usuarios, acceso con Google y permisos: [`metabase-usuarios-permisos.md`](metabase-usuarios-permisos.md).

## Estado

- **Hecho el 2026-09-07:** certificado (ya existía), virtual host en nginx y recarga.
  `https://metabase.helipistas.com` sirve certificado propio `CN=metabase.helipistas.com`
  (caducidad 2026-12-01), responde 200, y `http://` redirige 301. Verificado desde fuera.
- **Efecto colateral:** ese `nginx -s reload` cargó también los certificados renovados
  del resto. `erp.helipistas.com` pasó de servir el de caducidad 2026-10-02 al de
  2026-12-01 — ver [`produccion.md`](produccion.md), sección de certificados TLS.
- **Pendiente:** cambiar el enlace del ERP (paso 4) y cerrar el puerto 3000 (paso 5).

## Situación de partida (comprobada el 2026-09-07)

- `metabase.helipistas.com` **ya resuelve** a `54.228.16.152` (el EC2 de producción).
  El registro DNS ya estaba creado en Cloudflare, en modo *DNS only* (nube gris),
  igual que `erp.helipistas.com`. Se confirma porque resuelve a la IP del EC2: un
  registro con proxy activo devolvería una IP anycast de Cloudflare (`104.21.x` /
  `172.67.x`), que es lo que devuelve el apex `helipistas.com`.
- El puerto `3000` está abierto en el security group y responde `200` en HTTP plano.
- `https://metabase.helipistas.com` presenta el certificado de `erp.helipistas.com`
  (no hay virtual host propio, así que cae en el `server` por defecto de nginx) →
  el navegador da error de nombre de certificado.
- El contenedor `metabase_app` ya arranca con `MB_SITE_URL=https://metabase.helipistas.com`,
  o sea que la configuración ya apuntaba al destino aunque no existiera el camino.
- El enlace del ERP (menú **KPI**) apuntaba a `http://54.228.16.152:3000/`.

Conclusión: **en Cloudflare no hay nada que tocar**. Lo que falta es certificado,
virtual host en nginx, cambiar el enlace de Odoo y cerrar el puerto directo.

## Arquitectura final

```
navegador
   │  https://metabase.helipistas.com
   ▼
Cloudflare (solo DNS, nube gris — no hay proxy ni TLS de Cloudflare)
   │  A metabase.helipistas.com → 54.228.16.152
   ▼
EC2 54.228.16.152 :443
   │  helipistas_nginx — termina TLS con certificado Let's Encrypt propio
   ▼  red docker helipistas_network
metabase_app :3000  (sin puerto publicado al exterior)
   │
   ▼
helipistas_postgres :5432
   ├── metabase_config   (configuración, preguntas y dashboards de Metabase)
   └── productiu         (datos de Odoo que Metabase consulta)
```

Es exactamente el mismo patrón que `erp.helipistas.com`: TLS lo termina nginx en el
origen con un certificado Let's Encrypt, y Cloudflare solo hace de DNS autoritativo.

### Por qué nube gris y no naranja

Con nube gris no hay que cambiar nada en Cloudflare y el certificado se gestiona
igual que el del ERP, con el mismo `certbot` y la misma renovación. Si algún día se
quiere activar el proxy de Cloudflare (nube naranja) para tener WAF y ocultar la IP
de origen, el certificado de origen sigue haciendo falta (modo *Full (strict)*), y
además habría que dejar pasar el reto HTTP-01 por el puerto 80. No aporta nada hoy y
mete una pieza más en medio, así que se queda en gris.

---

## Comprobaciones previas (obligatorias)

Tres cosas que hay que mirar **antes** de empezar, porque cambian el plan si fallan.

### 1. ¿Está vivo el contenedor de certbot?

El servicio `certbot` **no tiene `restart:` en el `docker-compose.yml`**. Si en algún
momento se paró o el host reinició sin un `docker-compose up -d`, la renovación
automática lleva parada desde entonces y nadie se entera hasta que caduca.

```bash
docker ps --filter name=helipistas_certbot --format '{{.Names}} {{.Status}}'
docker exec helipistas_certbot certbot certificates
```

Si no está en marcha: `cd /efs/HELIPISTAS-ODOO-17 && docker-compose up -d certbot`.

**Resultado el 2026-09-07:** `Up 6 months`, funcionando, con **tres** certificados
válidos en disco renovados el 2026-09-02 y con caducidad 2026-12-01:
`erp.helipistas.com`, `erp17.helipistas.com` y **`metabase.helipistas.com`**.

Dos consecuencias:

1. **El certificado de Metabase ya existe.** El paso 1 de la migración no hay que
   hacerlo; queda documentado por si algún día se rehace.
2. **nginx lleva los mismos 6 meses sin recargar** y sigue sirviendo el certificado de
   `erp.helipistas.com` emitido el 2026-07-04, que caduca el **2026-10-02** — el mismo
   fallo que tumbó el ERP el 2026-08-03, otra vez en curso. El `nginx -s reload` del
   paso 2 carga de paso el certificado bueno y cierra ese riesgo gratis. Si esta
   migración no se va a hacer ahora, ejecutar igualmente:
   `docker exec helipistas_nginx nginx -s reload`.

### 2. ¿Quién más usa `54.228.16.152:3000`?

Cerrar el puerto rompe a cualquiera que lo llame por IP. El enlace del ERP ya está
cubierto, pero hay que descartar el resto:

```bash
# workflows de n8n (los guarda en PostgreSQL, no en ficheros)
docker exec -i helipistas_postgres psql -U odoo -d n8n -c \
  "SELECT id, name FROM workflow_entity WHERE nodes::text LIKE '%54.228.16.152:3000%';"

# enlaces públicos / embebidos de Metabase compartidos fuera
docker exec -i helipistas_postgres psql -U odoo -d metabase_config -c \
  "SELECT (SELECT count(*) FROM report_card     WHERE public_uuid IS NOT NULL) AS preguntas_publicas,
          (SELECT count(*) FROM report_dashboard WHERE public_uuid IS NOT NULL) AS dashboards_publicos;"
```

Si sale algo en n8n, hay que cambiar esos nodos a `http://metabase_app:3000` (llamada
interna por la red de Docker, no pasa por nginx ni por internet) antes de cerrar.

**Resultado el 2026-09-07:** `database "n8n" does not exist`. No hay nada que
comprobar del lado de n8n para esta migración, pero el hallazgo es serio por su
cuenta: el servicio declara `DB_POSTGRESDB_DATABASE=n8n` y esa base no existe, así
que o n8n no está funcionando o cayó al SQLite por defecto **dentro del contenedor**,
con sus workflows a un `docker rm` de desaparecer. Mirarlo aparte con
`docker logs helipistas_n8n`.

Los enlaces públicos de Metabase se construyen con `MB_SITE_URL`, que ya es
`https://metabase.helipistas.com`, así que esos no dependen del puerto. Lo que sí se
rompe son los **marcadores del navegador** de quien tenga guardado `IP:3000`: hay que
avisar a los usuarios, no hay redirección posible en ese puerto.

### 3. ¿El compose desplegado es igual que el del repo?

`/efs/HELIPISTAS-ODOO-17/docker-compose.yml` es una *copia* de
`dockerserver/docker-compose.yml`, y puede haber divergido.

```bash
diff /efs/HELIPISTAS-ODOO-17/docker-compose.yml \
     /efs/HELIPISTAS-ODOO-17/odoo/addons/helipistas-erp-odoo-17/dockerserver/docker-compose.yml
```

Si hay diferencias más allá del bloque de Metabase, **no copiar el fichero entero**:
editar a mano solo las dos líneas del `ports:` de Metabase en el fichero del servidor.

---

## Pasos de la migración

Todo se ejecuta en el EC2 (`ssh ec2-user@54.228.16.152`), salvo el cambio en el repo.

### 1. Certificado — YA HECHO, solo verificar

> **El certificado de `metabase.helipistas.com` ya existe** (comprobado el 2026-09-07:
> emitido, renovándose solo, caducidad 2026-12-01). Este paso se reduce a confirmarlo
> y saltar al 2. El procedimiento de emisión queda documentado abajo por si hay que
> rehacerlo.

```bash
docker exec helipistas_nginx ls -l /etc/letsencrypt/live/metabase.helipistas.com/fullchain.pem
```

<details>
<summary>Emitirlo desde cero (si algún día hiciera falta)</summary>

#### Emitir el certificado — antes de tocar nginx

**El orden importa y no es negociable.** Si se añade el `server` de `:443` antes de
que exista el certificado, `nginx -t` falla con *cannot load certificate*. Un reload
fallido no rompe nada (nginx conserva la configuración vieja), pero **un
`docker restart helipistas_nginx` en ese estado deja el contenedor sin arrancar y
tumba también `erp.helipistas.com`**. Certificado primero, siempre.

El `location /.well-known/acme-challenge/` del virtual host de `erp` está en el
`server` por defecto de nginx, así que ya sirve el reto para cualquier `Host`,
incluido `metabase.helipistas.com`. Verificado: devuelve `404` (webroot vacío), no un
`301`. Por eso el certificado se puede emitir sin tocar nginx antes: no hay bloqueo
de huevo y gallina.

```bash
# Ensayo primero, para no gastar cuota de Let's Encrypt si algo falla.
# --dry-run ejecuta el reto HTTP-01 de verdad: si pasa, el camino está validado.
docker exec helipistas_certbot certbot certonly --webroot -w /var/www/certbot \
  -d metabase.helipistas.com --dry-run

# De verdad (reutiliza la cuenta ACME ya registrada para erp.helipistas.com)
docker exec helipistas_certbot certbot certonly --webroot -w /var/www/certbot \
  -d metabase.helipistas.com -n --agree-tos

# Comprobar que el fichero existe antes de referenciarlo en nginx
docker exec helipistas_nginx ls -l /etc/letsencrypt/live/metabase.helipistas.com/fullchain.pem
```

Si pidiera un correo es que no encuentra cuenta ACME previa: añadir
`--email <correo> --no-eff-email`.

El certificado queda en `/efs/HELIPISTAS-ODOO-17/certbot/conf/live/metabase.helipistas.com/`,
que nginx ya tiene montado en `/etc/letsencrypt`. El bucle `certbot renew` del
contenedor `helipistas_certbot` lo renovará junto al del ERP sin configurar nada más.

</details>

### 2. Añadir el virtual host a nginx

Editar `/efs/HELIPISTAS-ODOO-17/nginx/conf/default.conf` (fichero del servidor, no
versionado en el repo; la copia de referencia está en [`produccion.md`](produccion.md)).

**⚠️ Ese fichero es un bind mount de un fichero suelto: Docker monta el inodo.** Si al
editarlo se sustituye por uno nuevo (`mv`, `sed -i`, `vi` con su `backupcopy=auto` por
defecto), el contenedor sigue viendo el viejo, `nginx -t` valida la configuración
antigua y el reload no hace nada, sin error visible. Editar una copia y meterla con
`cp`, que escribe dentro del mismo inodo:

```bash
cd /efs/HELIPISTAS-ODOO-17/nginx/conf
cp default.conf default.conf.bak-$(date +%F)
cp default.conf /tmp/nuevo.conf
vi /tmp/nuevo.conf
cp /tmp/nuevo.conf default.conf

# comprobar que el contenedor ve el cambio: debe dar 4, no 0
docker exec helipistas_nginx grep -c metabase.helipistas.com /etc/nginx/conf.d/default.conf
```

Al **principio** del fichero, fuera de cualquier `server`:

```nginx
# Necesario para el proxy de websockets de Metabase: "upgrade" solo cuando el
# cliente lo pide, "close" en el resto de peticiones. Va en contexto http, que es
# donde nginx incluye conf.d/*.conf — por eso puede estar aquí y no dentro de un server.
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
```

Y al **final** del fichero —después del bloque de `erp`, no antes: el primer `server`
de cada puerto es el `default_server` implícito y es el que atiende los `Host` que no
casan con nadie; ese papel debe seguir siendo del ERP— los dos `server` nuevos:

```nginx
# ---------------------------------------------------------------------------
# metabase.helipistas.com
# ---------------------------------------------------------------------------
server {
    listen 80;
    server_name metabase.helipistas.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name metabase.helipistas.com;

    client_max_body_size 100M;

    ssl_certificate     /etc/letsencrypt/live/metabase.helipistas.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/metabase.helipistas.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    add_header Strict-Transport-Security "max-age=63072000" always;

    # DNS interno de Docker + upstream en variable, a propósito: con el nombre
    # literal, nginx lo resuelve al cargar la configuración y si metabase_app está
    # parado falla con "host not found in upstream" y no arranca TODO el nginx,
    # llevándose por delante erp.helipistas.com. Así solo se cae Metabase.
    # ipv6=off porque la red no tiene IPv6 y la consulta AAAA solo añade latencia
    # o errores según la versión de Docker.
    resolver 127.0.0.11 valid=30s ipv6=off;
    set $metabase_upstream http://metabase_app:3000;

    location / {
        proxy_pass $metabase_upstream;

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_http_version 1.1;
        proxy_set_header Upgrade    $http_upgrade;
        proxy_set_header Connection $connection_upgrade;

        # Las consultas de Metabase contra productiu pueden tardar minutos
        proxy_connect_timeout 720s;
        proxy_send_timeout    720s;
        proxy_read_timeout    720s;
    }
}
```

> Contrapartida del `resolver`: con una variable en `proxy_pass`, nginx desactiva el
> `proxy_redirect default`. Aquí da igual —Metabase construye sus `Location` a partir
> de `MB_SITE_URL`, que ya es la URL correcta—, pero si `nginx -t` se quejara por
> este bloque, la alternativa es volver al literal `proxy_pass http://metabase_app:3000;`
> y quitar las dos líneas de `resolver`/`set`, asumiendo que un Metabase parado impide
> arrancar nginx.

Validar y recargar sin cortar el ERP:

```bash
docker exec helipistas_nginx nginx -t     # si falla, NO reiniciar el contenedor: arreglar el fichero
docker exec helipistas_nginx nginx -s reload
```

### 3. Comprobar

```bash
# Certificado correcto y a nombre de metabase
echo | openssl s_client -connect metabase.helipistas.com:443 \
  -servername metabase.helipistas.com 2>/dev/null \
  | openssl x509 -noout -subject -dates

# La app responde por HTTPS y HTTP redirige
curl -s -o /dev/null -w "%{http_code}\n" https://metabase.helipistas.com/
curl -s -o /dev/null -w "%{http_code} -> %{redirect_url}\n" http://metabase.helipistas.com/

# El ERP sigue en pie y con SU certificado (la recarga afecta a los dos virtual hosts)
curl -s -o /dev/null -w "%{http_code}\n" https://erp.helipistas.com/web/login
echo | openssl s_client -connect erp.helipistas.com:443 -servername erp.helipistas.com 2>/dev/null \
  | openssl x509 -noout -subject -dates
```

En el navegador, entrar y confirmar que **Admin → Configuración → URL del sitio**
muestra `https://metabase.helipistas.com`. Si no, la env `MB_SITE_URL` no llegó al
contenedor; los enlaces de alertas y suscripciones por correo saldrían con la IP.

### 4. Cambiar el enlace en Odoo

El cambio está en el repo: `addons/leulit/views/actions.xml`, acción
`leulit_20260205_1219_action` (**Open KPI**), ahora `https://metabase.helipistas.com/`.

**Para aplicarlo en producción NO uses `./upd_module.sh leulit prod`.** `leulit` es el
módulo base: **21 módulos `leulit_*` lo declaran en `depends`** (más los que dependen
de esos). Odoo, en un `-u`, marca `to upgrade` también todos los módulos dependientes,
así que un `-u leulit` no es "solo XML": es una actualización de prácticamente todo el
ERP, con los `ALTER TABLE` de cualquier cambio de esquema que haya acumulado el código
desplegado. Con producción por detrás de `main`, eso es un despliegue completo, no un
retoque de una URL.

Para una sola URL, lo proporcionado es actualizar el registro directamente:

```bash
docker exec -i helipistas_postgres psql -U odoo -d productiu <<'SQL'
UPDATE ir_act_url SET url = 'https://metabase.helipistas.com/'
 WHERE id = (SELECT res_id FROM ir_model_data
              WHERE module = 'leulit' AND name = 'leulit_20260205_1219_action');
SELECT id, name, url FROM ir_act_url
 WHERE id = (SELECT res_id FROM ir_model_data
              WHERE module = 'leulit' AND name = 'leulit_20260205_1219_action');
SQL
```

No genera divergencia: el valor que se escribe es exactamente el que tiene el XML, así
que el próximo despliegue normal de `leulit` lo reescribe igual. En el navegador hace
falta un **F5** (el cliente web de Odoo cachea las acciones cargadas en la sesión).

Vuelta atrás: el mismo `UPDATE` con `http://54.228.16.152:3000/`.

### 5. Cerrar el puerto 3000

Solo cuando HTTPS ya funcione y la comprobación previa nº 2 esté limpia. Son dos
cosas independientes y hacen falta las dos.

**a) Dejar de publicar el puerto en Docker.** Ya hecho en el repo
(`dockerserver/docker-compose.yml`, servicio `metabase`: eliminado el bloque
`ports: - "3000:3000"`). En el servidor, según lo que dijera el `diff` de la
comprobación previa nº 3: copiar el fichero, o borrar esas dos líneas a mano. Después:

```bash
cd /efs/HELIPISTAS-ODOO-17
docker-compose up -d --no-deps metabase   # --no-deps: no toca postgres ni nada más
docker port metabase_app                   # no debe imprimir nada
curl -s -o /dev/null -w "%{http_code}\n" https://metabase.helipistas.com/   # sigue 200/302
```

Recrear `metabase_app` **no pierde nada**: preguntas, dashboards, usuarios y
colecciones viven en la base `metabase_config` de PostgreSQL, no en el contenedor.

**b) Quitar la regla del security group.** Docker inserta sus reglas de publicación en
la cadena `DOCKER` de iptables, saltándose el firewall del sistema; el security group
de AWS sí filtra. Y conviene cerrarlo aunque ya no se publique el puerto, para que no
vuelva a quedar abierto si alguien reintroduce el `ports:`.

Consola AWS → EC2 → instancia `erp.helipistas.com` → *Security* → security group →
*Inbound rules* → eliminar la regla del puerto `3000`. Por CLI:

```bash
SG=$(aws ec2 describe-instances --region eu-west-1 \
      --filters "Name=ip-address,Values=54.228.16.152" \
      --query 'Reservations[].Instances[].SecurityGroups[].GroupId' --output text)

# Mirar la regla ANTES de revocar: el CIDR tiene que coincidir o el revoke falla
aws ec2 describe-security-groups --region eu-west-1 --group-ids "$SG" \
  --query 'SecurityGroups[].IpPermissions[?FromPort==`3000`]'

aws ec2 revoke-security-group-ingress --region eu-west-1 --group-id "$SG" \
  --protocol tcp --port 3000 --cidr 0.0.0.0/0
```

Después, esto debe fallar (timeout o conexión rechazada):

```bash
curl -m 8 http://54.228.16.152:3000/
```

### 6. Depurar Metabase sin el puerto abierto

Ya no se llega a `IP:3000` desde fuera. Desde el propio servidor:

```bash
docker logs -f metabase_app
docker exec metabase_app curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/api/health
```

---

## Qué puede salir mal, y vuelta atrás

Ningún paso toca datos: todo es certificado, configuración de nginx, una fila de Odoo
y una publicación de puerto. La vuelta atrás es completa en los cuatro casos.

**`nginx -t` falla tras añadir los bloques.** Casi siempre es que el certificado no
existe todavía (paso 1 sin hacer) o una llave sin cerrar. nginx sigue sirviendo con la
configuración anterior, así que no hay caída *mientras no se reinicie el contenedor*.
Arreglar el fichero o restaurar el `.bak` y volver a `nginx -t`. **Nunca**
`docker restart helipistas_nginx` con la configuración rota: ahí sí se cae el ERP.

**El reto HTTP-01 falla en el `--dry-run`.** Comprobar que el 80 sigue abierto en el
security group y que el registro DNS no se ha pasado a nube naranja (si alguien activó
el proxy de Cloudflare, el reto sigue funcionando pero el `A` ya no apunta al EC2 y
conviene decidir el modo TLS antes de seguir):
`dig +short metabase.helipistas.com` debe devolver `54.228.16.152`.

**Metabase devuelve 502 por HTTPS.** El contenedor está parado o aún arrancando (tarda
~1 min en levantar la JVM). `docker ps`, `docker logs metabase_app`. Con el `resolver`
esto afecta solo a Metabase; `erp.helipistas.com` sigue sirviendo.

**Sesión que no persiste o bucle de login en Metabase.** Señal de que Metabase no se
cree que está tras HTTPS. Revisar que `MB_SITE_URL` llegó al contenedor
(`docker inspect metabase_app --format '{{range .Config.Env}}{{println .}}{{end}}' | grep SITE_URL`)
y que nginx manda `X-Forwarded-Proto https`.

**Vuelta atrás completa** (deja las cosas como estaban):

```bash
# 1. nginx: quitar los dos server de metabase (o restaurar el .bak) y recargar
cp /efs/HELIPISTAS-ODOO-17/nginx/conf/default.conf.bak-<fecha> \
   /efs/HELIPISTAS-ODOO-17/nginx/conf/default.conf
docker exec helipistas_nginx nginx -t && docker exec helipistas_nginx nginx -s reload

# 2. republicar el puerto: devolver el bloque ports al servicio metabase y
cd /efs/HELIPISTAS-ODOO-17 && docker-compose up -d --no-deps metabase

# 3. security group: volver a autorizar el 3000
aws ec2 authorize-security-group-ingress --region eu-west-1 --group-id "$SG" \
  --protocol tcp --port 3000 --cidr 0.0.0.0/0

# 4. enlace de Odoo: el UPDATE inverso del paso 4
```

El certificado emitido puede quedarse; no molesta a nadie y caduca solo.

---

## Estado final

- `https://metabase.helipistas.com` — Metabase, TLS Let's Encrypt en nginx.
- `http://metabase.helipistas.com` — redirige 301 a HTTPS.
- `http://54.228.16.152:3000` — cerrado (ni publicado en Docker ni abierto en el SG).
- Certificado renovado por el mismo bucle `certbot renew` que el del ERP.

### Ojo con la recarga de nginx tras renovar

El contenedor `certbot` no avisa a nginx cuando renueva; nginx solo lee el certificado
al arrancar o al recargar. Esto ya provocó una caída real del ERP el 2026-08-03
(detalle en [`produccion.md`](produccion.md)). El cron mensual del host lo cubre:

```bash
0 3 1 * * docker exec helipistas_nginx nginx -s reload
```

Pero ahora ese cron es la única salvaguarda de **dos** certificados, y su margen no es
tan holgado como parece: se ejecuta el día 1 y la ventana de renovación de Let's
Encrypt se abre 30 días antes de caducar, así que un certificado que caduque a
principios de mes se recarga con horas de margen (ver el aviso de la comprobación
previa nº 1: el del ERP, con caducidad 2026-10-02 y reload el 2026-10-01, tiene un
día). Si se quiere quitar esa dependencia del calendario, el arreglo es recargar
semanalmente en vez de mensualmente:

```bash
0 3 * * 0 docker exec helipistas_nginx nginx -s reload
```

Un reload no corta conexiones ni reinicia nada, así que hacerlo más a menudo no cuesta.

## n8n: mismo problema, misma receta

`helipistas_n8n` sigue con `N8N_HOST=n8n.helipistas.com` y
`WEBHOOK_URL=https://n8n.helipistas.com/`, pero:

- `n8n.helipistas.com` **no tiene registro DNS** (a diferencia de Metabase, aquí sí
  hay que crearlo en Cloudflare: registro `A` → `54.228.16.152`, nube gris).
- Se accede por `http://54.228.16.152:5678` en HTTP plano, con el puerto abierto.

Los pasos son los mismos de este documento cambiando `metabase_app:3000` por
`helipistas_n8n:5678`, más el registro DNS previo. n8n necesita websockets sí o sí
para el editor de workflows, así que el `map $http_upgrade` es obligatorio en su caso.
Ojo además con los webhooks: si hay integraciones externas apuntando a
`http://54.228.16.152:5678/webhook/...`, cerrar el puerto las rompe y hay que
cambiarlas antes. Pendiente, no está hecho.
