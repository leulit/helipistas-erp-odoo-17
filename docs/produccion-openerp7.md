# OpenERP 7 legacy (erp2021.helipistas.com)

Este documento describe el entorno legacy de OpenERP 7, mantenido **solo para consulta de datos históricos** (auditoría, informes puntuales, conservación legal). No es el sistema operativo del día a día — eso es el ERP nuevo documentado en [`produccion.md`](./produccion.md). No recibe despliegues regulares: se toca a mano y de forma puntual cuando surge algo concreto.

## Resumen

- **Orquestación:** Docker Compose (`/root/docker-compose.yml`, solo en el servidor — no versionado en ningún repo)
- **Aplicación y base de datos en servidores EC2 separados**
- **TLS:** terminado por Cloudflare (proxy naranja), no por el servidor
- **Último despliegue de código:** commit del 2022-02-26 en la rama `002021-06-PROD`

## Infraestructura AWS

### Servidor de aplicación (OpenERP + nginx)

- **Instancia EC2:** `erp2021.helipistas.com` (`18.203.113.0`), tipo `t3a.large`, región `eu-west-1` (AZ `eu-west-1a`). Security groups: consultar consola AWS, no versionados aquí.
- **Acceso SSH:** mismo patrón que el ERP nuevo — usuario `ec2-user`, key pair (`.pem`), directo a la IP anterior (sin bastion).
- **Disco:** EBS local, sin EFS.
  ```
  /dev/nvme0n1p1   24G  7.9G   17G  33%  /                    (raíz)
  /dev/nvme2n1     20G   18G  636M  97%  /mnt/filestore        (⚠️ ver Pendiente)
  ```

### Servidor de base de datos

- **Instancia EC2 separada:** `18.200.222.88`. Tipo de instancia, región y acceso SSH no verificados en esta sesión — consultar consola AWS.
- Antes de apuntar a esta IP directa, el `db_host` apuntaba a hostnames RDS (`openerp-t2.cizigbklkky2.eu-west-1.rds.amazonaws.com`, `helipistasopenerpbak.cshppjv8x6y3.eu-west-1.rds.amazonaws.com`), ahora comentados en la config — en algún momento se migró la BD fuera de RDS a esta EC2 propia con Postgres instalado directamente.
- **Backups:** no verificado — ni de esta EC2, ni de la BD, ni del filestore. Ver Pendiente.

## Ubicación de ficheros en el servidor (aplicación)

Sin EFS: todo vive en disco local del EC2 de aplicación, montado por bind mount directo en `/root/docker-compose.yml` (no hay un directorio "raíz de despliegue" único como en el ERP nuevo):

```
/app/erp                       # checkout git del código custom (ver Despliegue) → bind mount al contenedor
/mnt/filestore/productiu       # filestore de la BD "productiu" (EBS al 97%, ver Pendiente) → bind mount al contenedor
/root/estable_70.conf          # config de OpenERP (credenciales incluidas) → bind mount solo lectura al contenedor
/root/docker-compose.yml       # definición de los contenedores
/root/nginx-proxy.conf         # config de nginx, bind mount al contenedor nginx-proxy
```

## Contenedores

`/root/docker-compose.yml`, tal cual está en el servidor (no versionado en ningún repo):

```yaml
version: '3'
services:
  erphelipistas:
    container_name: erphelipistas
    image: 663007906241.dkr.ecr.eu-west-1.amazonaws.com/helipistas_openerp:v_7.3
    restart: unless-stopped
    ports:
      - 8069:8069
    entrypoint: ["./entrypoint.sh"]
    volumes:
      - /app/erp:/home/openerp/instancias/estable/odoo/server/addons/helipistas
      - /root/estable_70.conf:/home/openerp/instancias/config/estable_70.conf:ro
      - /mnt/filestore/productiu:/home/openerp/instancias/estable/odoo/server/openerp/filestore/productiu/
    logging:
      driver: "json-file"
      options:
        max-size: "100k"
        max-file: "3"
  proxy-server:
      image: nginx
      container_name: nginx-proxy
      restart: unless-stopped
      depends_on:
        - erphelipistas
      ports:
        - "80:80"
      volumes:
        - /root/nginx-proxy.conf:/etc/nginx/nginx.conf:ro
      logging:
        driver: "json-file"
        options:
             max-size: "100k"
             max-file: "3"
```

