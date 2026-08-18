# App móvil "Parte de Vuelo" (`leulit.vuelo`) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir una app Flutter para Android e iOS que permita crear, editar, firmar y cerrar partes de vuelo (`leulit.vuelo`) contra el Odoo 17 de Helipistas, replicando el formulario web completo.

**Architecture:** MVVM sobre primitivas del SDK de Flutter (View → ViewModel → Repository → Service), sin gestor de estado externo. El estado de negocio vive en Odoo: la app es un cliente fino que delega **todos** los cálculos derivados en el endpoint `onchange` del servidor y replica en cliente solo lo necesario para feedback inmediato y para el cálculo de envolventes del Weight & Balance (que en el ERP vive en JavaScript de navegador y no existe en el servidor).

**Tech Stack:** Flutter 3.x · Dart 3 · `http` + `CookieJar` para JSON-RPC · `leulit_flutter_fullresponsive` para dimensionado · `flutter_test` para tests. Sin base de datos local, sin gestor de estado de terceros, sin generación de código.

**Spec:** `docs/superpowers/specs/2026-08-18-app-parte-vuelo-spec.md` — **de lectura obligatoria antes de la Task 1.** Cada tarea remite a secciones concretas (`§n`) de ese documento; las reglas de negocio no se repiten aquí.

---

## Global Constraints

- **Odoo 17 Community.** No usar modelos ni funcionalidades Enterprise.
- **Endpoint:** `https://erp.helipistas.com`. La base de datos se configura, no se hardcodea.
- **Siempre online.** No hay cache local, ni cola de escritura, ni resolución de conflictos.
- **El servidor manda.** Todo campo derivado se obtiene del endpoint `onchange` (spec §11.4). Las fórmulas replicadas en cliente (Task 3, Task 4) existen para dar feedback inmediato y para tests de equivalencia, nunca como fuente del valor persistido.
- **Excepción única:** los cuatro `valid_*cg` del Weight & Balance se calculan en cliente (spec §9.4) porque en el ERP los calcula JavaScript de navegador.
- **Prohibido el formateo automático.** No ejecutar `dart format`, ni configurar hooks/CI que lo hagan. Imitar el estilo del código circundante.
- **Permitido y recomendado:** `dart analyze` y `flutter test`. Cada tarea termina con ambos en verde.
- **Dimensionado:** siempre vía `leulit_flutter_fullresponsive` (`.w` / `.h` / `.sp` o `rw()` / `rh()` / `rsp()`). Nunca `MediaQuery` manual.
- **Mensajes de error:** los `UserError` de Odoo se muestran **íntegros y en castellano**, sin reescribir ni resumir. Son texto normativo para el piloto.
- **No inventar validaciones.** Si el ERP no valida algo (spec §12.1), la app tampoco.
- **Firma:** el piloto **teclea** el código OTP (spec §8.2). Prohibido autocompletar el campo
  con el código mostrado, permitir pegarlo, o enviar `otp = notp` automáticamente.
- **Lista:** solo partes donde el usuario es `piloto_id` o `piloto_supervisor_id`
  (spec §15.1). Sin conmutador "ver todos". Nunca usar el campo `user_vuelo_ids`.
- **Technical Log y anomalías:** solo lectura, filas **no pulsables** (spec §4.1 D y E). No
  se abre la ficha de `leulit.anomalia` ni la de `leulit.anotacion_technical_log`, aunque el
  ERP web sí lo permita. `anotacion_ids` y `diferido_ids` son `compute` sin `inverse`: jamás
  se envían en `create` ni en `write`.
- **Idioma de la UI:** castellano, con las etiquetas exactas del formulario web (spec §4).

---

## File Structure

```
lib/
  main.dart                                 arranque, ScreenSizeInitializer, rutas
  config/
    app_config.dart                         baseUrl, db, timeouts
  core/
    odoo/
      odoo_client.dart                      transporte JSON-RPC + sesión + mapeo de errores
      odoo_exception.dart                   jerarquía UserError/ValidationError/AccessError/SessionExpired
      odoo_action.dart                      parseo de ir.actions.* devueltas por botones
    util/
      float_time.dart                       conversiones HH:MM ↔ float (spec §6.7)
      unit_convert.dart                     litros↔kg/gal, kt↔m/s, NM↔m (spec §6.6)
      result.dart                           Result<T> / Command
  domain/
    vuelo.dart                              modelo Vuelo (de/serialización)
    vuelo_enums.dart                        Estado, EstadoVista, ControlFirma, HelicopteroTipo...
    ref.dart                                Ref (par [id, display_name] de Odoo)
    vuelo_tipo_line.dart
    aerovia_line.dart
    silabus_line.dart
    weight_and_balance.dart
    performance.dart
  data/
    vuelo_repository.dart                   searchRead/read/create/write/onchange/callButton
    catalog_repository.dart                 name_search de m2o con sus domains
    signature_repository.dart               codeFromServer / checksignatureRef
    wb_repository.dart                      lectura y guardado del W&B
  feature/
    login/            login_view.dart, login_viewmodel.dart
    lista/            lista_view.dart, lista_viewmodel.dart
    parte/
      parte_viewmodel.dart                  estado del formulario + onchange + guardado
      parte_shell_view.dart                 cabecera, selector de pantalla, barra de acciones
      prevuelo_view.dart                    pantalla 1 (spec §4.1)
      prevuelo2_view.dart                   pantalla 2 (spec §4.2)
      postvuelo_view.dart                   pantalla 3 (spec §4.3)
      cerrado_view.dart                     pantalla 4 (spec §4.4)
      pie_comun_view.dart                   pie común (spec §4.5)
      widgets/
        float_time_field.dart
        semaforo_indicator.dart
        m2o_picker_field.dart
        fuel_card.dart                      litros + kg/gal colapsables
    escuela/          escuela_view.dart, escuela_viewmodel.dart
    wb/               wb_view.dart, wb_viewmodel.dart, wb_envelopes.dart
    performance/      performance_constants.dart (generado), performance_math.dart,
                      performance_painter.dart, performance_render.dart,
                      performance_viewmodel.dart, performance_view.dart
    firma/            firma_view.dart, firma_viewmodel.dart
test/
  core/util/float_time_test.dart
  core/util/unit_convert_test.dart
  core/odoo/odoo_client_test.dart
  domain/vuelo_test.dart
  data/vuelo_repository_test.dart
  feature/parte/fuel_engine_test.dart
  feature/performance/performance_math_test.dart
  feature/performance/performance_render_test.dart
  feature/wb/wb_envelopes_test.dart
  feature/parte/parte_viewmodel_test.dart
```

Un fichero, una responsabilidad. Las vistas de pantalla no superan las ~400 líneas: si un bloque de la spec §4 crece, se extrae a `widgets/`.

---

## Task 1: Bootstrap del proyecto y configuración

**Files:**
- Create: `pubspec.yaml`
- Create: `lib/config/app_config.dart`
- Create: `lib/main.dart`
- Test: `test/config/app_config_test.dart`

**Interfaces:**
- Consumes: nada.
- Produces: `AppConfig({required String baseUrl, required String db})`, `AppConfig.fromEnvironment()`.

- [ ] **Step 1: Crear el proyecto**

```bash
flutter create --org com.helipistas --platforms=android,ios parte_vuelo_app
cd parte_vuelo_app
flutter pub add http cookie_jar
flutter pub add leulit_flutter_fullresponsive
```

Si `leulit_flutter_fullresponsive` no está publicado en pub.dev, añadirlo como dependencia git o path en `pubspec.yaml` según cómo lo consuman los demás proyectos de la casa.

- [ ] **Step 2: Escribir el test que falla**

`test/config/app_config_test.dart`:
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:parte_vuelo_app/config/app_config.dart';

void main() {
  test('baseUrl sin barra final', () {
    final cfg = AppConfig(baseUrl: 'https://erp.helipistas.com/', db: 'productiu');
    expect(cfg.baseUrl, 'https://erp.helipistas.com');
  });

  test('endpoint compone la ruta', () {
    final cfg = AppConfig(baseUrl: 'https://erp.helipistas.com', db: 'productiu');
    expect(cfg.endpoint('/web/dataset/call_kw').toString(),
        'https://erp.helipistas.com/web/dataset/call_kw');
  });
}
```

- [ ] **Step 3: Ejecutar el test y verificar que falla**

Run: `flutter test test/config/app_config_test.dart`
Expected: FAIL — `Target of URI doesn't exist: app_config.dart`

- [ ] **Step 4: Implementación mínima**

`lib/config/app_config.dart`:
```dart
class AppConfig {
  AppConfig({required String baseUrl, required this.db})
      : baseUrl = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl;

  final String baseUrl;
  final String db;

  Uri endpoint(String path) => Uri.parse('$baseUrl$path');

  factory AppConfig.fromEnvironment() => AppConfig(
        baseUrl: const String.fromEnvironment('ODOO_URL', defaultValue: 'https://erp.helipistas.com'),
        db: const String.fromEnvironment('ODOO_DB', defaultValue: 'productiu'),
      );
}
```

- [ ] **Step 5: Ejecutar el test y verificar que pasa**

Run: `flutter test test/config/app_config_test.dart` → PASS
Run: `dart analyze` → sin errores

- [ ] **Step 6: Commit**

```bash
git add pubspec.yaml lib/config/app_config.dart test/config/app_config_test.dart lib/main.dart
git commit -m "feat: bootstrap app parte de vuelo con configuracion de entorno"
```

---

## Task 2: Utilidades de tiempo (`float_time`)

Es la conversión más usada de toda la app y la que más errores de redondeo genera. Se implementa primero y con tests exhaustivos.

**Files:**
- Create: `lib/core/util/float_time.dart`
- Test: `test/core/util/float_time_test.dart`

**Interfaces:**
- Produces:
  - `({int horas, int minutos}) floatTimeConvert(double v)`
  - `String floatTimeToStr(double? v)`
  - `int floatTimeToMinutes(double v)`
  - `String floatMinutesToStr(double v)`
  - `double strToFloatTime(String hms)`

- [ ] **Step 1: Escribir el test que falla**

`test/core/util/float_time_test.dart`:
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:parte_vuelo_app/core/util/float_time.dart';

void main() {
  test('floatTimeToStr casos canonicos', () {
    expect(floatTimeToStr(2.5), '02:30');
    expect(floatTimeToStr(0.0), '00:00');
    expect(floatTimeToStr(null), '00:00');
    expect(floatTimeToStr(1.99), '01:59');
  });

  test('floatTimeToStr redondea 60 minutos a la hora siguiente', () {
    expect(floatTimeToStr(0.999), '01:00');
  });

  test('floatTimeToStr con negativos aplica el signo a las horas', () {
    expect(floatTimeToStr(-1.5), '-01:30');
  });

  test('floatTimeToMinutes', () {
    expect(floatTimeToMinutes(2.0), 120);
    expect(floatTimeToMinutes(2.5), 150);
    expect(floatTimeToMinutes(0.999), 60);
  });

  test('floatMinutesToStr convierte minutos a HH:MM', () {
    expect(floatMinutesToStr(5), '00:05');
    expect(floatMinutesToStr(90), '01:30');
  });

  test('strToFloatTime', () {
    expect(strToFloatTime('02:30'), closeTo(2.5, 1e-9));
    expect(strToFloatTime('01:00:36'), closeTo(1.01, 1e-9));
  });
}
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `flutter test test/core/util/float_time_test.dart`
Expected: FAIL — fichero inexistente.

- [ ] **Step 3: Implementación**

`lib/core/util/float_time.dart` — port literal de `addons/leulit/utilitylib.py:645-682`:
```dart
import 'dart:math' as math;

({int horas, int minutos}) floatTimeConvert(double v) {
  final factor = v < 0 ? -1 : 1;
  final val = v.abs();
  var horas = factor * val.floor();
  var minutos = ((val % 1) * 60).round();
  if (minutos >= 60) {
    minutos = 0;
    horas += 1;
  }
  return (horas: horas, minutos: minutos);
}

String floatTimeToStr(double? v) {
  if (v == null) return '00:00';
  final d = floatTimeConvert(v);
  final signo = d.horas < 0 ? '-' : '';
  final h = d.horas.abs().toString().padLeft(2, '0');
  final m = d.minutos.toString().padLeft(2, '0');
  return '$signo$h:$m';
}

int floatTimeToMinutes(double v) {
  final d = floatTimeConvert(v);
  return d.horas * 60 + d.minutos;
}

String floatMinutesToStr(double v) => floatTimeToStr(v / 60);

double strToFloatTime(String hms) {
  final f = hms.split(':');
  final h = f.isNotEmpty ? double.parse(f[0]) : 0.0;
  final m = f.length > 1 ? double.parse(f[1]) : 0.0;
  final s = f.length > 2 ? double.parse(f[2]) : 0.0;
  return h + (m / 60.0) + (s / math.pow(60.0, 2));
}
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `flutter test test/core/util/float_time_test.dart` → PASS

- [ ] **Step 5: Commit**

```bash
git add lib/core/util/float_time.dart test/core/util/float_time_test.dart
git commit -m "feat: conversiones float_time equivalentes a utilitylib"
```

---

## Task 3: Conversiones de unidades

**Files:**
- Create: `lib/core/util/unit_convert.dart`
- Test: `test/core/util/unit_convert_test.dart`

**Interfaces:**
- Produces: `double litrosToKg(double l, String? tipo)`, `double litrosToGal(double l)`,
  `double nudosToMs(double kt)`, `double metrosToNm(double m)`, `double nmToMetros(double nm)`,
  `double tiempoVueloDecimal(double nm, double kt)`.

- [ ] **Step 1: Escribir el test que falla**

`test/core/util/unit_convert_test.dart`:
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:parte_vuelo_app/core/util/unit_convert.dart';

void main() {
  test('densidades por tipo de helicoptero', () {
    expect(litrosToKg(100, 'R22'), 71.0);
    expect(litrosToKg(100, 'R44'), 71.0);
    expect(litrosToKg(100, 'CABRI G2'), 71.0);
    expect(litrosToKg(288.0, 'EC120B'), 227.52);
  });

  test('tipo sin densidad definida devuelve 0 (comportamiento del ERP)', () {
    expect(litrosToKg(100, 'AS350'), 0.0);
    expect(litrosToKg(100, 'EC130'), 0.0);
    expect(litrosToKg(100, 'DJI'), 0.0);
    expect(litrosToKg(100, null), 0.0);
  });

  test('galones ignora el tipo', () {
    expect(litrosToGal(100), 26.42);
  });

  test('tiempoVueloDecimal 220 NM a 110 kt son 2 horas', () {
    expect(tiempoVueloDecimal(220, 110), closeTo(2.0, 1e-6));
  });

  test('tiempoVueloDecimal con velocidad 0 devuelve 0', () {
    expect(tiempoVueloDecimal(220, 0), 0.0);
  });
}
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `flutter test test/core/util/unit_convert_test.dart` → FAIL

- [ ] **Step 3: Implementación**

`lib/core/util/unit_convert.dart` — port de `addons/leulit/utilitylib.py:1084-1146`:
```dart
const Map<String, double> densidadCombustible = {
  'R44': 0.71,
  'R22': 0.71,
  'EC120B': 0.79,
  'CABRI G2': 0.71,
};

double _round2(double v) => (v * 100).round() / 100;

// El ERP devuelve 0 para los tipos sin densidad (AS350, EC130, DJI). No es un bug
// que debamos corregir aqui: la app debe reproducir el valor que persiste Odoo.
double litrosToKg(double litros, String? tipo) =>
    _round2(litros * (densidadCombustible[tipo] ?? 0));

