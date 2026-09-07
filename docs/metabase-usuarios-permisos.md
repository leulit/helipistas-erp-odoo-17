# Metabase — usuarios, acceso y permisos

Quién puede entrar en `https://metabase.helipistas.com`, cómo se le da de alta y cómo
se le asigna lo que puede ver y hacer.

Edición: **Metabase Community (open source)**, v0.63.16.6. Eso condiciona buena parte
de lo que sigue — ver *Lo que Community no te da*.

Publicación del servicio, TLS y despliegue: [`metabase-https.md`](metabase-https.md).

---

## 1. Cómo se entra: Google Sign-In

La autenticación con Google **ya está configurada** (client ID
`1026694880961-...apps.googleusercontent.com`, `google-auth-enabled = true`).

> **Por qué antes no funcionaba y ahora sí.** El cliente OAuth de Google valida el
> **origen** desde el que se carga la página. El origen autorizado era
> `https://metabase.helipistas.com`, no `http://54.228.16.152:3000`. Mientras se
> accedía por IP, el botón de Google fallaba; desde que existe el dominio, funciona.
> No hubo que tocar nada en Google Cloud Console.

### El campo que decide quién entra

**Dónde está:** *Admin (rueda dentada) → Configuración → Autenticación →
**Autenticación de Google***. En esa pantalla, **debajo del Client ID**, hay un campo
de dominio. Según la versión aparece como **"Dominio"** o con el texto de ayuda
*"Permitir que los usuarios se registren por su cuenta si su dirección de Google
pertenece a este dominio"*.

**Es un interruptor de dos posiciones:**

- **Vacío** → Google sirve solo para identificarse. Entra **únicamente quien ya tiene
  cuenta creada en Metabase con ese mismo correo**. Es una lista blanca: tú decides
  quién entra, uno a uno. *Esta es la configuración recomendada.*
- **Con `helipistas.com`** → cualquiera con correo de ese dominio se crea la cuenta
  solo, sin que tú intervengas. No hay término medio: la documentación oficial es
  explícita en que no se pueden admitir personas concretas en lugar del dominio entero.

La documentación lo dice así para el caso del campo vacío: *"existing Metabase users
signed in to a Google account that matches the email they used to set up their
Metabase account will be able to sign in with just a click"*.

### Sí, con el campo vacío se sigue usando Google para entrar

Es la duda que surge siempre, porque el botón **"Iniciar sesión con Google" aparece en
la pantalla de login para todo el mundo**. Son dos cosas distintas:

- **Autenticación** — *¿quién eres?* Lo hace Google. El botón está siempre visible.
- **Aprovisionamiento** — *¿se te crea una cuenta si no la tienes?* Es lo único que
  controla el campo de dominio.

Con el campo vacío, al pulsar el botón:

- **Persona con cuenta ya creada** → Google confirma su identidad, Metabase encuentra la
  cuenta con ese correo → **entra de un clic, sin contraseña**.
- **Persona sin cuenta** → Google confirma su identidad igual, pero Metabase no
  encuentra cuenta con ese correo **y no la crea** → no entra.

Todos se identifican con Google; solo entran los que están dados de alta. Que el botón
esté visible no es una filtración: simplemente falla para quien no está en la lista.

### Comprobar el valor actual sin depender de la interfaz

El ajuste no se expone en la API pública, pero está en la base de configuración:

```bash
docker exec -i helipistas_postgres psql -U odoo -d metabase_config -c \
  "SELECT key, value FROM setting WHERE key LIKE 'google%';"
```

La clave es **`google-auth-auto-create-accounts-domain`**. Si no aparece o está vacía,
estás en modo lista blanca. Si trae `helipistas.com`, el alta es automática para toda
la empresa.

> Motivo adicional para dejarlo vacío: la documentación no aclara qué ocurre si una
> persona **desactivada** intenta entrar con el alta automática encendida. Con el campo
> vacío esa duda no existe.

---

## 2. Alta y baja de personas

### Alta

*Admin → Personas → **Invitar a alguien***:

1. Nombre, apellidos y **el correo exacto de su cuenta de Google** (`@helipistas.com`).
   Si no coincide carácter por carácter, el Sign-In no la reconocerá.
2. En ese mismo diálogo se le marcan ya los grupos (ver sección 4).
3. Metabase mostrará una **contraseña temporal**. **Ignórala**: esa persona entrará con
   el botón de Google y no la usará nunca.

Por eso no tener SMTP configurado no impide dar de alta a nadie.

> `email-configured? = false`: Metabase **no puede enviar correo**. Además de las
> invitaciones, eso deja fuera las **suscripciones a dashboards y las alertas**. Si
> hacen falta, hay que configurar SMTP en *Admin → Configuración → Correo electrónico*;
> es independiente del resto de este documento.

### Baja

*Admin → Personas → ⋮ → **Desactivar***. Deja de poder entrar aunque su cuenta de
Google siga activa.

**Desactivar, no borrar.** Así se conserva la autoría de sus preguntas y dashboards.

---

## 3. Cómo funcionan los permisos

**Todo va por grupos. A una persona nunca se le asignan permisos directamente.**

### Las dos trampas

**"Todos los usuarios" es un suelo, no un grupo más.** Nadie puede salir de él. Lo que
concedas ahí lo tiene todo el mundo, esté en los grupos que esté. Por eso ese grupo
debe quedar en el mínimo, y hay que cerrarlo **antes** de dar de alta a nadie.