| Servicio | Imagen | Contenedor | Puertos | Descripción |
|---|---|---|---|---|
| `erphelipistas` | `663007906241.dkr.ecr.eu-west-1.amazonaws.com/helipistas_openerp:v_7.3` (ECR) | `erphelipistas` | `8069:8069` | OpenERP 7 (app + gestión interna de OpenERP, supervisor arranca el proceso Python vía `service openerp-server restart`) |
| `proxy-server` | `nginx` | `nginx-proxy` | `80:80` | Proxy inverso — solo HTTP, el TLS lo pone Cloudflare por delante |

`restart: unless-stopped` en ambos: sobreviven a un reinicio del daemon Docker/EC2 sin intervención manual.

## Base de datos

Conexión definida en `/root/estable_70.conf` (bind mount de solo lectura dentro del contenedor, ver arriba):

```
db_host = 18.200.222.88
db_maxconn = 64
db_password = helipistas-openerp
db_port = 5462
db_template = template1
db_user = helipistas
dbfilter = productiu
admin_passwd = ealvarezheli
```

> Contraseñas en claro tanto en el fichero de config del servidor como en este documento — mismo criterio que el `docker-compose.yml` del ERP nuevo (ver "Pendiente" en `produccion.md`). `admin_passwd` es la contraseña maestra de administración de OpenERP (creación/gestión de bases de datos), no la de un usuario de la app.

Puerto `5462` (no el estándar `5432`) y BD en otra EC2 con Postgres instalado directamente (no RDS, ver Infraestructura).

## Dominio y TLS

- **Dominio:** `erp2021.helipistas.com` → registro DNS con proxy de Cloudflare activo (nube naranja), apuntando a `18.203.113.0`.
- **TLS:** lo termina Cloudflare, no el servidor. `nginx-proxy` solo escucha en el puerto 80 (HTTP plano) y no tiene ningún certificado propio configurado.
- **Config nginx** (`/root/nginx-proxy.conf`, solo el `server{}` relevante):
  ```nginx
  upstream erphelipistas {
    server erphelipistas:8069;
  }

  server {
      listen 80;
      server_name erp2021.helipistas.com;
      location / {
          proxy_pass http://erphelipistas/;
          proxy_http_version 1.1;
          proxy_set_header Upgrade $http_upgrade;
          proxy_set_header Connection 'upgrade';
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP  $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_cache_bypass $http_upgrade;
          proxy_read_timeout 300000;
      }
  }
  ```

## Despliegue / actualización

Ya no hay despliegues regulares — solo intervención manual y puntual cuando hace falta.

- **Código:** `/app/erp` en el servidor de aplicación es un checkout git de `https://bitbucket.org/ealvarezreb/openerp.git`, rama `002021-06-PROD`. Último commit desplegado: `6df75b6` (2022-02-26).
- El working tree del servidor tiene cambios **sin commitear** respecto a ese commit (`modules/hlp_herramienta/herramienta.xml`, `openerp-server.conf` modificados, y un binario suelto `a.out` sin trackear) — indica que en algún momento se editó código directamente en el servidor sin pasar por git. Si se retoma este entorno, revisar y reconciliar esos cambios antes de asumir que el código coincide con lo que hay en Bitbucket.
- **Imagen Docker:** viene de ECR (`helipistas_openerp:v_7.3`); no hay Dockerfile ni pipeline de build visible en este repo ni en el servidor — para reconstruirla habría que localizar de dónde salió esa imagen originalmente (no documentado).
- No hay pipeline de CI/CD, igual que en el ERP nuevo.

## Pendiente

- **`/mnt/filestore` al 97% (636M libres):** riesgo de quedarse sin espacio; revisar antes de que falle una escritura de adjunto.
- **Backups no verificados:** ni de la BD (`18.200.222.88`), ni del filestore, ni de la EC2 de aplicación. Confirmar si existe algo (AWS Backup, snapshot EBS, dump de Postgres) o asumir que no hay ninguno.
- **Servidor de BD (`18.200.222.88`):** tipo de instancia, región, acceso SSH y responsable de mantenimiento no documentados aquí.
- **Cambios sin commitear en `/app/erp`** (ver Despliegue): reconciliar con Bitbucket si se vuelve a tocar este entorno.
- **Origen de la imagen `helipistas_openerp:v_7.3` en ECR:** no hay Dockerfile ni proceso de build documentado; si hiciera falta reconstruirla, no está claro cómo.
- Security groups de la EC2 de aplicación: no versionados aquí, consultar consola AWS.
- Sin plan de apagado formal — se mantiene vivo solo para consulta histórica, sin fecha de fin decidida.