double litrosToGal(double litros) => _round2(litros * 0.264172);

double nudosToMs(double kt)     => kt * 0.51444444444;
double metrosToNm(double m)     => m * 0.000539956803;
double nmToMetros(double nm)    => nm * 1852;
double msToNudos(double ms)     => ms * 1.94384;

double tiempoVueloSegundos(double nm, double kt) {
  if (kt <= 0) return 0;
  final ms = nudosToMs(kt);
  if (ms <= 0) return 0;
  return nmToMetros(nm) / ms;
}

double tiempoVueloDecimal(double nm, double kt) {
  final v = tiempoVueloSegundos(nm, kt);
  return v > 0 ? v / 3600 : 0;
}
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `flutter test test/core/util/unit_convert_test.dart` → PASS

- [ ] **Step 5: Commit**

```bash
git add lib/core/util/unit_convert.dart test/core/util/unit_convert_test.dart
git commit -m "feat: conversiones de unidades combustible y navegacion"
```

---

## Task 4: Motor de combustible (espejo de `calculosFuel`)

Réplica en cliente de spec §6.3 para feedback inmediato. **No sustituye al `onchange` del servidor**; se usa para pintar valores mientras la llamada está en vuelo y como red de seguridad en tests de equivalencia.

**Files:**
- Create: `lib/feature/parte/fuel_engine.dart`
- Test: `test/feature/parte/fuel_engine_test.dart`

**Interfaces:**
- Consumes: `float_time.dart`, `unit_convert.dart`.
- Produces:
  ```dart
  class FuelInput { double tiempoprevisto, velocidadprevista, distanciatotalprevista,
                           consumomedioVuelo, editfuelrem, fuelqty, horasalida,
                           distanciaAlternativo; String reservasfuel, rodaje, contingencia;
                    String? helicopteroTipo; bool tieneRuta; }
  class FuelOutput { double combustibleminimo, fuelsalida, combustibleextra,
                            combustiblelanding, combustibletrayecto, horallegadaprevista,
                            tiempoprevisto, distanciatotalprevista; ... y sus _kg y _gal }
  FuelOutput calcularFuel(FuelInput input, String campoCambiado);
  ```

- [ ] **Step 1: Escribir el test que falla**

`test/feature/parte/fuel_engine_test.dart` — usa los números reales del parte VUL-0019153 (spec §14):
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:parte_vuelo_app/feature/parte/fuel_engine.dart';

void main() {
  FuelInput vul0019153() => FuelInput(
        tiempoprevisto: 2.0,
        velocidadprevista: 110.0,
        distanciatotalprevista: 220.0,
        consumomedioVuelo: 1.92,
        editfuelrem: 288.16,
        fuelqty: 40.0,
        horasalida: 12.0,
        distanciaAlternativo: 0.0,
        reservasfuel: '30',
        rodaje: '0',
        contingencia: '0',
        helicopteroTipo: 'EC120B',
        tieneRuta: false,
      );

  test('reproduce los valores de produccion del parte VUL-0019153', () {
    final out = calcularFuel(vul0019153(), 'consumomedio_vuelo');
    expect(out.combustibleminimo, 288.0);
    expect(out.fuelsalida, 328.16);
    expect(out.combustiblelanding, closeTo(97.76, 0.01));
    expect(out.horallegadaprevista, 14.0);
    expect(out.combustibleminimoKg, 227.52);
  });

  test('contingencia del 5% amplia el tiempo un 5%', () {
    final out = calcularFuel(vul0019153()..contingencia = '5', 'contingencia');
    // tiempo = 2.0 * 1.05 = 2.1 h = 126 min  →  1.92 * (126 + 30) = 299.52
    expect(out.combustibleminimo, 299.52);
  });

  test('rodaje de 5 minutos suma 5 minutos al tiempo', () {
    final out = calcularFuel(vul0019153()..rodaje = '5', 'rodaje');
    // 1.92 * (125 + 30) = 297.6
    expect(out.combustibleminimo, 297.6);
  });

  test('sin ruta, cambiar tiempoprevisto recalcula la distancia', () {
    final out = calcularFuel(vul0019153()..tiempoprevisto = 1.0, 'tiempoprevisto');
    expect(out.distanciatotalprevista, closeTo(110.0, 0.05));
  });

  test('sin ruta, cambiar velocidad recalcula el tiempo', () {
    final out = calcularFuel(vul0019153()..velocidadprevista = 55.0, 'velocidadprevista');
    expect(out.tiempoprevisto, closeTo(4.0, 0.01));
  });

  test('la hora de llegada prevista da la vuelta pasada la medianoche', () {
    final out = calcularFuel(vul0019153()..horasalida = 23.0, 'horasalida');
    expect(out.horallegadaprevista, 1.0);
  });
}
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `flutter test test/feature/parte/fuel_engine_test.dart` → FAIL

- [ ] **Step 3: Implementación**

`lib/feature/parte/fuel_engine.dart` — port literal de spec §6.3:
```dart
import '../../core/util/float_time.dart';
import '../../core/util/unit_convert.dart';

class FuelInput {
  FuelInput({
    required this.tiempoprevisto,
    required this.velocidadprevista,
    required this.distanciatotalprevista,
    required this.consumomedioVuelo,
    required this.editfuelrem,
    required this.fuelqty,
    required this.horasalida,
    required this.distanciaAlternativo,
    required this.reservasfuel,
    required this.rodaje,
    required this.contingencia,
    required this.helicopteroTipo,
    required this.tieneRuta,
    this.fuelllegada = 0,
  });

  double tiempoprevisto, velocidadprevista, distanciatotalprevista;
  double consumomedioVuelo, editfuelrem, fuelqty, horasalida, distanciaAlternativo;
  double fuelllegada;
  String reservasfuel, rodaje, contingencia;
  String? helicopteroTipo;
  bool tieneRuta;
}

class FuelOutput {
  FuelOutput({
    required this.tiempoprevisto,
    required this.distanciatotalprevista,
    required this.combustibleminimo,
    required this.fuelsalida,
    required this.combustibleextra,
    required this.combustiblelanding,
    required this.combustibletrayecto,
    required this.horallegadaprevista,
    required this.tipo,
  });

  final double tiempoprevisto, distanciatotalprevista;
  final double combustibleminimo, fuelsalida, combustibleextra;
  final double combustiblelanding, combustibletrayecto, horallegadaprevista;
  final String? tipo;

  double get combustibleminimoKg   => litrosToKg(combustibleminimo, tipo);
  double get combustibleminimoGal  => litrosToGal(combustibleminimo);
  double get fuelsalidaKg          => litrosToKg(fuelsalida, tipo);
  double get fuelsalidaGal         => litrosToGal(fuelsalida);
  double get combustiblelandingKg  => litrosToKg(combustiblelanding, tipo);
  double get combustiblelandingGal => litrosToGal(combustiblelanding);
  double get combustibleextraKg    => litrosToKg(combustibleextra, tipo);
  double get combustibleextraGal   => litrosToGal(combustibleextra);
  double get combustibletrayectoKg => litrosToKg(combustibletrayecto, tipo);
  double get combustibletrayectoGal=> litrosToGal(combustibletrayecto);
}

double _round2(double v) => (v * 100).round() / 100;

double calcCombustibleMinimo({
  required double tiempoprevisto,
  required String reservasfuel,
  required double consumomedioVuelo,
  required String rodaje,
  required String contingencia,
  required double distanciaAlternativo,
  required double velocidadprevista,
}) {
  final tiempoAlternativo = tiempoVueloDecimal(distanciaAlternativo, velocidadprevista);
  final rodajeHoras = strToFloatTime(floatMinutesToStr(double.parse(rodaje)));
  var tiempo = tiempoprevisto + rodajeHoras + tiempoAlternativo;
  if (contingencia == '5') tiempo = tiempo * 1.05;
  final minutos = floatTimeToMinutes(tiempo);
  return _round2(consumomedioVuelo * (minutos + double.parse(reservasfuel)));
}

FuelOutput calcularFuel(FuelInput i, String campoCambiado) {
  var tiempoprevisto = i.tiempoprevisto;
  var distancia = i.distanciatotalprevista;

  if (!i.tieneRuta) {
    if (campoCambiado == 'velocidadprevista' || campoCambiado == 'distanciatotalprevista') {
      tiempoprevisto = _round2(tiempoVueloDecimal(distancia, i.velocidadprevista));
    }
    if (campoCambiado == 'tiempoprevisto') {
      final vv = nudosToMs(i.velocidadprevista);
      distancia = _round2(metrosToNm(vv * (tiempoprevisto * 3600)));
    }
  }

  final combustibleminimo = calcCombustibleMinimo(
    tiempoprevisto: tiempoprevisto,
    reservasfuel: i.reservasfuel,
    consumomedioVuelo: i.consumomedioVuelo,
    rodaje: i.rodaje,
    contingencia: i.contingencia,
    distanciaAlternativo: i.distanciaAlternativo,
    velocidadprevista: i.velocidadprevista,
  );

  final fuelsalida = _round2(i.editfuelrem + i.fuelqty);
  final combustibleextra = fuelsalida - combustibleminimo;

  var horallegadaprevista = i.horasalida + tiempoprevisto;
  if (horallegadaprevista >= 24.0) horallegadaprevista -= 24.0;

  final minutosprevistos = floatTimeToMinutes(tiempoprevisto);
  final combustiblelanding = fuelsalida - (i.consumomedioVuelo * minutosprevistos);
  final combustibletrayecto = _round2(i.consumomedioVuelo * minutosprevistos);

  return FuelOutput(
    tiempoprevisto: tiempoprevisto,
    distanciatotalprevista: distancia,
    combustibleminimo: combustibleminimo,
    fuelsalida: fuelsalida,
    combustibleextra: combustibleextra,
    combustiblelanding: combustiblelanding,
    combustibletrayecto: combustibletrayecto,
    horallegadaprevista: horallegadaprevista,
    tipo: i.helicopteroTipo,
  );
}
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `flutter test test/feature/parte/fuel_engine_test.dart` → PASS

- [ ] **Step 5: Commit**

```bash
git add lib/feature/parte/fuel_engine.dart test/feature/parte/fuel_engine_test.dart
git commit -m "feat: motor de combustible espejo de calculosFuel"
```

---

## Task 5: Cliente JSON-RPC de Odoo

**Files:**
- Create: `lib/core/odoo/odoo_exception.dart`
- Create: `lib/core/odoo/odoo_client.dart`
- Test: `test/core/odoo/odoo_client_test.dart`

**Interfaces:**
- Consumes: `AppConfig`.
- Produces:
  - `class OdooClient { Future<int> authenticate(String login, String password); Future<dynamic> callKw({required String model, required String method, List args, Map<String,dynamic> kwargs}); }`
  - `sealed class OdooException` → `OdooUserError`, `OdooValidationError`, `OdooAccessError`, `OdooMissingError`, `OdooSessionExpired`, `OdooUnknownError` (todas con `message` y `debug`).

- [ ] **Step 1: Escribir el test que falla**

`test/core/odoo/odoo_client_test.dart` — usa `MockClient` de `package:http/testing.dart`:
```dart
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/testing.dart';
import 'package:http/http.dart' as http;
import 'package:parte_vuelo_app/config/app_config.dart';
import 'package:parte_vuelo_app/core/odoo/odoo_client.dart';
import 'package:parte_vuelo_app/core/odoo/odoo_exception.dart';

void main() {
  final cfg = AppConfig(baseUrl: 'https://erp.test', db: 'productiu');

  test('authenticate devuelve el uid y guarda la sesion', () async {
    final client = OdooClient(cfg, httpClient: MockClient((req) async {
      expect(req.url.path, '/web/session/authenticate');
      return http.Response(
        jsonEncode({'jsonrpc': '2.0', 'result': {'uid': 42, 'user_context': {'lang': 'es_ES'}}}),
        200,
        headers: {'set-cookie': 'session_id=abc123; Path=/; HttpOnly'},
      );
    }));
    expect(await client.authenticate('piloto', 'x'), 42);
    expect(client.sessionId, 'abc123');
  });

  test('callKw devuelve el result', () async {
    final client = OdooClient(cfg, httpClient: MockClient((req) async {
      final body = jsonDecode(req.body) as Map<String, dynamic>;
      expect(body['params']['model'], 'leulit.vuelo');
      expect(body['params']['method'], 'read');
      return http.Response(jsonEncode({'jsonrpc': '2.0', 'result': [{'id': 1}]}), 200);
    }));
    final r = await client.callKw(model: 'leulit.vuelo', method: 'read', args: [[1]]);
    expect((r as List).first['id'], 1);
  });

  test('un UserError se traduce a OdooUserError con el mensaje intacto', () async {
    const msg = 'Este vuelo no puede pasar a postvuelo. NO HA REVISADO NOTAM';
    final client = OdooClient(cfg, httpClient: MockClient((req) async {
      return http.Response(jsonEncode({
        'jsonrpc': '2.0',
        'error': {
          'code': 200,
          'message': 'Odoo Server Error',
          'data': {'name': 'odoo.exceptions.UserError', 'message': msg, 'debug': 'traceback'}
        }
      }), 200);
    }));
    expect(
      () => client.callKw(model: 'leulit.vuelo', method: 'wkf_act_postvuelo', args: [[1]]),
      throwsA(isA<OdooUserError>().having((e) => e.message, 'message', msg)),
    );
  });

  test('una sesion caducada se traduce a OdooSessionExpired', () async {
    final client = OdooClient(cfg, httpClient: MockClient((req) async {
      return http.Response(jsonEncode({
        'jsonrpc': '2.0',
        'error': {'code': 100, 'message': 'Odoo Session Expired',
                  'data': {'name': 'odoo.http.SessionExpiredException', 'message': 'Session expired'}}
      }), 200);
    }));
    expect(() => client.callKw(model: 'leulit.vuelo', method: 'read', args: [[1]]),
        throwsA(isA<OdooSessionExpired>()));
  });
}
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `flutter test test/core/odoo/odoo_client_test.dart` → FAIL

- [ ] **Step 3: Implementar las excepciones**

`lib/core/odoo/odoo_exception.dart`:
```dart
sealed class OdooException implements Exception {
  OdooException(this.message, {this.debug});
  final String message;
  final String? debug;
  @override
  String toString() => '$runtimeType: $message';
}

class OdooUserError       extends OdooException { OdooUserError(super.m, {super.debug}); }
class OdooValidationError extends OdooException { OdooValidationError(super.m, {super.debug}); }
class OdooAccessError     extends OdooException { OdooAccessError(super.m, {super.debug}); }
class OdooMissingError    extends OdooException { OdooMissingError(super.m, {super.debug}); }
class OdooSessionExpired  extends OdooException { OdooSessionExpired(super.m, {super.debug}); }
class OdooUnknownError    extends OdooException { OdooUnknownError(super.m, {super.debug}); }

OdooException odooExceptionFrom(Map<String, dynamic> error) {
  final data = (error['data'] as Map<String, dynamic>?) ?? const {};
  final name = (data['name'] as String?) ?? '';
  final message = (data['message'] as String?)?.trim().isNotEmpty == true
      ? data['message'] as String
      : (error['message'] as String? ?? 'Error desconocido');
  final debug = data['debug'] as String?;
  return switch (name) {
    'odoo.exceptions.UserError'        => OdooUserError(message, debug: debug),
    'odoo.exceptions.ValidationError'  => OdooValidationError(message, debug: debug),
    'odoo.exceptions.AccessError'      => OdooAccessError(message, debug: debug),
    'odoo.exceptions.AccessDenied'     => OdooAccessError(message, debug: debug),
    'odoo.exceptions.MissingError'     => OdooMissingError(message, debug: debug),
    'odoo.http.SessionExpiredException'=> OdooSessionExpired(message, debug: debug),
    _                                  => OdooUnknownError(message, debug: debug),
  };
}
```