**Los permisos se suman y gana el más permisivo.** Quien está en dos grupos obtiene lo
mejor de ambos. **Un grupo nunca quita permisos, solo los da.** Es el error clásico:
crear un grupo "restringido" no restringe nada si la persona sigue en otro más abierto.

### Los dos ejes

Son independientes y se configuran en sitios distintos:

- **Datos** — *Admin → Permisos → Datos*: a qué base de datos puede lanzar consultas y
  si puede escribir SQL nativo.
- **Colecciones** — *Admin → Permisos → Colecciones*: qué dashboards y preguntas ve.

### Lo que Community no te da

- **"View data"** no aparece siquiera en el panel de permisos. La documentación:
  *"Since the setting's options aren't available in the OSS version, Metabase will only
  display this View data setting in the Pro/Enterprise version."*
- **Permisos por tabla o esquema** (opción *Granular*): de pago.
- **Seguridad por filas** (que un piloto vea solo sus horas): de pago.
- **Forzar SSO** desactivando el login por contraseña: de pago
  (`can-disable-password-login? = false`).
- **2FA**: de pago (`enable-multi-factor-auth? = false`).

**Dos consecuencias prácticas que hay que tener claras:**

1. Quien pueda consultar `productiu` **puede consultar todas sus tablas**. No se pueden
   esconder unas y enseñar otras. **La segmentación por departamento se hace con
   colecciones**, no con permisos de datos.
2. Un dato que no deba ver alguien no se protege con permisos: o se expone ya filtrado
   en una pregunta, o no se expone.

Lo que **sí** tienes: **Create queries** por grupo y base de datos, con *Query builder
and native* / *Query builder only* / *No*. Solo la variante *Granular* lleva candado.

---

## 4. Estructura de grupos propuesta

Deliberadamente **no** replica los grupos del ERP. Según
[`roles-autorizaciones.md`](roles-autorizaciones.md), allí conviven cuatro vocabularios
de roles y la jerarquía no modela la organización real; importarlo traería el problema.
Aquí lo que manda es qué datos necesita ver cada uno.

### Capa 1 — capacidad (eje de datos)

Configurar en *Admin → Permisos → Datos → `productiu`*, columna **Create queries**:

- **Todos los usuarios** → `No`
- **Consulta** → `Query builder only` — la mayoría de la gente: construye preguntas, no
  escribe SQL
- **Analistas** → `Query builder and native` — tres o cuatro personas como mucho
- **Administrators** (grupo integrado) → acceso total, cuantos menos mejor

### Capa 2 — departamento (eje de colecciones)

Una colección por departamento, y a cada grupo **Ver** sobre la suya (**Curar** a quien
deba crear dashboards ahí). Los demás grupos, **Sin acceso**.

Operaciones · Taller/CAMO · Escuela · Calidad y Seguridad · Almacén · Comercial · Dirección

Estos grupos **no tocan el eje de datos**. Solo colecciones.

### Alta de una persona, entonces

1. Entra por Google (su cuenta ya existe porque la creaste tú).
2. *Admin → Personas* → añadirla a **un grupo de capacidad** + **su departamento**.

---

## 5. Orden de implantación

1. *Admin → Autenticación → Autenticación de Google*: confirmar que el campo de
   dominio está **vacío** (o vaciarlo).
2. *Admin → Permisos → Datos → `productiu`*: **Todos los usuarios → `No`**.
3. Crear los grupos de capacidad y asignarles su *Create queries*.
4. Crear las colecciones por departamento y sus grupos, con Ver/Curar.
5. Dar de alta a **una** persona y probar con ella antes de seguir.

El paso 2 va antes de cualquier alta a propósito: con *Todos los usuarios* permisivo,
cualquiera que entre tiene acceso completo hasta que lo cierres.

---

## 6. La conexión a `productiu`: el control que no depende de la licencia

Comprobar con qué rol de PostgreSQL se conecta Metabase (no imprime la contraseña):

```bash
docker exec -i helipistas_postgres psql -U odoo -d metabase_config -c \
  "SELECT id, name, engine, details::json->>'user' AS db_user, details::json->>'dbname' AS dbname FROM metabase_database;"
```

Si sale `odoo` —el dueño de todas las tablas— cualquiera con *Query builder and native*
puede ejecutar `DELETE`, `UPDATE` o `DROP` contra producción desde el editor SQL de
Metabase. Los permisos de Metabase son la única barrera, y en Community son gruesos.

El arreglo estructural es un rol de solo lectura:

```sql
CREATE ROLE metabase_ro LOGIN PASSWORD '<una buena>';
GRANT CONNECT ON DATABASE productiu TO metabase_ro;
GRANT USAGE ON SCHEMA public TO metabase_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO metabase_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO metabase_ro;
```

Luego cambiar el usuario en *Admin → Bases de datos → `productiu`*. Con esto da igual
qué permisos tenga nadie en Metabase: PostgreSQL no deja escribir. **Es el único
control de esta lista que no depende de la edición.**

---

## 7. Pendiente

- Decidir y aplicar el rol `metabase_ro` (sección 6).
- Subir `password-complexity` (hoy 6 caracteres, 1 dígito) en *Admin → Configuración →
  General*. Al no poder desactivar el login por contraseña en Community, es la única
  palanca sobre esa vía de entrada.
- Configurar SMTP si se quieren suscripciones y alertas por correo.
