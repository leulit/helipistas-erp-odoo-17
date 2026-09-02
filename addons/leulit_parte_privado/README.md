# leulit_parte_privado

## Qué es

Módulo aditivo que transcribe al ERP el parte de vuelo (PTV) en papel de un
piloto privado. Un usuario autorizado rellena un wizard simplificado ("Parte
piloto privado") y, al pulsar **Finalizar**, el vuelo recorre el ciclo
completo — creación → firma prevuelo→postvuelo → firma postvuelo→cerrado —
generando y firmando POV, PTV (y F27 si aplica) **como si los hubiera hecho
el propio piloto**. No modifica nada del workflow ni del código actual de
vuelos: reutiliza los handlers y la maquinaria de firma existentes
importándolos, nunca editándolos.

## Quién lo usa

Grupo nuevo `Parte piloto privado` (`leulit.ROperaciones_parte_privado`, en
`leulit/groups.xml`). No implica ningún otro rol de operaciones: quien lo
tenga ve únicamente el menú nuevo, más lo que ya viera por otros grupos.

Nota: el menú "Partes de vuelo" (bajo Vuelos) no lleva grupos, así que un
usuario con solo este grupo también lo verá junto al wizard nuevo. No es un
permiso que otorgue este módulo: ese menú no está restringido por grupo.

## Prerequisitos de datos

- **Piloto**: marcar el check "Piloto privado" (`privado`) en su ficha, y
  tener un `res.users` activo enlazado a su `partner_id` (si no lo tiene, el
  wizard no puede firmar en su nombre y lo indica con un error claro). Si
  puede volar el EC120B, necesita firma escaneada en ficha (`piloto.firma`)
  para el F27 automático.
- **Helicóptero**: operativo (sin estar en taller ni con anomalías sin
  firmar), con `consumomedio` y `velocidad` informados en ficha, y horas de
  potencial remanentes suficientes para el vuelo.
- **Presupuesto**: un `sale.order` NCO en estado `sale`, con
  `flag_flight_part=True` y `task_done=False`.
- **Descansos**: los descansos del piloto deben cuadrar con datos reales — la
  cadena B (postvuelo→cerrado) los valida igual que en el flujo normal.
- **Orden cronológico**: la cadena rechaza cualquier parte que quede por
  detrás en el tiempo de otro parte ya en postvuelo o cerrado de la misma
  máquina. Los partes privados de una misma máquina deben introducirse en
  orden cronológico real, uno detrás de otro.

## Flujo de `finalizar()`

1. Resuelve el usuario activo del piloto (`partner_id.user_ids`); sin
   usuario, `UserError`.
2. Crea el `leulit.vuelo` con `with_user(usuario_piloto)`, para que
   `create_uid` y el chatter queden a nombre del piloto.
3. Llama a `onchange_helicoptero()` (pesos, velocidad, consumo, tacom/fuel
   del último vuelo cerrado) y reescribe `lugarsalida`, porque el onchange lo
   pisa con la llegada del vuelo anterior.
4. Llama a `calculosFuel('tiempoprevisto')` (distancia, hora de llegada
   prevista, combustibles).
5. Ejecuta la **cadena paralela A** (prevuelo→postvuelo): handlers
   importados de `vuelo_chain_postvuelo.py` más `DatosGeneralesPrivadoHandler`
   propio, que reproduce los mismos checks del original salvo meteo, C.G.,
   performance y pasajeros W&B.
6. Firma 1 (`with_user` del piloto): estado pasa a `postvuelo`, se generan y
   firman POV y PTV con el OTP real del piloto (`get_otp()` +
   `buildSignature` + `buildPdfSigned`); F27 automático si es EC120B con
   `checklist_prevuelo_BFF`.
7. Ejecuta la **cadena paralela B** (postvuelo→cerrado): handlers importados
   de `vuelo_chain_cerrado.py` tal cual.
8. Comprueba `verificar_actividad_aerea()` del partner del piloto.
9. Firma 2: estado pasa a `cerrado`, `control_firma='firmado'`.
10. Deja traza (ver más abajo) y cierra el wizard.

## Qué se omite y por qué

Todo lo que un parte NCO transcrito desde papel no necesita ni puede
rellenar de forma fiable:

- **Meteo**: la cadena original la exige a todos los vuelos; el handler
  nuevo del flujo paralelo no la comprueba, y el campo queda vacío.
- **W&B (masa y centrado)**: el PTV en papel lleva estos datos manuscritos;
  no se piden en el wizard ni los valida la cadena.
- **Performance**: igual que W&B, no se comprueba en este flujo.
- **Perfiles de formación**: omitido de momento (decisión del usuario,
  2026-09-01); reactivable en el futuro añadiendo el handler importado a
  `chains/vuelo_chain_privado.py` — un import y un eslabón más en la lista.
- **Parte de escuela**: no aplica, el flujo es NCO privado, sin escuela.

## Qué queda si falla

No hay rollback total posible sin editar los handlers de
`vuelo_chain_postvuelo.py` / `vuelo_chain_cerrado.py`, porque varios de ellos
hacen `cr.commit()` internamente. Si un eslabón falla tras el primer commit,
el wizard captura la excepción, hace `rollback()` al último commit y, si el
vuelo sigue existiendo y no llegó a `cerrado`, lo deja en estado
**`cancelado`** (con el motivo del fallo en `comentarios`) para no bloquear
el helicóptero ni el piloto — y **relanza el error original** para que el
usuario vea qué pasó.

## Trazabilidad

- Campo `privado_introducido_por` (Many2one a `res.users`, en
  `leulit.vuelo`) queda con el usuario autorizado real que rellenó el
  wizard, no el piloto.
- Nota en el chatter del vuelo: "Parte introducido por {usuario} mediante
  Parte piloto privado en nombre de {piloto}".

Con esto, aunque la firma y el `create_uid` queden a nombre del piloto (para
que la maquinaria de firma funcione igual que en el flujo normal), siempre es
reconstruible quién transcribió realmente cada parte.

## Instalación, actualización y tests

Sin Odoo local en este entorno; ejecutar en el Docker de pruebas del
usuario:

```bash
./upd_module.sh leulit dev
docker exec -ti helipistas_odoo_17 odoo -i leulit_parte_privado -d productiu --stop-after-init
docker exec -ti helipistas_odoo_17 odoo -u leulit_parte_privado -d productiu --test-enable --test-tags=/leulit_parte_privado --stop-after-init
```

Manual: marcar "Piloto privado" en la ficha de un piloto con usuario activo;
dar el grupo "Parte piloto privado" a un usuario; ir a Operaciones > Vuelos >
Parte piloto privado; rellenar y Finalizar; comprobar que el vuelo queda en
`cerrado`/`firmado`, con POV y PTV generados, y la nota correspondiente en el
chatter.