- [ ] **Step 4: Implementar el cliente**

`lib/core/odoo/odoo_client.dart`:
```dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../config/app_config.dart';
import 'odoo_exception.dart';

class OdooClient {
  OdooClient(this.config, {http.Client? httpClient})
      : _http = httpClient ?? http.Client();

  final AppConfig config;
  final http.Client _http;

  String? sessionId;
  int? uid;
  Map<String, dynamic> userContext = const {};

  Future<int> authenticate(String login, String password) async {
    final res = await _post('/web/session/authenticate', {
      'db': config.db,
      'login': login,
      'password': password,
    });
    uid = res['uid'] as int?;
    userContext = (res['user_context'] as Map?)?.cast<String, dynamic>() ?? const {};
    if (uid == null) throw OdooAccessError('Usuario o contraseña incorrectos');
    return uid!;
  }

  Future<dynamic> callKw({
    required String model,
    required String method,
    List<dynamic> args = const [],
    Map<String, dynamic> kwargs = const {},
  }) {
    final ctx = <String, dynamic>{...userContext, ...?(kwargs['context'] as Map?)?.cast<String, dynamic>()};
    return _post('/web/dataset/call_kw', {
      'model': model,
      'method': method,
      'args': args,
      'kwargs': {...kwargs, 'context': ctx},
    });
  }

  Future<dynamic> _post(String path, Map<String, dynamic> params) async {
    final response = await _http.post(
      config.endpoint(path),
      headers: {
        'Content-Type': 'application/json',
        if (sessionId != null) 'Cookie': 'session_id=$sessionId',
      },
      body: jsonEncode({'jsonrpc': '2.0', 'method': 'call', 'params': params}),
    );

    _captureSession(response);

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    if (body.containsKey('error')) {
      throw odooExceptionFrom((body['error'] as Map).cast<String, dynamic>());
    }
    return body['result'];
  }

  void _captureSession(http.Response response) {
    final raw = response.headers['set-cookie'];
    if (raw == null) return;
    final match = RegExp(r'session_id=([^;]+)').firstMatch(raw);
    if (match != null) sessionId = match.group(1);
  }
}
```

- [ ] **Step 5: Ejecutar y verificar que pasa**

Run: `flutter test test/core/odoo/odoo_client_test.dart` → PASS
Run: `dart analyze` → sin errores

- [ ] **Step 6: Commit**

```bash
git add lib/core/odoo test/core/odoo
git commit -m "feat: cliente JSON-RPC de Odoo con mapeo de excepciones de negocio"
```

---

## Task 6: Modelo de dominio `Vuelo`

**Files:**
- Create: `lib/domain/ref.dart`
- Create: `lib/domain/vuelo_enums.dart`
- Create: `lib/domain/vuelo.dart`
- Test: `test/domain/vuelo_test.dart`

**Interfaces:**
- Produces:
  - `class Ref { final int id; final String name; static Ref? fromOdoo(dynamic v); dynamic toOdoo(); }`
  - `enum Estado { prevuelo, postvuelo, cerrado, cancelado }` con `fromValue`/`value`
  - `enum EstadoVista { prevuelo, finPrevuelo, postvuelo, cerrado, cancelado }` (valor Odoo `fin_prevuelo`)
  - `enum ControlFirma { noFirmado, pendiente, firmado }` (valores `no-firmado`, `pendiente`, `firmado`)
  - `class Vuelo { ...campos de spec §4...; factory Vuelo.fromJson(Map); Map<String,dynamic> toWriteValues({Set<String>? soloCampos}); }`

- [ ] **Step 1: Escribir el test que falla**

`test/domain/vuelo_test.dart` — usa el payload real de spec §14:
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:parte_vuelo_app/domain/vuelo.dart';
import 'package:parte_vuelo_app/domain/vuelo_enums.dart';

void main() {
  final json = <String, dynamic>{
    'id': 18864, 'codigo': 'VUL-0019153',
    'estado': 'prevuelo', 'estado_vista': 'prevuelo', 'control_firma': 'no-firmado',
    'fechavuelo': '2026-08-18', 'horasalida': 12.0, 'horallegadaprevista': 14.0,
    'tiempoprevisto': 2.0, 'helicoptero_id': [87, 'SE-JXP'], 'helicoptero_tipo': 'EC120B',
    'piloto_id': [238, 'Joan Sampons Ritort'], 'operador': [251, 'Guiu Serra Gavaldà'],
    'alumno': false, 'verificado': false,
    'lugarsalida': [173, '(Heliport Manresa) Heliport Bombers Manresa'],
    'lugarllegada': [173, '(Heliport Manresa) Heliport Bombers Manresa'],
    'reservasfuel': '30', 'rodaje': '0', 'contingencia': '0',
    'consumomedio_vuelo': 1.92, 'editfuelrem': 288.16, 'fuelqty': 40.0,
    'fuelsalida': 328.16, 'combustibleminimo': 288.0,
    'numtripulacion': 1, 'numpax': 0, 'numpae': 2, 'asiento_pic': 'pic_right',
    'vuelo_tipo_line': [19639], 'oilqty': 0.0,
  };

  test('deserializa los enums', () {
    final v = Vuelo.fromJson(json);
    expect(v.estado, Estado.prevuelo);
    expect(v.estadoVista, EstadoVista.prevuelo);
    expect(v.controlFirma, ControlFirma.noFirmado);
  });

  test('deserializa los many2one como Ref y los false como null', () {
    final v = Vuelo.fromJson(json);
    expect(v.helicopteroId?.id, 87);
    expect(v.helicopteroId?.name, 'SE-JXP');
    expect(v.alumno, isNull);
    expect(v.verificado, isNull);
  });

  test('toWriteValues serializa m2o como id y omite codigo y create_uid', () {
    final values = Vuelo.fromJson(json).toWriteValues();
    expect(values['helicoptero_id'], 87);
    expect(values['piloto_id'], 238);
    expect(values.containsKey('codigo'), isFalse);
    expect(values.containsKey('create_uid'), isFalse);
  });

  test('toWriteValues envía false para los m2o vacíos', () {
    final values = Vuelo.fromJson(json).toWriteValues();
    expect(values['alumno'], false);
  });

  test('EstadoVista fin_prevuelo mapea al enum finPrevuelo', () {
    final v = Vuelo.fromJson({...json, 'estado_vista': 'fin_prevuelo'});
    expect(v.estadoVista, EstadoVista.finPrevuelo);
    expect(v.toWriteValues()['estado_vista'], 'fin_prevuelo');
  });
}
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `flutter test test/domain/vuelo_test.dart` → FAIL

- [ ] **Step 3: Implementar `Ref` y los enums**

`lib/domain/ref.dart`:
```dart
class Ref {
  const Ref(this.id, this.name);
  final int id;
  final String name;

  // Odoo devuelve [id, display_name] o false.
  static Ref? fromOdoo(dynamic v) {
    if (v is List && v.length >= 2) return Ref(v[0] as int, '${v[1]}');
    return null;
  }

  // Odoo espera el id, o false para vaciar el campo.
  static dynamic toOdoo(Ref? r) => r?.id ?? false;

  @override
  bool operator ==(Object other) => other is Ref && other.id == id;
  @override
  int get hashCode => id.hashCode;
}
```

`lib/domain/vuelo_enums.dart`:
```dart
enum Estado {
  prevuelo('prevuelo', 'Pre-Vuelo'),
  postvuelo('postvuelo', 'Post-Vuelo'),
  cerrado('cerrado', 'Cerrado'),
  cancelado('cancelado', 'Cancelado');

  const Estado(this.value, this.label);
  final String value;
  final String label;

  static Estado fromValue(String? v) =>
      Estado.values.firstWhere((e) => e.value == v, orElse: () => Estado.prevuelo);
}

enum EstadoVista {
  prevuelo('prevuelo', 'Prevuelo'),
  finPrevuelo('fin_prevuelo', 'Prevuelo 2'),
  postvuelo('postvuelo', 'Postvuelo'),
  cerrado('cerrado', 'Cerrado'),
  cancelado('cancelado', 'Cancelado');

  const EstadoVista(this.value, this.label);
  final String value;
  final String label;

  static EstadoVista fromValue(String? v) =>
      EstadoVista.values.firstWhere((e) => e.value == v, orElse: () => EstadoVista.prevuelo);
}

enum ControlFirma {
  noFirmado('no-firmado'), pendiente('pendiente'), firmado('firmado');

  const ControlFirma(this.value);
  final String value;

  static ControlFirma fromValue(String? v) =>
      ControlFirma.values.firstWhere((e) => e.value == v, orElse: () => ControlFirma.noFirmado);
}
```

- [ ] **Step 4: Implementar `Vuelo`**

`lib/domain/vuelo.dart` — un campo por cada entrada de spec §4. La clase es mutable
(el formulario la edita en sitio) y `toWriteValues()` produce el mapa para `write`.
Incluir **obligatoriamente** los `force_save` de spec §4 en `toWriteValues`
(`velocidadprevista`, `distanciatotalprevista`, `horallegadaprevista`, `horallegada`,
`fuelsalida`, `combustiblelanding`, `combustibleextra`, `combustibleminimo`,
`combustibletrayecto` y todos los `_kg`/`_gal`, `notaminfo`), y **excluir siempre**
`codigo`, `create_uid`, `write_uid`, `id` y los campos calculados no almacenados
(`utc_*`, `semaforo*`, `strhoras_remanente`, `can_sign`, `foto_*`, `diferido_ids`,
`anotacion_ids`, `esignature_docs`, `account_analytic_lines`, `night_hours`,
`peso_piloto`, `peso_alumno`, `is_it_developer`, `non_conformity_count`,
`helicoptero_modelo`, `combustibletrayecto*`).

Definir la lista de campos a leer como constante pública para que el repositorio la use en
`web_read`:
```dart
const List<String> vueloReadFields = [
  'id','codigo','estado','estado_vista','control_firma','can_sign','active',
  'fechavuelo','horasalida','utc_horasalida','horallegada','utc_horallegada',
  'horallegadaprevista','utc_horallegadaprevista','tiempoprevisto','tiemposervicio','airtime',
  'helicoptero_id','helicoptero_modelo','helicoptero_tipo','strhoras_remanente','semaforo',
  'piloto_id','operador','verificado','alumno','piloto_supervisor_id',
  'foto_piloto','foto_operador','foto_verificado','foto_alumno','foto_piloto_supervisor_id',
  'semaforo_pf_piloto','semaforo_pf_operador','doblemando','asiento_pic',
  'numtripulacion','numpax','numpae','pasajeros_wb',
  'lugarsalida','lugarllegada','alternativos','ruta_id','aerovia_ids',
  'velocidadprevista','distanciatotalprevista','distancia_alternativo',
  'reservasfuel','rodaje','contingencia','consumomedio_vuelo','consumomedio_vuelo_kg','consumomedio_vuelo_gal',
  'editfuelrem','fuelremanente_kg','fuelremanente_gal','fuelqty','fuelqty_kg','fuelqty_gal',
  'fuelsalida','fuelsalida_kg','fuelsalida_gal','combustibleminimo','combustibleminimo_kg','combustibleminimo_gal',
  'combustiblelanding','combustiblelanding_kg','combustiblelanding_gal',
  'combustibleextra','combustibleextra_kg','combustibleextra_gal',
  'combustibletrayecto','combustibletrayecto_kg','combustibletrayecto_gal',
  'fuelllegada','fuelllegada_kg','fuelllegada_gal','oilqty','oilqty_kg','oilqty_gal',
  'tacomsalida','tacomllegada','ngvuelo','nfvuelo','arlanding',
  'landings','nightlandings','uso_gancho','sling_cycle',
  'checklist_realizado','checklist_prevuelo_BFF','checklist_prevuelo_entre_vuelos',
  'checklist_postvuelo_realizado','briefing_realizado','notam_revisado',
  'indicativometeo','meteo','notaminfo','comentarios',
  'presupuesto_vuelo','vuelo_tipo_line','nombre_actividad',
  'balsa','flotadores','chalecos','ifr','nv','nv_uid','nv_date',
  'weight_and_balance_id','performance',
  'valid_takeoff_longcg','valid_takeoff_latcg','valid_landing_longcg','valid_landing_latcg',
  'emptyweight','longmoment','latmoment','longarm','latarm','pesomax',
  'silabus_ids','valoracion_escuela','comentario_escuela','parte_escuela_id',
  'anotacion_ids','diferido_ids','esignature_docs','account_analytic_lines',
  'is_comercial_uid','is_it_developer','p_corregido','p_corregido_date','create_uid',
];
```

- [ ] **Step 5: Ejecutar y verificar que pasa**

Run: `flutter test test/domain/vuelo_test.dart` → PASS

- [ ] **Step 6: Commit**

```bash
git add lib/domain test/domain
git commit -m "feat: modelo de dominio Vuelo con serializacion Odoo"
```

---

## Task 7: `VueloRepository`

**Files:**
- Create: `lib/data/vuelo_repository.dart`
- Test: `test/data/vuelo_repository_test.dart`

**Interfaces:**
- Consumes: `OdooClient`, `Vuelo`, `vueloReadFields`.
- Produces:
  ```dart
  class VueloRepository {
    Future<List<VueloResumen>> listar({required List<int> misPilotoIds, int limit, int offset});
    Future<Vuelo> abrir(int id);
    Future<int> crear(Map<String, dynamic> values);
    Future<void> guardar(int id, Map<String, dynamic> values);
    Future<OnchangeResult> onchange(int? id, Map<String,dynamic> values, List<String> campos);
    Future<OdooAction?> pulsarBoton(String metodo, int id);
  }
  class OnchangeResult { Map<String,dynamic> value; String? warningTitle; String? warningMessage; }
  ```

- [ ] **Step 1: Escribir el test que falla**

`test/data/vuelo_repository_test.dart`:
```dart
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/testing.dart';
import 'package:http/http.dart' as http;
import 'package:parte_vuelo_app/config/app_config.dart';
import 'package:parte_vuelo_app/core/odoo/odoo_client.dart';
import 'package:parte_vuelo_app/data/vuelo_repository.dart';

void main() {
  final cfg = AppConfig(baseUrl: 'https://erp.test', db: 'productiu');

  test('listar restringe a los partes donde el usuario es PIC o supervisor', () async {
    late Map<String, dynamic> enviado;
    final repo = VueloRepository(OdooClient(cfg, httpClient: MockClient((req) async {
      enviado = (jsonDecode(req.body) as Map<String, dynamic>)['params'] as Map<String, dynamic>;
      return http.Response(jsonEncode({'result': {'records': [], 'length': 0}}), 200);
    })));

    await repo.listar(misPilotoIds: [238, 400]);

    final kwargs = enviado['kwargs'] as Map<String, dynamic>;
    expect(kwargs['order'], 'fechavuelo desc, horasalida desc');
    expect(kwargs['domain'], [
      '&',
      ['fechavuelo', '<=', hoyIso()],
      '|',
      ['piloto_id', 'in', [238, 400]],
      ['piloto_supervisor_id', 'in', [238, 400]],
    ]);
  });

  test('listar nunca usa el campo user_vuelo_ids', () async {
    late Map<String, dynamic> enviado;
    final repo = VueloRepository(OdooClient(cfg, httpClient: MockClient((req) async {
      enviado = (jsonDecode(req.body) as Map<String, dynamic>)['params'] as Map<String, dynamic>;
      return http.Response(jsonEncode({'result': {'records': [], 'length': 0}}), 200);
    })));

    await repo.listar(misPilotoIds: [238]);

    expect(jsonEncode(enviado), isNot(contains('user_vuelo_ids')));
  });

  test('onchange envia campos cambiados y devuelve value y warning', () async {
    final repo = VueloRepository(OdooClient(cfg, httpClient: MockClient((req) async {
      final p = (jsonDecode(req.body) as Map<String, dynamic>)['params'] as Map<String, dynamic>;
      expect(p['method'], 'onchange');
      expect((p['args'] as List)[2], ['helicoptero_id']);
      return http.Response(jsonEncode({'result': {
        'value': {'velocidadprevista': 110.0},
        'warning': {'title': 'Warning', 'message': 'Este helicoptero tiene una anomalía/discrepancia sin firmar y no puede ser utilizado'},
      }}), 200);
    })));

    final r = await repo.onchange(18864, {'helicoptero_id': 87}, ['helicoptero_id']);
    expect(r.value['velocidadprevista'], 110.0);
    expect(r.warningMessage, contains('anomalía'));
  });

  test('crear no envía codigo ni create_uid', () async {
    final repo = VueloRepository(OdooClient(cfg, httpClient: MockClient((req) async {
      final p = (jsonDecode(req.body) as Map<String, dynamic>)['params'] as Map<String, dynamic>;
      final values = ((p['args'] as List).first as Map).cast<String, dynamic>();
      expect(values.containsKey('codigo'), isFalse);
      expect(values.containsKey('create_uid'), isFalse);
      return http.Response(jsonEncode({'result': 99}), 200);
    })));

    expect(await repo.crear({'fechavuelo': '2026-08-18', 'codigo': 'X', 'create_uid': 1}), 99);
  });
}
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `flutter test test/data/vuelo_repository_test.dart` → FAIL

- [ ] **Step 3: Implementación**

`lib/data/vuelo_repository.dart`. Puntos no negociables:
- `listar()` usa `web_search_read` con `order: 'fechavuelo desc, horasalida desc'`, una
  `specification` con las columnas del tree (spec §15.3) y el domain de spec §15.1:
  `['&', ['fechavuelo','<=', hoy], '|', ['piloto_id','in', misPilotoIds], ['piloto_supervisor_id','in', misPilotoIds]]`.
  Si `misPilotoIds` está vacío, devolver lista vacía **sin llamar al servidor**: un usuario
  sin ficha de piloto no tiene partes propios.
- `abrir(id)` usa `web_read` con `specification` construida desde `vueloReadFields`.
- `crear` y `guardar` filtran `codigo`, `create_uid`, `write_uid`, `id` antes de enviar.
- `onchange(id, values, campos)` llama a `onchange` con
  `args: [[id o vacío], values, campos, fieldsSpec]`, donde `fieldsSpec` es
  `{ for (final f in vueloReadFields) f: <String, dynamic>{} }`.
- `pulsarBoton(metodo, id)` llama a `callKw(model:'leulit.vuelo', method: metodo, args: [[id]])`
  y devuelve `OdooAction.parse(result)` (Task 8).

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `flutter test test/data/vuelo_repository_test.dart` → PASS

- [ ] **Step 5: Commit**

```bash
git add lib/data/vuelo_repository.dart test/data/vuelo_repository_test.dart
git commit -m "feat: repositorio de partes de vuelo sobre JSON-RPC"
```

---

## Task 8: Parseo de acciones devueltas por botones

**Files:**
- Create: `lib/core/odoo/odoo_action.dart`
- Test: `test/core/odoo/odoo_action_test.dart`

**Interfaces:**
- Produces: `sealed class OdooAction` → `ActWindow({required String model, int? resId, int? viewId, Map<String,dynamic> context = const {}, String? name})`,
  `DisplayNotification(title, message, type, sticky)`, `ReportAction(reportName, ids, data)`,
  `CloseWindow()`, `NoAction()`. Constructor `OdooAction.parse(dynamic result)`.

- [ ] **Step 1: Escribir el test que falla**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:parte_vuelo_app/core/odoo/odoo_action.dart';

void main() {
  test('null es NoAction', () {
    expect(OdooAction.parse(null), isA<NoAction>());
  });

  test('display_notification de la meteo', () {
    final a = OdooAction.parse({
      'type': 'ir.actions.client', 'tag': 'display_notification',
      'params': {'title': 'Meteorología actualizada', 'message': 'Meteorología obtenida para LELL',
                 'type': 'success', 'sticky': false},
    });
    expect(a, isA<DisplayNotification>());
    expect((a as DisplayNotification).title, 'Meteorología actualizada');
    expect(a.type, 'success');
  });

  test('act_window del wizard de weight and balance', () {
    final a = OdooAction.parse({
      'type': 'ir.actions.act_window', 'name': 'Weight And Balance',
      'res_model': 'leulit.weight_and_balance', 'res_id': 55,
      'context': {'default_vuelo_id': 18864},
    });
    expect(a, isA<ActWindow>());
    expect((a as ActWindow).model, 'leulit.weight_and_balance');
    expect(a.resId, 55);
    expect(a.context['default_vuelo_id'], 18864);
  });

  test('act_window_close', () {
    expect(OdooAction.parse({'type': 'ir.actions.act_window_close'}), isA<CloseWindow>());
  });
}
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `flutter test test/core/odoo/odoo_action_test.dart` → FAIL

- [ ] **Step 3: Implementación**

`lib/core/odoo/odoo_action.dart` con un `switch` sobre `result['type']` y, para
`ir.actions.client`, sobre `result['tag']`. Cualquier tipo no contemplado devuelve
`NoAction` y registra un warning (no debe romper la app).

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `flutter test test/core/odoo/odoo_action_test.dart` → PASS

- [ ] **Step 5: Commit**

```bash
git add lib/core/odoo/odoo_action.dart test/core/odoo/odoo_action_test.dart
git commit -m "feat: parseo de ir.actions devueltas por los botones del ERP"
```

---

## Task 9: Login y sesión

**Files:**
- Create: `lib/feature/login/login_viewmodel.dart`
- Create: `lib/feature/login/login_view.dart`
- Modify: `lib/main.dart`
- Test: `test/feature/login/login_viewmodel_test.dart`

**Interfaces:**
- Consumes: `OdooClient`.
- Produces: `LoginViewModel extends ChangeNotifier { Future<void> entrar(String login, String pass); bool cargando; String? error; bool autenticado; List<int> misPilotoIds; }`

Tras autenticar, el ViewModel resuelve **una sola vez** los ids de piloto del usuario
(spec §15.1) y los deja en `misPilotoIds`, que es lo que consume la lista:
```
partnerId    = res.users.read([uid], ['partner_id']) -> partner_id[0]
misPilotoIds = leulit.piloto.search([('partner_id','=', partnerId)])
```
Si el usuario no tiene ficha de piloto, `misPilotoIds` queda vacío y la lista se muestra
vacía con el mensaje "No tienes partes de vuelo asignados".

- [ ] **Step 1: Escribir el test que falla**

```dart
test('un AccessError deja el mensaje en error y no autentica', () async {
  final vm = LoginViewModel(clienteQueLanza(OdooAccessError('Usuario o contraseña incorrectos')));
  await vm.entrar('x', 'y');
  expect(vm.autenticado, isFalse);
  expect(vm.error, 'Usuario o contraseña incorrectos');
});

test('login correcto marca autenticado y limpia el error', () async {
  final vm = LoginViewModel(clienteQueDevuelveUid(42));
  await vm.entrar('piloto', 'ok');
  expect(vm.autenticado, isTrue);
  expect(vm.error, isNull);
});

test('tras autenticar resuelve los ids de piloto del usuario', () async {
  final vm = LoginViewModel(clienteConPartner(partnerId: 91, pilotoIds: [238]));
  await vm.entrar('piloto', 'ok');
  expect(vm.misPilotoIds, [238]);
});

test('un usuario sin ficha de piloto queda con la lista de ids vacia', () async {
  final vm = LoginViewModel(clienteConPartner(partnerId: 91, pilotoIds: []));
  await vm.entrar('admin', 'ok');
  expect(vm.autenticado, isTrue);
  expect(vm.misPilotoIds, isEmpty);
});
```

- [ ] **Step 2: Ejecutar y verificar que falla** → FAIL

- [ ] **Step 3: Implementar el ViewModel** — `ChangeNotifier` puro, sin dependencias de UI,
  con `cargando`/`error`/`autenticado` y captura de `OdooException`.

- [ ] **Step 4: Implementar la vista** — formulario con usuario, contraseña y botón, usando
  `ListenableBuilder` sobre el ViewModel. Dimensionado con `.w`/`.h`/`.sp`.

- [ ] **Step 5: Ejecutar tests y analizador** → PASS + `dart analyze` limpio

- [ ] **Step 6: Commit**

```bash
git add lib/feature/login test/feature/login lib/main.dart
git commit -m "feat: pantalla de login contra Odoo"
```

---

## Task 10: Lista de partes de vuelo

**Files:**
- Create: `lib/feature/lista/lista_viewmodel.dart`
- Create: `lib/feature/lista/rol_en_parte.dart`
- Create: `lib/feature/lista/lista_view.dart`
- Test: `test/feature/lista/rol_en_parte_test.dart`
- Test: `test/feature/lista/lista_viewmodel_test.dart`

**Interfaces:**
- Consumes: `VueloRepository`, `misPilotoIds` (Task 9).
- Produces:
  - `enum RolEnParte { pic, supervisor }`
  - `RolEnParte? rolEnParte({required int? pilotoId, required int? supervisorId, required List<int> misPilotoIds})`
  - `ListaViewModel { List<VueloResumen> partes; bool cargando; String? error; bool get sinFichaDePiloto; Future<void> cargar(); Future<void> cargarMas(); }`

La lista muestra **solo los partes propios**: aquellos en los que el usuario es `piloto_id` o
`piloto_supervisor_id` (spec §15.1). Cada fila lleva un distintivo de rol (spec §15.2):
**PIC** si el usuario es el piloto al mando, **SUP** si es el supervisor. Si se cumplen las
dos condiciones prevalece PIC.

Columnas y decoración: spec §15.3. Cada fila muestra el distintivo de rol, `semaforo_firma`,
`codigo`, `helicoptero_id`, foto del piloto, `piloto_id`, fecha de salida y `tiemposervicio`
en `HH:MM`. Color de fondo por `estado`: cerrado verde, cancelado rojo, postvuelo ámbar,
prevuelo azul.

- [ ] **Step 1: Escribir el test del distintivo de rol que falla**

`test/feature/lista/rol_en_parte_test.dart`:
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:parte_vuelo_app/feature/lista/rol_en_parte.dart';

void main() {
  test('soy PIC si el piloto del parte es uno de mis ids', () {
    expect(rolEnParte(pilotoId: 238, supervisorId: null, misPilotoIds: [238]),
        RolEnParte.pic);
  });

  test('soy SUP si solo aparezco como supervisor', () {
    expect(rolEnParte(pilotoId: 900, supervisorId: 238, misPilotoIds: [238]),
        RolEnParte.supervisor);
  });

  test('si soy piloto y supervisor a la vez prevalece PIC', () {
    expect(rolEnParte(pilotoId: 238, supervisorId: 238, misPilotoIds: [238]),
        RolEnParte.pic);
  });

  test('si no aparezco en ninguno de los dos roles no hay distintivo', () {
    expect(rolEnParte(pilotoId: 900, supervisorId: 901, misPilotoIds: [238]), isNull);
  });

  test('con varios ids de piloto vale cualquiera de ellos', () {
    expect(rolEnParte(pilotoId: 400, supervisorId: null, misPilotoIds: [238, 400]),
        RolEnParte.pic);
  });
}
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `flutter test test/feature/lista/rol_en_parte_test.dart`
Expected: FAIL — `rol_en_parte.dart` no existe.

- [ ] **Step 3: Implementar `rol_en_parte.dart`**

```dart
enum RolEnParte { pic, supervisor }

// Solo estos dos roles pueden firmar el parte (spec §8.3), y son los unicos por los que
// la lista filtra (spec §15.1). PIC gana si el usuario es a la vez piloto y supervisor.
RolEnParte? rolEnParte({
  required int? pilotoId,
  required int? supervisorId,
  required List<int> misPilotoIds,
}) {
  if (pilotoId != null && misPilotoIds.contains(pilotoId)) return RolEnParte.pic;
  if (supervisorId != null && misPilotoIds.contains(supervisorId)) return RolEnParte.supervisor;
  return null;
}
```

- [ ] **Step 4: Escribir el test del ViewModel que falla**

`test/feature/lista/lista_viewmodel_test.dart`:
```dart
test('cargar rellena la lista y desactiva el spinner', () async {
  final vm = ListaViewModel(repoConPartes([resumen(codigo: 'VUL-0019153')]), misPilotoIds: [238]);
  final f = vm.cargar();
  expect(vm.cargando, isTrue);
  await f;
  expect(vm.cargando, isFalse);
  expect(vm.partes.single.codigo, 'VUL-0019153');
});

test('un error de red se expone en error sin dejar la lista a medias', () async {
  final vm = ListaViewModel(repoQueFalla(), misPilotoIds: [238]);
  await vm.cargar();
  expect(vm.error, isNotNull);
  expect(vm.partes, isEmpty);
});

test('sin ficha de piloto no se llama al servidor y se marca el caso', () async {
  final repo = repoEspia();
  final vm = ListaViewModel(repo, misPilotoIds: []);
  await vm.cargar();
  expect(repo.llamadas, isEmpty);
  expect(vm.sinFichaDePiloto, isTrue);
  expect(vm.partes, isEmpty);
});

test('cargarMas acumula sin duplicar y respeta el offset', () async {
  final repo = repoPaginado(pagina1: ['A'], pagina2: ['B']);
  final vm = ListaViewModel(repo, misPilotoIds: [238]);
  await vm.cargar();
  await vm.cargarMas();
  expect(vm.partes.map((p) => p.codigo), ['A', 'B']);
  expect(repo.ultimoOffset, 1);
});
```

- [ ] **Step 5: Ejecutar y verificar que falla** → FAIL

- [ ] **Step 6: Implementar el ViewModel**

`cargar()` delega en `repo.listar(misPilotoIds: misPilotoIds, limit: 40, offset: 0)`.
Si `misPilotoIds` está vacío, marca `sinFichaDePiloto` y no llama al servidor.

- [ ] **Step 7: Escribir el test de widget que falla**

```dart
testWidgets('cada fila muestra el distintivo de rol correcto', (t) async {
  await t.pumpWidget(listaCon(misPilotoIds: [238], partes: [
    resumen(codigo: 'A', pilotoId: 238, supervisorId: null),
    resumen(codigo: 'B', pilotoId: 900, supervisorId: 238),
  ]));
  expect(find.text('PIC'), findsOneWidget);
  expect(find.text('SUP'), findsOneWidget);
});

testWidgets('sin ficha de piloto se muestra el mensaje en lugar de una lista vacia', (t) async {
  await t.pumpWidget(listaCon(misPilotoIds: [], partes: []));
  expect(find.text('No tienes partes de vuelo asignados'), findsOneWidget);
});
```

- [ ] **Step 8: Implementar la vista**

`ListView.builder` con pull-to-refresh, paginación por `offset` al llegar al final y FAB
"Nuevo parte". El distintivo de rol es un chip a la izquierda del código: **PIC** en color
de énfasis, **SUP** en color secundario. Ambos con `Semantics(label: 'Piloto al mando')` /
`'Piloto supervisor'` para lectores de pantalla.

- [ ] **Step 9: Ejecutar tests y analizador**

Run: `flutter test test/feature/lista/` → PASS
Run: `dart analyze` → sin errores

- [ ] **Step 10: Commit**

```bash
git add lib/feature/lista test/feature/lista
git commit -m "feat: listado de partes propios con distintivo de rol PIC o supervisor"
```

---

## Task 11: `ParteViewModel` — el núcleo del formulario

Es la pieza más delicada del proyecto: mantiene el estado del formulario, orquesta los
`onchange` contra el servidor y calcula la visibilidad/readonly de cada campo.

**Files:**
- Create: `lib/feature/parte/parte_viewmodel.dart`
- Create: `lib/feature/parte/field_rules.dart`
- Test: `test/feature/parte/parte_viewmodel_test.dart`
- Test: `test/feature/parte/field_rules_test.dart`

**Interfaces:**
- Consumes: `VueloRepository`, `Vuelo`, `calcularFuel`, `OdooAction`.
- Produces:
  ```dart
  class ParteViewModel extends ChangeNotifier {
    Vuelo get vuelo;
    bool get cargando; bool get sucio; String? get errorNegocio; String? get avisoNegocio;
    Future<void> abrir(int id);
    Future<void> cambiarCampo(String campo, dynamic valor);   // aplica local + onchange servidor
    Future<void> guardar();
    Future<OdooAction?> pulsarBoton(String metodo);
    Future<void> cambiarPantalla(EstadoVista v);
  }
  // field_rules.dart
  bool esVisible(String campo, Vuelo v);
  bool esSoloLectura(String campo, Vuelo v);
  ```

- [ ] **Step 1: Escribir el test de reglas de campo que falla**

`test/feature/parte/field_rules_test.dart` — codifica literalmente las columnas
`RO` y `Vis` de spec §4:
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:parte_vuelo_app/domain/vuelo_enums.dart';
import 'package:parte_vuelo_app/feature/parte/field_rules.dart';

void main() {
  test('helicoptero_id es editable en prevuelo y readonly en postvuelo', () {
    expect(esSoloLectura('helicoptero_id', vueloEn(Estado.prevuelo)), isFalse);
    expect(esSoloLectura('helicoptero_id', vueloEn(Estado.postvuelo)), isTrue);
    expect(esSoloLectura('helicoptero_id', vueloEn(Estado.cerrado)), isTrue);
  });

  test('airtime solo es editable en postvuelo', () {
    expect(esSoloLectura('airtime', vueloEn(Estado.prevuelo)), isTrue);
    expect(esSoloLectura('airtime', vueloEn(Estado.postvuelo)), isFalse);
    expect(esSoloLectura('airtime', vueloEn(Estado.cerrado)), isTrue);
  });

  test('checklist_prevuelo_BFF solo se ve con inspeccion hecha y tipo EC120B o CABRI G2', () {
    expect(esVisible('checklist_prevuelo_BFF',
        vueloCon(checklistRealizado: true, tipo: 'EC120B')), isTrue);
    expect(esVisible('checklist_prevuelo_BFF',
        vueloCon(checklistRealizado: true, tipo: 'R44')), isFalse);
    expect(esVisible('checklist_prevuelo_BFF',
        vueloCon(checklistRealizado: false, tipo: 'EC120B')), isFalse);
  });

  test('tacom se oculta y NG/NF se muestra en EC120B', () {
    expect(esVisible('tacomllegada', vueloCon(tipo: 'EC120B')), isFalse);
    expect(esVisible('ngvuelo', vueloCon(tipo: 'EC120B')), isTrue);
    expect(esVisible('tacomllegada', vueloCon(tipo: 'R44')), isTrue);
    expect(esVisible('ngvuelo', vueloCon(tipo: 'R44')), isFalse);
  });

  test('verificado se oculta si hay alumno y viceversa', () {
    expect(esVisible('verificado', vueloConAlumno()), isFalse);
    expect(esVisible('alumno', vueloConVerificado()), isFalse);
  });

  test('lugarsalida es readonly si el usuario no es comercial', () {
    expect(esSoloLectura('lugarsalida', vueloCon(esComercial: false)), isTrue);
  });
}
```

- [ ] **Step 2: Ejecutar y verificar que falla** → FAIL

- [ ] **Step 3: Implementar `field_rules.dart`**

Un `switch` por nombre de campo que devuelve la expresión traducida de spec §4. Nada de
lógica ad hoc en las vistas: **toda** condición de visibilidad y readonly vive aquí.

- [ ] **Step 4: Escribir el test del ViewModel que falla**

`test/feature/parte/parte_viewmodel_test.dart`:
```dart
test('cambiarCampo aplica el valor local y luego el resultado del onchange', () async {
  final vm = ParteViewModel(repoConOnchange({'velocidadprevista': 110.0, 'tacomsalida': 3.2}));
  await vm.abrir(18864);
  await vm.cambiarCampo('helicoptero_id', 87);
  expect(vm.vuelo.velocidadprevista, 110.0);
  expect(vm.vuelo.tacomsalida, 3.2);
  expect(vm.sucio, isTrue);
});

test('un warning del onchange se expone en avisoNegocio', () async {
  final vm = ParteViewModel(repoConWarning('Este helicoptero tiene una anomalía/discrepancia sin firmar y no puede ser utilizado'));
  await vm.abrir(18864);
  await vm.cambiarCampo('helicoptero_id', 87);
  expect(vm.avisoNegocio, contains('anomalía'));
});

test('tocar un parametro de combustible invalida W&B y Performance', () async {
  final vm = ParteViewModel(repoConOnchange({'weight_and_balance_id': false, 'performance': []}));
  await vm.abrir(18864);
  await vm.cambiarCampo('fuelqty', 60.0);
  expect(vm.vuelo.weightAndBalanceId, isNull);
  expect(vm.vuelo.validTakeoffLongcg, isFalse);
});

test('un UserError al pulsar Firmar se expone en errorNegocio intacto', () async {
  const msg = 'Este vuelo no puede pasar a postvuelo. NO HA REVISADO NOTAM';
  final vm = ParteViewModel(repoQueLanzaEnBoton(OdooUserError(msg)));
  await vm.abrir(18864);
  await vm.pulsarBoton('firmar_doc_parte_vuelo');
  expect(vm.errorNegocio, msg);
});

test('marcar BFF desmarca entre vuelos y viceversa', () async {
  final vm = ParteViewModel(repoConOnchange({'checklist_prevuelo_entre_vuelos': false}));
  await vm.abrir(18864);
  await vm.cambiarCampo('checklist_prevuelo_BFF', true);
  expect(vm.vuelo.checklistPrevueloEntreVuelos, isFalse);
});
```

- [ ] **Step 5: Ejecutar y verificar que falla** → FAIL

- [ ] **Step 6: Implementar `ParteViewModel`**

Reglas de implementación:
- `cambiarCampo` aplica el valor en local, notifica (feedback instantáneo), **y solo si el
  campo está en la lista de campos con `on_change`** (spec §6) llama a
  `repo.onchange(id, valoresActuales, [campo])` y aplica `result.value` sobre el modelo.
- Las llamadas `onchange` se serializan (una en vuelo cada vez) y se descartan las
  respuestas obsoletas: si el usuario cambia otro campo mientras hay una petición en curso,
  la respuesta de la anterior no debe pisar la edición nueva. Usar un contador de secuencia.
- `guardar()` envía `vuelo.toWriteValues()` completo (incluidos los `force_save`).
- `pulsarBoton` captura `OdooException`, guarda `errorNegocio` y devuelve la `OdooAction`.
- `cambiarPantalla` llama al `action_cambiar_pantalla_*` correspondiente (spec §2.2) y
  actualiza `estadoVista`.

- [ ] **Step 7: Ejecutar tests y analizador** → PASS + `dart analyze` limpio

- [ ] **Step 8: Commit**

```bash
git add lib/feature/parte/parte_viewmodel.dart lib/feature/parte/field_rules.dart test/feature/parte
git commit -m "feat: viewmodel del parte de vuelo con onchange de servidor y reglas de campo"
```

---

## Task 12: Shell del formulario (cabecera, navegación, acciones, pie)

**Files:**
- Create: `lib/feature/parte/parte_shell_view.dart`
- Create: `lib/feature/parte/pie_comun_view.dart`
- Create: `lib/feature/parte/widgets/semaforo_indicator.dart`
- Create: `lib/feature/parte/widgets/float_time_field.dart`
- Test: `test/feature/parte/parte_shell_view_test.dart`

**Interfaces:**
- Consumes: `ParteViewModel`, `field_rules.dart`, `OdooAction`.
- Produces: `ParteShellView(vuelo)` con el `Scaffold`, el stepper de `estado`, el selector de
  `estado_vista` y la barra de acciones; `SemaforoIndicator(valor)`; `FloatTimeField({double? value, ValueChanged<double> onChanged, bool readOnly, bool paso6Minutos = false})`.

- [ ] **Step 1: Escribir el test de widget que falla**

```dart
testWidgets('el boton Postvuelo no aparece si el parte esta en prevuelo', (t) async {
  await t.pumpWidget(shellCon(estado: Estado.prevuelo));
  expect(find.widgetWithText(TextButton, 'Postvuelo'), findsNothing);
  expect(find.widgetWithText(TextButton, 'Prevuelo 2'), findsOneWidget);
});

testWidgets('el boton Firmar solo aparece si can_sign', (t) async {
  await t.pumpWidget(shellCon(canSign: false));
  expect(find.widgetWithText(ElevatedButton, 'Firmar'), findsNothing);
  await t.pumpWidget(shellCon(canSign: true));
  await t.pump();
  expect(find.widgetWithText(ElevatedButton, 'Firmar'), findsOneWidget);
});

testWidgets('el boton Set to Pre-Vuelo solo aparece en postvuelo, cerrado o cancelado', (t) async {
  await t.pumpWidget(shellCon(estado: Estado.prevuelo));
  expect(find.text('Set to Pre-Vuelo'), findsNothing);
  await t.pumpWidget(shellCon(estado: Estado.cerrado));
  await t.pump();
  expect(find.text('Set to Pre-Vuelo'), findsOneWidget);
});

testWidgets('FloatTimeField muestra 2.5 como 02:30', (t) async {
  await t.pumpWidget(campoTiempo(2.5));
  expect(find.text('02:30'), findsOneWidget);
});
```

- [ ] **Step 2: Ejecutar y verificar que falla** → FAIL

- [ ] **Step 3: Implementar los widgets base**

`SemaforoIndicator`: círculo de color según `'red'`/`'orange'`/`'green'`; devuelve
`SizedBox.shrink()` si el valor es `'N/A'` o nulo (spec §5).
`FloatTimeField`: muestra `floatTimeToStr(value)`, abre un `TimePicker` al pulsar y devuelve
`hora + minuto/60`. Cuando `paso6Minutos` es `true` (caso `airtime`, spec §7.3), redondea el
minuto al múltiplo de 6 más cercano.

- [ ] **Step 4: Implementar `ParteShellView` y `PieComunView`**

Cabecera: stepper de `estado` no interactivo, `codigo` y creador, y el selector de
`estado_vista` con las reglas de spec §2.2. Barra de acciones con los 5 botones de spec §3.1.
Al pulsar cualquier botón se llama a `vm.pulsarBoton` y se despacha la `OdooAction`
resultante (spec §11.7). Los `OdooUserError` se muestran en un `AlertDialog` con el texto
íntegro y un solo botón "Entendido".

Pie común: `nv`, `nv_uid`, `ifr`, y dos `ExpansionTile` con las imputaciones de tiempo y los
documentos firmados (spec §4.5).

- [ ] **Step 5: Implementar `cerrado_view.dart` (pantalla 4)**

Es la pantalla más simple: spec §4.4. Todos los bloques operativos ocultos, solo cabecera,
anotaciones y anomalías si las hay, y el pie común. **Sin ningún campo editable.** Se
implementa aquí porque es literalmente el shell sin cuerpo:

```dart
class CerradoView extends StatelessWidget {
  const CerradoView({super.key, required this.vm});

  final ParteViewModel vm;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: EdgeInsets.all(12.w),
      children: [
        ResumenParteCard(vuelo: vm.vuelo),                       // codigo, fechas, tripulacion, tiempos
        if (vm.vuelo.anotacionIds.isNotEmpty)
          AnotacionesCard(lineas: vm.vuelo.anotacionIds),
        if (vm.vuelo.diferidoIds.isNotEmpty)
          AnomaliasCard(lineas: vm.vuelo.diferidoIds),
        PieComunView(vm: vm, soloLectura: true),
      ],
    );
  }
}
```

Test que lo acompaña:
```dart
testWidgets('la pantalla de cerrado no expone ningun campo editable', (t) async {
  await t.pumpWidget(cerradoCon(estado: Estado.cerrado));
  expect(find.byType(TextField), findsNothing);
  expect(find.byType(Switch), findsNothing);
});
```

- [ ] **Step 6: Ejecutar tests** → PASS

- [ ] **Step 7: Commit**

```bash
git add lib/feature/parte/parte_shell_view.dart lib/feature/parte/pie_comun_view.dart lib/feature/parte/cerrado_view.dart lib/feature/parte/widgets test/feature/parte/parte_shell_view_test.dart
git commit -m "feat: shell del formulario de parte con navegacion de pantallas y acciones"
```

---

## Task 13: Pantalla 1 — Prevuelo

**Files:**
- Create: `lib/feature/parte/prevuelo_view.dart`
- Create: `lib/feature/parte/widgets/m2o_picker_field.dart`
- Create: `lib/feature/parte/widgets/fuel_card.dart`
- Create: `lib/data/catalog_repository.dart`
- Test: `test/feature/parte/prevuelo_view_test.dart`
- Test: `test/data/catalog_repository_test.dart`

**Interfaces:**
- Consumes: `ParteViewModel`, `field_rules.dart`, `FloatTimeField`, `SemaforoIndicator`.
- Produces: `PrevueloView`; `M2oPickerField({model, domain, value, onChanged, readOnly, allowCreate:false})`;
  `FuelCard({titulo, litros, kg, gal, onLitrosChanged, readOnly})`;
  `CatalogRepository.buscar(String model, String texto, {List domain})`.

Contenido exacto: bloques A a J de spec §4.1, **en ese orden**. Cada campo consulta
`esVisible`/`esSoloLectura` de Task 11 y escribe mediante `vm.cambiarCampo`.
Domains de los selectores: tabla de spec §11.3. Ningún selector permite crear registros.

Los bloques **D (Anotaciones Technical Log)** y **E (Anomalías/Discrepancias)** son
**solo informativos**: se pintan como tarjetas de solo lectura, sus filas **no son
pulsables** y no llevan acciones de crear, editar ni borrar. Ambos se ocultan si la lista
está vacía. Como una anotación activa o una anomalía sin firmar **impiden firmar el parte**
(spec §7.1-5), estas dos tarjetas van con tratamiento de aviso —icono y color de
advertencia—, no como una lista más.

- [ ] **Step 1: Escribir el test que falla**

```dart
testWidgets('en prevuelo se ven los bloques de tripulacion y combustible', (t) async {
  await t.pumpWidget(prevueloCon(estadoVista: EstadoVista.prevuelo));
  expect(find.text('Tripulantes'), findsOneWidget);
  expect(find.text('Combustible'), findsOneWidget);
  expect(find.text('Ruta'), findsOneWidget);
});

testWidgets('el bloque Escuela aparece al haber alumno', (t) async {
  await t.pumpWidget(prevueloCon(alumno: null));
  expect(find.text('Escuela'), findsNothing);
  await t.pumpWidget(prevueloCon(alumno: const Ref(5, 'Alumno Prueba')));
  await t.pump();
  expect(find.text('Escuela'), findsOneWidget);
});

testWidgets('la tarjeta Tacom se oculta con EC120B', (t) async {
  await t.pumpWidget(prevueloCon(tipo: 'EC120B'));
  expect(find.text('Tacom'), findsNothing);
});

testWidgets('editar los litros de fuel añadido llama a cambiarCampo', (t) async {
  final vm = vmEspia();
  await t.pumpWidget(prevueloConVm(vm));
  await t.enterText(find.byKey(const Key('fuelqty')), '60');
  await t.pump();
  expect(vm.camposCambiados, contains('fuelqty'));
});

testWidgets('las tarjetas de Technical Log y anomalias se ocultan si no hay lineas', (t) async {
  await t.pumpWidget(prevueloCon(anotaciones: const [], anomalias: const []));
  expect(find.text('Anotaciones Technical Log'), findsNothing);
  expect(find.text('Anomalías/Discrepancias'), findsNothing);
});

testWidgets('las filas de anomalias no son pulsables', (t) async {
  final vm = vmEspia();
  await t.pumpWidget(prevueloConVm(vm, anomalias: [anomalia(codigo: 'ANO-001')]));
  await t.tap(find.text('ANO-001'));
  await t.pumpAndSettle();
  expect(vm.accionesLanzadas, isEmpty);          // no abre ninguna ficha
  expect(find.text('ANO-001'), findsOneWidget);  // seguimos en la misma pantalla
});

testWidgets('una anotacion activa se presenta como aviso, no como lista normal', (t) async {
  await t.pumpWidget(prevueloCon(anotaciones: [anotacion(codigo: 'ATL-007')]));
  expect(find.byKey(const Key('aviso_anotaciones')), findsOneWidget);
});
```

- [ ] **Step 2: Ejecutar y verificar que falla** → FAIL

- [ ] **Step 3: Implementar `CatalogRepository`**

`buscar(model, texto, {domain})` → `callKw(model: model, method: 'name_search',
kwargs: {'name': texto, 'args': domain, 'operator': 'ilike', 'limit': 20})`.
Devuelve `List<Ref>`. Con debounce de 300 ms en el widget, no en el repositorio.

- [ ] **Step 4: Implementar `M2oPickerField` y `FuelCard`**

`M2oPickerField` abre un modal con buscador y lista de resultados. `FuelCard` muestra el
campo de litros y un `ExpansionTile` con kg y gal en solo lectura (spec §4.1 H).

- [ ] **Step 5: Implementar `PrevueloView`** con los bloques A–J.

- [ ] **Step 6: Ejecutar tests y analizador** → PASS + `dart analyze` limpio

- [ ] **Step 7: Commit**

```bash
git add lib/feature/parte/prevuelo_view.dart lib/feature/parte/widgets lib/data/catalog_repository.dart test/feature/parte/prevuelo_view_test.dart test/data/catalog_repository_test.dart
git commit -m "feat: pantalla de prevuelo con selectores, checks y bloque de combustible"
```

---

## Task 14: Pantalla 2 — Prevuelo 2 (meteo, NOTAM y comentarios)

**Files:**
- Create: `lib/feature/parte/prevuelo2_view.dart`
- Test: `test/feature/parte/prevuelo2_view_test.dart`

**Interfaces:**
- Consumes: `ParteViewModel`, `OdooAction`.
- Produces: `Prevuelo2View`.

Contenido: spec §4.2 — `indicativometeo`, botón "Obtener meteo", `meteo` (texto
monoespaciado con scroll), `notam_revisado`, `notaminfo` (visor HTML de solo lectura),
enlaces externos a Insignia (ENAIRE) e ICAO iSTARS, pestaña Comentarios, botón "Weight and
Balance", los 4 semáforos `valid_*cg` y el botón "Performance".

- [ ] **Step 1: Escribir el test que falla**

```dart
testWidgets('Obtener meteo muestra la notificacion devuelta por el servidor', (t) async {
  final vm = vmConAccion(const DisplayNotification(
      title: 'Meteorología actualizada', message: 'Meteorología obtenida para LELL',
      type: 'success', sticky: false));
  await t.pumpWidget(prevuelo2ConVm(vm));
  await t.tap(find.text('Obtener meteo'));
  await t.pump();
  expect(find.text('Meteorología obtenida para LELL'), findsOneWidget);
});

testWidgets('los cuatro semaforos de W&B se pintan en rojo si no hay W&B', (t) async {
  await t.pumpWidget(prevuelo2Con(validos: false));
  expect(find.byWidgetPredicate((w) => w is SemaforoIndicator && w.valor == 'red'), findsNWidgets(4));
});

testWidgets('Obtener meteo sin indicativo muestra el UserError del servidor', (t) async {
  final vm = vmQueLanza(OdooUserError('Introduce un indicativo OACI en el campo "Indicativo meteo".'));
  await t.pumpWidget(prevuelo2ConVm(vm));
  await t.tap(find.text('Obtener meteo'));
  await t.pumpAndSettle();
  expect(find.textContaining('Introduce un indicativo OACI'), findsOneWidget);
});
```

- [ ] **Step 2: Ejecutar y verificar que falla** → FAIL
- [ ] **Step 3: Implementar la vista**
- [ ] **Step 4: Ejecutar tests** → PASS
- [ ] **Step 5: Commit**

```bash
git add lib/feature/parte/prevuelo2_view.dart test/feature/parte/prevuelo2_view_test.dart
git commit -m "feat: pantalla prevuelo 2 con meteo, NOTAM y accesos a W&B y performance"
```

---

## Task 15: Weight & Balance

**Files:**
- Create: `lib/feature/wb/wb_envelopes.dart`
- Create: `lib/feature/wb/wb_viewmodel.dart`
- Create: `lib/feature/wb/wb_view.dart`
- Create: `lib/data/wb_repository.dart`
- Test: `test/feature/wb/wb_envelopes_test.dart`
- Test: `test/feature/wb/wb_viewmodel_test.dart`

**Interfaces:**
- Consumes: `OdooClient`, `ParteViewModel` (para el contexto de defaults).
- Produces:
  - `class Punto { final double x, y; }`
  - `bool pointInPoly(Punto pt, List<Punto> poly)`
  - `Map<String, ({List<Punto> long, List<Punto> lat})> envolventes`
  - `({bool takeoffLong, bool takeoffLat, bool landingLong, bool landingLat}) validarCg({required String clave, required double takeoffGw, required double takeoffLongArm, required double takeoffLatArm, required double landingGw, required double landingLongArm, required double landingLatArm})`
  - `WbViewModel { Future<void> abrir(int vueloId); void cambiarPeso(String campo, double v); void cambiarCb(String campo, bool v); Future<void> guardar(); }`

- [ ] **Step 1: Escribir el test de envolventes que falla**

`test/feature/wb/wb_envelopes_test.dart`:
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:parte_vuelo_app/feature/wb/wb_envelopes.dart';

void main() {
  test('un punto claramente interior del EC120B es valido', () {
    // envolvente long EC120B: y (peso) entre 1035 y 1715, x (brazo) entre 383 y 416
    expect(pointInPoly(const Punto(x: 400, y: 1400), envolventes['EC120B']!.long), isTrue);
  });

  test('un punto por encima del peso maximo del EC120B es invalido', () {
    expect(pointInPoly(const Punto(x: 400, y: 1900), envolventes['EC120B']!.long), isFalse);
  });

  test('un punto con brazo fuera de rango es invalido', () {
    expect(pointInPoly(const Punto(x: 370, y: 1400), envolventes['EC120B']!.long), isFalse);
  });

  test('EC-HIL admite mas peso que el EC120B estandar', () {
    const p = Punto(x: 400, y: 1760);
    expect(pointInPoly(p, envolventes['EC120B']!.long), isFalse);
    expect(pointInPoly(p, envolventes['EC-HIL']!.long), isTrue);
  });

  test('R44 Raven II admite mas peso que R44 Raven I', () {
    const p = Punto(x: 245, y: 1110);
    expect(pointInPoly(p, envolventes['R44 Raven I']!.long), isFalse);
    expect(pointInPoly(p, envolventes['R44 Raven II']!.long), isTrue);
  });

  test('validarCg devuelve los cuatro booleanos', () {
    final r = validarCg(
      clave: 'EC120B',
      takeoffGw: 1400, takeoffLongArm: 400, takeoffLatArm: 0,
      landingGw: 1200, landingLongArm: 400, landingLatArm: 0,
    );
    expect(r.takeoffLong, isTrue);
    expect(r.takeoffLat, isTrue);
    expect(r.landingLong, isTrue);
    expect(r.landingLat, isTrue);
  });
}
```

- [ ] **Step 2: Ejecutar y verificar que falla** → FAIL

- [ ] **Step 3: Implementar `wb_envelopes.dart`**

Port literal de spec §9.4: las 9 entradas del mapa `envolventes` (`R22`, `R44`,
`R44 Raven I`, `R44 Clipper I`, `R44 Astro`, `R44 Raven II`, `R44 Clipper II`, `EC120B`,
`EC-HIL`, `CABRI G2`) con los pares `(y, x)` exactos, y `pointInPoly` traducido del
JavaScript sin cambiar el algoritmo.

La clave se resuelve así (spec §9.4): si `helicoptero_id.name == 'EC-HIL'` se usa `EC-HIL`;
en cualquier otro caso, `helicoptero_modelo`.

- [ ] **Step 4: Escribir el test del ViewModel que falla**

```dart
test('cambiar un peso recalcula totales y semaforos sin ir al servidor', () {
  final vm = wbViewModelR44Cargado();
  vm.cambiarPeso('frs', 80);
  expect(vm.takeoffGw, greaterThan(0));
  expect(vm.validTakeoffLongcg, isTrue);
});

test('desmarcar el cb de un elemento lo excluye del total', () {
  final vm = wbViewModelR44Cargado();
  final antes = vm.takeoffGw;
  vm.cambiarCb('dualcontrols_cb', false);
  expect(vm.takeoffGw, lessThan(antes));
});

test('pasajeros_wb cuenta los asientos con peso mayor que cero', () {
  final vm = wbViewModelR44Cargado();
  vm.cambiarPeso('frs', 80);
  vm.cambiarPeso('fls', 75);
  vm.cambiarPeso('aftrp', 0);
  expect(vm.pasajerosWb, 2);
});
```

- [ ] **Step 5: Ejecutar y verificar que falla** → FAIL

- [ ] **Step 6: Implementar `WbRepository` y `WbViewModel`**

- `WbRepository.abrirDesdeVuelo(vueloId)` llama a `leulit.vuelo.wizard_add_wb([id])`, obtiene
  el `ActWindow` con `res_id` y `context`, y hace `web_read` del W&B con los campos que
  indique `fieldslist` (spec §9.2) más los de fuel y totales.
- `WbViewModel` reimplementa `updateTotals` (spec §9.3) **exactamente**, incluidos los cruces
  `takeoff_gw = total - fuellanding` y `landing_gw = total - fueltakeoff`.
- Tras cada cambio recalcula los cuatro `valid_*cg` con `validarCg`.
- `guardar()` escribe todos los campos calculados y luego llama a
  `leulit.weight_and_balance.btn_save_wizard([id])`, propagando el `UserError` si lo hay.
- La vista muestra, junto al botón de guardar, el contador
  `pasajerosWb` vs `numtripulacion + numpax + numpae` con un aviso visible si no coinciden
  (spec §9.5).

- [ ] **Step 7: Implementar `WbView`**

Formulario dinámico generado a partir de `fieldslist`: por cada clave, un campo numérico de
peso y, si existe, un `Switch` para el `_cb`. Arriba, un panel con `takeoff_gw`,
`landing_gw`, brazos y los cuatro semáforos.

- [ ] **Step 8: Ejecutar tests y analizador** → PASS + `dart analyze` limpio

- [ ] **Step 9: Commit**

```bash
git add lib/feature/wb lib/data/wb_repository.dart test/feature/wb
git commit -m "feat: weight and balance con envolventes de centro de gravedad en cliente"
```

---

## Task 16: Performance — cálculo del punto sobre las curvas

Solo el motor de cálculo. El renderizado y el guardado van en la Task 16b, para que el
algoritmo quede cubierto por tests puros antes de tocar píxeles.

**Files:**
- Create: `lib/feature/performance/performance_constants.dart` (copiar tal cual desde `docs/superpowers/specs/assets/performance_constants.dart`)
- Create: `lib/feature/performance/performance_math.dart`
- Test: `test/feature/performance/performance_math_test.dart`

**Interfaces:**
- Consumes: `perfCharts`, `perfChartPorModelo` (constantes generadas).
- Produces:
  - `double calcPeso(double pesoKg, double inicioEje, double proporcion)`
  - `double interpAtX(List<List<double>> pts, double x)`
  - `double calcAltura(List<PerfCurve> curvas, double temperatura, double x)`
  - `({double x, double y}) puntoGrafica(PerfChart chart, double pesoKg, double temperatura)`
  - `({double x, double y}) puntoCanvas(PerfChart chart, double pesoKg, double temperatura)`
  - `({String ige, String oge})? graficasDe(String helicopteroModelo, {required bool esEcHilConGancho})`

- [ ] **Step 1: Copiar las constantes generadas**

```bash
cp docs/superpowers/specs/assets/performance_constants.dart \
   lib/feature/performance/performance_constants.dart
```

No editarlo a mano. Copiar también las 12 imágenes de
`addons/leulit_operaciones/static/src/img/` a `assets/performance/` y declararlas en
`pubspec.yaml` (spec §10.4).

- [ ] **Step 2: Escribir el test que falla**

`test/feature/performance/performance_math_test.dart`:
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:parte_vuelo_app/feature/performance/performance_constants.dart';
import 'package:parte_vuelo_app/feature/performance/performance_math.dart';

void main() {
  test('calcPeso convierte kg a libras antes de escalar', () {
    // r22_in: inicioEje 909 lb, proporcion 0.839722
    final x = calcPeso(500, 909.0, 0.839722);
    expect(x, closeTo((500 * 2.2046227 - 909) * 0.839722, 1e-6));
  });

  test('interpAtX interpola dentro del segmento', () {
    expect(interpAtX([[0, 0], [10, 100]], 5), closeTo(50, 1e-9));
  });

  test('interpAtX extrapola por ambos extremos con el segmento del borde', () {
    expect(interpAtX([[0, 0], [10, 100]], -5), closeTo(-50, 1e-9));
    expect(interpAtX([[0, 0], [10, 100]], 15), closeTo(150, 1e-9));
  });

  test('interpAtX con un solo punto devuelve su y', () {
    expect(interpAtX([[3, 42]], 999), 42);
  });

  test('interpAtX con segmento vertical devuelve la y del extremo', () {
    expect(interpAtX([[5, 10], [5, 20]], 5), anyOf(10, 20));
  });

  test('calcAltura no extrapola por temperatura: satura en la curva extrema', () {
    final curvas = perfCharts['r22_in']!.temperaturas;
    final xMedio = 200.0;
    final fria = calcAltura(curvas, -100, xMedio);   // muy por debajo de -20
    final borde = interpAtX(curvas.first.pts, xMedio);
    expect(fria, closeTo(borde, 1e-9));

    final calida = calcAltura(curvas, 100, xMedio);  // muy por encima de 40
    expect(calida, closeTo(interpAtX(curvas.last.pts, xMedio), 1e-9));
  });

  test('calcAltura interpola linealmente entre dos curvas', () {
    final curvas = perfCharts['r22_in']!.temperaturas;   // curvas a -20, -10, 0, 10, 20, 30, 40
    const x = 300.0;
    final y0  = interpAtX(curvas[2].pts, x);            // 0 ºC
    final y10 = interpAtX(curvas[3].pts, x);            // 10 ºC
    expect(calcAltura(curvas, 5, x), closeTo(y0 + 0.5 * (y10 - y0), 1e-9));
  });

  test('puntoCanvas traslada el origen segun inicioEjeY + alturaImagen', () {
    final chart = perfCharts['r22_in']!;
    final p = puntoGrafica(chart, 500, 20);
    final c = puntoCanvas(chart, 500, 20);
    expect(c.x, closeTo(chart.inicioEjeX + p.x, 1e-9));
    expect(c.y, closeTo(chart.inicioEjeY + chart.alturaImagen + p.y, 1e-9));
  });

  test('graficasDe resuelve las variantes de R44', () {
    expect(graficasDe('R44 Astro', esEcHilConGancho: false)!.ige, 'r44_in');
    expect(graficasDe('R44 Raven II', esEcHilConGancho: false)!.ige, 'r44_2_in');
  });

  test('EC-HIL con gancho usa las curvas hil y sin gancho las de EC120B', () {
    expect(graficasDe('EC120B', esEcHilConGancho: true)!.ige, 'hil_in');
    expect(graficasDe('EC120B', esEcHilConGancho: false)!.ige, 'ec_in');
  });

  test('un modelo no implementado devuelve null', () {
    expect(graficasDe('AS350', esEcHilConGancho: false), isNull);
  });
}
```

- [ ] **Step 3: Ejecutar y verificar que falla**

Run: `flutter test test/feature/performance/performance_math_test.dart`
Expected: FAIL — `performance_math.dart` no existe.

- [ ] **Step 4: Implementación**

`lib/feature/performance/performance_math.dart` — port literal de spec §10.6:
```dart
import 'performance_constants.dart';

// El peso llega en kg desde el W&B; los ejes de las cartas están calibrados en libras.
// El ERP pasa siempre pasarLibras=true, por eso aquí la conversión no es opcional.
double calcPeso(double pesoKg, double inicioEje, double proporcion) =>
    (pesoKg * 2.2046227 - inicioEje) * proporcion;

double interpAtX(List<List<double>> pts, double x) {
  if (pts.length == 1) return pts[0][1];
  final n = pts.length;
  if (x <= pts[0][0]) {
    final dx = pts[1][0] - pts[0][0];
    if (dx == 0) return pts[0][1];
    return pts[0][1] + (x - pts[0][0]) * (pts[1][1] - pts[0][1]) / dx;
  }
  if (x >= pts[n - 1][0]) {
    final dx = pts[n - 1][0] - pts[n - 2][0];
    if (dx == 0) return pts[n - 1][1];
    return pts[n - 2][1] + (x - pts[n - 2][0]) * (pts[n - 1][1] - pts[n - 2][1]) / dx;
  }
  for (var i = 0; i < n - 1; i++) {
    if (x >= pts[i][0] && x <= pts[i + 1][0]) {
      final dx = pts[i + 1][0] - pts[i][0];
      if (dx == 0) return pts[i][1];
      return pts[i][1] + (x - pts[i][0]) * (pts[i + 1][1] - pts[i][1]) / dx;
    }
  }
  return pts[n - 1][1];
}

double calcAltura(List<PerfCurve> curvas, double temperatura, double x) {
  final bandas = [...curvas]..sort((a, b) => a.temp.compareTo(b.temp));
  final n = bandas.length;
  if (n == 0) return 0;
  if (n == 1) return interpAtX(bandas[0].pts, x);
  if (temperatura <= bandas[0].temp) return interpAtX(bandas[0].pts, x);
  if (temperatura >= bandas[n - 1].temp) return interpAtX(bandas[n - 1].pts, x);

  for (var i = 0; i < n - 1; i++) {
    if (temperatura >= bandas[i].temp && temperatura < bandas[i + 1].temp) {
      final y1 = interpAtX(bandas[i].pts, x);
      final y2 = interpAtX(bandas[i + 1].pts, x);
      final ratio = (temperatura - bandas[i].temp) / (bandas[i + 1].temp - bandas[i].temp);
      return y1 + ratio * (y2 - y1);
    }
  }
  return interpAtX(bandas[n - 1].pts, x);
}

({double x, double y}) puntoGrafica(PerfChart chart, double pesoKg, double temperatura) {
  final x = calcPeso(pesoKg, chart.inicioEje, chart.proporcion);
  return (x: x, y: calcAltura(chart.temperaturas, temperatura, x));
}

({double x, double y}) puntoCanvas(PerfChart chart, double pesoKg, double temperatura) {
  final p = puntoGrafica(chart, pesoKg, temperatura);
  return (x: chart.inicioEjeX + p.x, y: chart.inicioEjeY + chart.alturaImagen + p.y);
}

({String ige, String oge})? graficasDe(String helicopteroModelo, {required bool esEcHilConGancho}) {
  if (helicopteroModelo == 'EC120B' && esEcHilConGancho) {
    return perfChartPorModelo['EC-HIL con gancho'];
  }
  return perfChartPorModelo[helicopteroModelo];
}
```

- [ ] **Step 5: Ejecutar y verificar que pasa**

Run: `flutter test test/feature/performance/performance_math_test.dart` → PASS
Run: `dart analyze` → sin errores

- [ ] **Step 6: Commit**

```bash
git add lib/feature/performance/performance_constants.dart lib/feature/performance/performance_math.dart assets/performance pubspec.yaml test/feature/performance/performance_math_test.dart
git commit -m "feat: motor de calculo de performance con las curvas del ERP"
```

---

## Task 16b: Performance — renderizado, pantalla y guardado

**Files:**
- Create: `lib/feature/performance/performance_painter.dart`
- Create: `lib/feature/performance/performance_render.dart`
- Create: `lib/feature/performance/performance_viewmodel.dart`
- Create: `lib/feature/performance/performance_view.dart`
- Create: `lib/data/performance_repository.dart`
- Test: `test/feature/performance/performance_render_test.dart`
- Test: `test/feature/performance/performance_viewmodel_test.dart`

**Interfaces:**
- Consumes: `performance_math.dart`, `OdooClient`, `ParteViewModel`.
- Produces:
  - `class PerformancePainter extends CustomPainter` — pinta imagen de fondo + punto.
  - `Future<String> renderChartDataUrl(PerfChart chart, ui.Image fondo, double peso, double temperatura)` → cadena `data:image/png;base64,...`
  - `PerformanceRepository { Future<PerformanceRecord> abrirDesdeVuelo(int vueloId); Future<void> guardar(int id, {required double temperatura, required String ige, required String oge}); }`
  - `PerformanceViewModel extends ChangeNotifier { double peso; double temperatura; String? error; Future<void> abrir(int vueloId); Future<void> guardar(); }`

- [ ] **Step 1: Escribir el test de renderizado que falla**

`test/feature/performance/performance_render_test.dart`:
```dart
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:parte_vuelo_app/feature/performance/performance_constants.dart';
import 'package:parte_vuelo_app/feature/performance/performance_render.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('el data URL lleva el prefijo exacto que guarda el ERP', () async {
    final chart = perfCharts['r22_in']!;
    final url = await renderChartDataUrl(chart, await fondoDePrueba(chart), 500, 20);
    expect(url.startsWith('data:image/png;base64,'), isTrue);
  });

  test('lo que sigue al prefijo es un PNG valido del tamaño del canvas', () async {
    final chart = perfCharts['r22_in']!;
    final url = await renderChartDataUrl(chart, await fondoDePrueba(chart), 500, 20);
    final bytes = base64Decode(url.split(',').last);
    expect(bytes.sublist(0, 8), [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]);
    final ancho = ByteData.sublistView(Uint8List.fromList(bytes)).getUint32(16);
    final alto  = ByteData.sublistView(Uint8List.fromList(bytes)).getUint32(20);
    expect(ancho, chart.canvasWidth);
    expect(alto, chart.canvasHeight);
  });

  test('dos temperaturas distintas producen imagenes distintas', () async {
    final chart = perfCharts['r22_in']!;
    final fondo = await fondoDePrueba(chart);
    final a = await renderChartDataUrl(chart, fondo, 500, 0);
    final b = await renderChartDataUrl(chart, fondo, 500, 40);
    expect(a, isNot(equals(b)));
  });
}
```

- [ ] **Step 2: Ejecutar y verificar que falla** → FAIL

- [ ] **Step 3: Implementar el pintado**

`performance_painter.dart` y `performance_render.dart`, siguiendo spec §10.6 paso 3:
```dart
void pintarPunto(Canvas canvas, PerfChart chart, double pesoKg, double temperatura) {
  final p = puntoCanvas(chart, pesoKg, temperatura);
  final relleno = Paint()..color = const Color(0xFFFF0000)..style = PaintingStyle.fill;
  final borde = Paint()
    ..color = const Color(0xFFFFFFFF)
    ..style = PaintingStyle.stroke
    ..strokeWidth = 2;
  canvas.drawCircle(Offset(p.x, p.y), 6, relleno);
  canvas.drawCircle(Offset(p.x, p.y), 6, borde);
}
```

`renderChartDataUrl` usa `ui.PictureRecorder` + `Canvas`, dibuja el fondo en `Offset.zero`,
llama a `pintarPunto`, hace `picture.toImage(chart.canvasWidth, chart.canvasHeight)`,
`toByteData(format: ui.ImageByteFormat.png)` y devuelve
`'data:image/png;base64,${base64Encode(bytes)}'`.

**El prefijo `data:image/png;base64,` es obligatorio** (spec §10.7): así lo guarda el ERP y
así lo esperan los ~13.000 registros históricos y los informes. No guardar base64 limpio.

- [ ] **Step 4: Escribir el test del ViewModel que falla**

```dart
test('abrir toma el peso del W&B y deja la temperatura a 0', () async {
  final vm = PerformanceViewModel(repoConPeso(1420.0));
  await vm.abrir(18864);
  expect(vm.peso, 1420.0);
  expect(vm.temperatura, 0);
});

test('un modelo sin performance implementado propaga el UserError del ERP', () async {
  const msg = 'NO SE PUEDE CALCULAR PERFORMANCE PARA ESTE MODELO PORQUE NO HA SIDO IMPLEMENTADO EN EL SISTEMA';
  final vm = PerformanceViewModel(repoQueLanza(OdooUserError(msg)));
  await vm.abrir(18864);
  expect(vm.error, msg);
});

test('guardar persiste temperatura y las dos imagenes con prefijo data url', () async {
  final repo = repoEspia();
  final vm = PerformanceViewModel(repo);
  await vm.abrir(18864);
  vm.temperatura = 28;
  await vm.guardar();
  expect(repo.ultimoWrite['temperatura'], 28);
  expect(repo.ultimoWrite['ige'], startsWith('data:image/png;base64,'));
  expect(repo.ultimoWrite['oge'], startsWith('data:image/png;base64,'));
});

test('no se puede guardar si el modelo no tiene graficas', () async {
  final vm = PerformanceViewModel(repoConModelo('AS350'));
  await vm.abrir(18864);
  expect(vm.puedeGuardar, isFalse);
});
```

- [ ] **Step 5: Ejecutar y verificar que falla** → FAIL

- [ ] **Step 6: Implementar repositorio y ViewModel**

`abrirDesdeVuelo` llama a `leulit.vuelo.button_performance_vuelo([id])`, toma el `res_id` del
`ActWindow` y hace `web_read` de `peso`, `temperatura`, `vuelo`. Propaga el `UserError` de
modelo no implementado tal cual.
`guardar()` renderiza las dos imágenes y escribe `{temperatura, ige, oge}` de una sola vez.

- [ ] **Step 7: Implementar la pantalla**

Campo `peso` en solo lectura, campo `temperatura` editable, y las dos gráficas
(`IN GROUND EFFECT` / `OUT GROUND EFFECT`) pintadas con `CustomPaint` que se repintan al
cambiar la temperatura — el botón "Calcular" del ERP no hace falta: el repintado es
inmediato. Envolver cada gráfica en un contenedor con scroll horizontal, porque los canvas
llegan a 620 px de ancho y no caben en pantalla de móvil.

- [ ] **Step 8: Ejecutar tests y analizador**

Run: `flutter test test/feature/performance/` → PASS
Run: `dart analyze` → sin errores

- [ ] **Step 9: Verificación visual contra el ERP**

Con un parte del entorno de pruebas: calcular el Performance en la app y en el ERP web con
el mismo peso y la misma temperatura, y comprobar que el punto rojo cae **en el mismo sitio**
de la carta. Repetir para al menos tres modelos distintos (uno de cada familia: R22, R44,
EC120B). Esta comprobación no es opcional: un error de signo en `inicioEjeY` da un punto
plausible pero equivocado, y el gráfico acaba en un documento aeronáutico.

- [ ] **Step 10: Commit**

```bash
git add lib/feature/performance lib/data/performance_repository.dart test/feature/performance
git commit -m "feat: renderizado y guardado de las graficas de performance IGE y OGE"
```

---

## Task 17: Pantalla 3 — Postvuelo

**Files:**
- Create: `lib/feature/parte/postvuelo_view.dart`
- Test: `test/feature/parte/postvuelo_view_test.dart`

**Interfaces:**
- Consumes: `ParteViewModel`, `field_rules.dart`, `FloatTimeField`.
- Produces: `PostvueloView`.

Contenido exacto: spec §4.3 — tarjetas Tiempos, Tacom **o** NG/NF según tipo, Combustible
llegada, Gancho y Landings, más el bloque de Escuela si procede.

- [ ] **Step 1: Escribir el test que falla**

```dart
testWidgets('con EC120B se ve NG/NF y no Tacom', (t) async {
  await t.pumpWidget(postvueloCon(tipo: 'EC120B'));
  expect(find.text('NG / NF'), findsOneWidget);
  expect(find.text('Tacom'), findsNothing);
});

testWidgets('con R44 se ve Tacom y no NG/NF', (t) async {
  await t.pumpWidget(postvueloCon(tipo: 'R44'));
  expect(find.text('Tacom'), findsOneWidget);
  expect(find.text('NG / NF'), findsNothing);
});

testWidgets('el airtime solo admite multiplos de 6 minutos', (t) async {
  final vm = vmEspia();
  await t.pumpWidget(postvueloConVm(vm));
  await t.tap(find.byKey(const Key('airtime')));
  await t.pumpAndSettle();
  // seleccionar 01:07 en el picker debe persistir 1.1 (01:06)
  await seleccionarHora(t, 1, 7);
  expect(vm.valorDe('airtime'), closeTo(1.1, 1e-9));
});

testWidgets('cambiar tiemposervicio recalcula hora de llegada y fuel de llegada', (t) async {
  final vm = vmConOnchange({'horallegada': 14.5, 'fuelllegada': 40.0});
  await t.pumpWidget(postvueloConVm(vm));
  await cambiarTiempoServicio(t, 2.5);
  expect(vm.vuelo.horallegada, 14.5);
  expect(vm.vuelo.fuelllegada, 40.0);
});
```

- [ ] **Step 2: Ejecutar y verificar que falla** → FAIL
- [ ] **Step 3: Implementar la vista**
- [ ] **Step 4: Ejecutar tests** → PASS
- [ ] **Step 5: Commit**

```bash
git add lib/feature/parte/postvuelo_view.dart test/feature/parte/postvuelo_view_test.dart
git commit -m "feat: pantalla de postvuelo con tacom o NG/NF segun tipo de aeronave"
```

---

## Task 18: Escuela (sílabus y valoración)

**Files:**
- Create: `lib/feature/escuela/escuela_viewmodel.dart`
- Create: `lib/feature/escuela/escuela_view.dart`
- Test: `test/feature/escuela/escuela_viewmodel_test.dart`

**Interfaces:**
- Consumes: `ParteViewModel`, `VueloRepository`.
- Produces: `EscuelaViewModel { List<SilabusLine> lineas; Future<void> anadirSilabus(); void cambiarValoracion(int idx, String v); void cambiarNota(int idx, double n); }`

Contenido: spec §4.1 bloque G. La columna `valoracion` solo se muestra si `sil_valoracion`;
`nota` solo si `sil_test`; el botón "Adjuntar Doc." solo si `sil_test`. Decoración verde si
`todo_cerrar == False`, ámbar si `True`.

- [ ] **Step 1: Escribir el test que falla**

```dart
test('la columna nota solo se expone en silabus de tipo test', () {
  final vm = escuelaConLineas([linea(silTest: true), linea(silTest: false)]);
  expect(vm.lineas[0].muestraNota, isTrue);
  expect(vm.lineas[1].muestraNota, isFalse);
});

test('anadirSilabus delega en wizard_add_parte_escuela', () async {
  final repo = repoEspia();
  await escuelaCon(repo).anadirSilabus();
  expect(repo.ultimoMetodo, 'wizard_add_parte_escuela');
});
```

- [ ] **Step 2: Ejecutar y verificar que falla** → FAIL
- [ ] **Step 3: Implementar el ViewModel y la vista**
- [ ] **Step 4: Ejecutar tests** → PASS
- [ ] **Step 5: Commit**

```bash
git add lib/feature/escuela test/feature/escuela
git commit -m "feat: bloque de escuela con silabus, valoracion y nota"
```

---

## Task 19: Firma electrónica

**Files:**
- Create: `lib/data/signature_repository.dart`
- Create: `lib/feature/firma/firma_viewmodel.dart`
- Create: `lib/feature/firma/firma_view.dart`
- Test: `test/data/signature_repository_test.dart`
- Test: `test/feature/firma/firma_viewmodel_test.dart`

**Interfaces:**
- Consumes: `OdooClient`, `VueloRepository`.
- Produces:
  - `SignatureRepository { Future<String> codigoServidor(); Future<bool> validar({required String otp, required String notp, required int vueloId}); }`
  - `FirmaViewModel { Future<void> iniciar(int vueloId); String? notp; Future<bool> confirmar(String otp); String? error; }`

**Decisión tomada (2026-08-18): se mantiene el flujo actual del ERP — el piloto teclea el
código** (spec §8.2). El servidor solo compara `otp == notp`, así que técnicamente bastaría
con enviar `otp = notp`; **no se hace**. El parte de vuelo firmado es documento aeronáutico y
el gesto deliberado forma parte del procedimiento vigente. En consecuencia, y esto es
verificable en test:

- el campo de OTP **no se autocompleta** con el código mostrado,
- **no admite pegar** desde el portapapeles,
- `confirmar()` envía como `otp` **lo que el piloto escribió**, nunca el `notp` guardado.

- [ ] **Step 1: Escribir el test que falla**

`test/data/signature_repository_test.dart`:
```dart
test('codigoServidor llama a leulit_signaturedoc.codeFromServer', () async {
  final repo = SignatureRepository(OdooClient(cfg, httpClient: MockClient((req) async {
    final p = (jsonDecode(req.body) as Map<String, dynamic>)['params'] as Map<String, dynamic>;
    expect(p['model'], 'leulit_signaturedoc');
    expect(p['method'], 'codeFromServer');
    return http.Response(jsonEncode({'result': {'notp': '482913'}}), 200);
  })));
  expect(await repo.codigoServidor(), '482913');
});

test('validar envia otp, notp, modelo e idmodelo en context.args', () async {
  final repo = SignatureRepository(OdooClient(cfg, httpClient: MockClient((req) async {
    final p = (jsonDecode(req.body) as Map<String, dynamic>)['params'] as Map<String, dynamic>;
    final args = ((p['kwargs'] as Map)['context'] as Map)['args'] as Map;
    expect(args['otp'], '482913');
    expect(args['notp'], '482913');
    expect(args['modelo'], 'leulit.vuelo');
    expect(args['idmodelo'], 18864);
    return http.Response(jsonEncode({'result': {'valid': true, 'error': false, 'errmsg': ''}}), 200);
  })));
  expect(await repo.validar(otp: '482913', notp: '482913', vueloId: 18864), isTrue);
});
```

`test/feature/firma/firma_viewmodel_test.dart`:
```dart
test('iniciar ejecuta firmar_doc_parte_vuelo antes de pedir el codigo', () async {
  final repo = repoEspia();
  await FirmaViewModel(repo, firmas).iniciar(18864);
  expect(repo.metodosLlamados.first, 'firmar_doc_parte_vuelo');
});

test('un UserError de la cadena aborta la firma y se muestra intacto', () async {
  const msg = 'Este vuelo no puede pasar a postvuelo. NO HA MARCADO LA INSPECCIÓN PREVUELO CÓMO REALIZADA';
  final vm = FirmaViewModel(repoQueLanza(OdooUserError(msg)), firmas);
  await vm.iniciar(18864);
  expect(vm.error, msg);
  expect(vm.notp, isNull);
});

test('el wizard de freelance se propaga como accion en vez de pedir OTP', () async {
  final vm = FirmaViewModel(
    repoConAccion(const ActWindow(model: 'leulit.wizard_freelance_actividad_aerea', resId: null,
        context: {'default_date': '2026-08-18'}, name: 'Actividad Aerea')),
    firmas);
  await vm.iniciar(18864);
  expect(vm.accionPendiente, isA<ActWindow>());
  expect(vm.notp, isNull);
});

test('un OTP incorrecto no avanza el estado', () async {
  final vm = FirmaViewModel(repoOk(), firmasQueDevuelven(false));
  await vm.iniciar(18864);
  expect(await vm.confirmar('000000'), isFalse);
});

test('confirmar envia como otp lo que tecleo el piloto, no el notp del servidor', () async {
  final firmas = firmasEspia(notp: '482913');
  final vm = FirmaViewModel(repoOk(), firmas);
  await vm.iniciar(18864);
  await vm.confirmar('111111');
  expect(firmas.ultimoOtp, '111111');
  expect(firmas.ultimoNotp, '482913');
});
```

- [ ] **Step 2: Ejecutar y verificar que falla** → FAIL

- [ ] **Step 3: Implementar `SignatureRepository`**

`validar` llama a `callKw(model: 'leulit_signaturedoc', method: 'checksignatureRef',
args: [], kwargs: {'context': {'args': {'otp': otp, 'notp': notp, 'modelo': 'leulit.vuelo',
'idmodelo': vueloId}}})` y devuelve `result['valid'] == true`.

- [ ] **Step 4: Implementar `FirmaViewModel`**

Secuencia de spec §8.1: `firmar_doc_parte_vuelo` → si devuelve un `ActWindow`, exponerlo en
`accionPendiente` y parar (caso freelance, spec §7.5) → si no, `codigoServidor()` →
`confirmar(otp)` → recargar el parte.

- [ ] **Step 5: Escribir el test de widget que falla**

`test/feature/firma/firma_view_test.dart`:
```dart
testWidgets('el campo de OTP arranca vacio aunque el codigo este a la vista', (t) async {
  await t.pumpWidget(firmaCon(notp: '482913'));
  expect(find.text('482913'), findsOneWidget);                      // el codigo mostrado
  final campo = t.widget<TextField>(find.byKey(const Key('otp')));
  expect(campo.controller!.text, isEmpty);                          // el campo, vacio
});

testWidgets('el campo de OTP no permite pegar', (t) async {
  await t.pumpWidget(firmaCon(notp: '482913'));
  final campo = t.widget<TextField>(find.byKey(const Key('otp')));
  expect(campo.enableInteractiveSelection, isFalse);
});

testWidgets('Firmar queda deshabilitado hasta que se teclea el codigo completo', (t) async {
  await t.pumpWidget(firmaCon(notp: '482913'));
  expect(t.widget<ElevatedButton>(find.byKey(const Key('confirmar'))).onPressed, isNull);
  await t.enterText(find.byKey(const Key('otp')), '482913');
  await t.pump();
  expect(t.widget<ElevatedButton>(find.byKey(const Key('confirmar'))).onPressed, isNotNull);
});
```

- [ ] **Step 6: Implementar `FirmaView`**

Diálogo con el código devuelto por el servidor a la vista, un campo **vacío** para teclearlo
(`enableInteractiveSelection: false`, teclado numérico, longitud fija), botón "Firmar"
deshabilitado hasta completar el código, y el estado resultante. Si el código no coincide,
mensaje de error y el campo se vacía para reintentar. Al terminar con éxito, refrescar el
parte para que `estado` y `control_firma` se actualicen.

> El código TOTP caduca cada **20 segundos** (spec §8.2). Si el usuario tarda, `confirmar`
> fallará: en ese caso volver a pedir `codigoServidor()` y mostrar el nuevo código, no dejar
> al piloto atascado con uno caducado.

- [ ] **Step 7: Ejecutar tests y analizador** → PASS + `dart analyze` limpio

- [ ] **Step 8: Commit**

```bash
git add lib/data/signature_repository.dart lib/feature/firma test/data/signature_repository_test.dart test/feature/firma
git commit -m "feat: firma electronica con OTP tecleado y transiciones de estado del parte"
```

---

## Task 20: Checklist de firma (ayuda visual) y cierre

**Files:**
- Create: `lib/feature/parte/checklist_firma.dart`
- Modify: `lib/feature/parte/parte_shell_view.dart`
- Test: `test/feature/parte/checklist_firma_test.dart`

**Interfaces:**
- Consumes: `Vuelo`.
- Produces: `List<RequisitoFirma> requisitosParaPostvuelo(Vuelo v)` y
  `List<RequisitoFirma> requisitosParaCerrado(Vuelo v)`, donde
  `class RequisitoFirma { final String texto; final bool cumplido; }`.

Traduce a cliente **solo** las condiciones de spec §7.1 y §7.2 que la app puede evaluar con
los datos que ya tiene en memoria (checks, meteo, NOTAM, oilqty, tacómetros, `valid_*cg`,
performance, cuadre de `pasajeros_wb`, tipos de vuelo, presupuesto, combustible). Las que
requieren búsquedas globales (solapamientos, perfiles de formación, descansos, actividad
aérea) **no se evalúan**: se listan como "lo comprueba el servidor al firmar".

**Es ayuda visual, no validación.** El botón Firmar sigue habilitándose por `can_sign` y el
veredicto lo da siempre el servidor. No se añade ninguna condición que el ERP no tenga
(spec §12.1).

- [ ] **Step 1: Escribir el test que falla**

```dart
test('lista los requisitos incumplidos de la cadena de postvuelo', () {
  final r = requisitosParaPostvuelo(vueloCon(
      checklistRealizado: false, briefingRealizado: true, notamRevisado: true,
      meteo: 'METAR...', oilqty: 0, tacomsalida: 3.0, tipo: 'R44',
      distanciatotalprevista: 220, numtripulacion: 1, tiempoprevisto: 2.0,
      validCg: true, tienePerformance: true, pasajerosWb: 3, numpax: 0, numpae: 2,
      tieneTipoVuelo: true));
  expect(r.where((x) => !x.cumplido).map((x) => x.texto),
      contains('Inspección prevuelo realizada'));
});

test('no evalua el solapamiento de tripulacion', () {
  final textos = requisitosParaPostvuelo(vueloCompleto()).map((x) => x.texto);
  expect(textos.any((t) => t.contains('SOLAPAMIENTO')), isFalse);
});

test('la suma de ocupantes debe cuadrar con los pesos del W&B', () {
  final r = requisitosParaPostvuelo(vueloCon(pasajerosWb: 2, numtripulacion: 1, numpax: 0, numpae: 2));
  final req = r.firstWhere((x) => x.texto.contains('Carga y Centrado'));
  expect(req.cumplido, isFalse);
});

test('la cadena de cerrado no comprueba el combustible (bug conocido del ERP)', () {
  final textos = requisitosParaCerrado(vueloCon(fuelllegada: 0)).map((x) => x.texto);
  expect(textos.any((t) => t.contains('combustible llegada')), isFalse);
});
```

- [ ] **Step 2: Ejecutar y verificar que falla** → FAIL

- [ ] **Step 3: Implementar `checklist_firma.dart`**

- [ ] **Step 4: Integrar en el shell** — al pulsar Firmar, si hay requisitos incumplidos se
      muestra primero la lista; el usuario puede continuar igualmente (el servidor decide).

- [ ] **Step 5: Ejecutar toda la batería**

Run: `flutter test`
Run: `dart analyze`
Expected: todo verde.

- [ ] **Step 6: Prueba manual end-to-end contra el entorno de pruebas**

Con un parte real en el entorno de pruebas (no producción):
1. Crear un parte nuevo, seleccionar helicóptero, verificar que se autorrellenan
   `velocidadprevista`, `consumomedio_vuelo`, `editfuelrem`, `tacomsalida` y `lugarsalida`.
2. Rellenar combustible y comprobar que los kg/gal coinciden con los del ERP web abierto en
   paralelo con el mismo parte.
3. Obtener meteo, marcar NOTAM, calcular W&B y Performance.
4. Firmar el prevuelo y confirmar que el `estado` pasa a `postvuelo`.
5. Rellenar el postvuelo y firmar el cierre.
6. Abrir el mismo parte en el ERP web y comparar **campo a campo** los valores persistidos.

- [ ] **Step 7: Commit**

```bash
git add lib/feature/parte/checklist_firma.dart test/feature/parte/checklist_firma_test.dart
git commit -m "feat: checklist de requisitos de firma como ayuda visual"
```

---

## Riesgos y puntos de control

| Riesgo | Mitigación |
|---|---|
| Divergencia entre el motor de combustible local y el del servidor | El valor persistido es siempre el del `onchange`. El motor local solo pinta. Test de equivalencia con los datos reales de spec §14 |
| Envolventes del W&B desactualizadas respecto al ERP | Las envolventes viven en JS del addon. Si cambian allí, hay que replicarlas. Añadir una nota en `wb_envelopes.dart` apuntando a `addons/leulit_operaciones/static/src/js/weight_and_balance.js` |
| `onchange helicoptero_id` borra el Performance del parte | Confirmar con el usuario antes de cambiar el helicóptero en un parte existente (spec §12.3) |
| El usuario no puede firmar por un parte pendiente de otro vuelo | `can_sign` viene del servidor; mostrar por qué no se puede firmar consultando si hay otro parte pendiente del mismo piloto/helicóptero |
| Sesión caducada a mitad de un formulario | `OdooSessionExpired` → re-login transparente y reintento de la última llamada. Nunca perder el estado del formulario |
| Campos `force_save` no enviados en el `write` | `toWriteValues()` los incluye explícitamente y hay test que lo comprueba (Task 6) |

## Fuera de alcance de este plan

- Modo offline y sincronización.
- Creación y gestión de anomalías/anotaciones desde la app.
- Generación local de los PDF firmados: se descargan del servidor.
- Pantalla "Pendientes de firma" consolidada (`allPendienteFirmaOdoo`, spec §8.4).
