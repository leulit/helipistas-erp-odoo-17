// GENERADO AUTOMÁTICAMENTE — no editar a mano.
// Fuente: addons/leulit_operaciones/static/src/js/performance_constants.js
//         (ERP-ODOO, Odoo 17 Helipistas), volcado el 2026-08-18.
// Si las curvas cambian en el addon, hay que regenerar este fichero.
//
// Uso: ver docs/superpowers/specs/2026-08-18-app-parte-vuelo-spec.md §10.

/// Una curva de temperatura del gráfico: los puntos están en píxeles de la
/// imagen de fondo, ordenados por x, y `temp` es la temperatura exacta en ºC.
class PerfCurve {
  const PerfCurve(this.temp, this.pts);

  final double temp;
  final List<List<double>> pts;
}

/// Una de las dos gráficas (IGE u OGE) de un modelo de helicóptero.
class PerfChart {
  const PerfChart({
    required this.asset,
    required this.canvasWidth,
    required this.canvasHeight,
    required this.inicioEje,
    required this.proporcion,
    required this.alturaImagen,
    required this.inicioEjeX,
    required this.inicioEjeY,
    required this.temperaturas,
  });

  /// Ruta del asset dentro de la app (copiar el PNG/JPG del addon).
  final String asset;
  final int canvasWidth;
  final int canvasHeight;

  /// Origen del eje de peso, en libras.
  final double inicioEje;

  /// Píxeles por libra en el eje de peso.
  final double proporcion;

  /// Alto de la imagen usado por el ERP para trasladar el origen.
  /// Ojo: no siempre coincide con `canvasHeight` ni con el alto real del fichero.
  final double alturaImagen;
  final double inicioEjeX;
  final double inicioEjeY;

  final List<PerfCurve> temperaturas;
}

const Map<String, PerfChart> perfCharts = {
  'hil_in': PerfChart(
    asset: 'assets/performance/ec_120_b_in.png',
    canvasWidth: 500,
    canvasHeight: 725,
    inicioEje: 2204.0,
    proporcion: 0.224683,
    alturaImagen: 636.0,
    inicioEjeX: 41.0,
    inicioEjeY: -52.0,
    temperaturas: [
      PerfCurve(-40.0, [[142.0, -485.0], [231.0, -415.0], [358.0, -327.0]]),
      PerfCurve(-30.0, [[118.0, -484.0], [219.0, -405.0], [286.0, -358.0], [357.0, -308.0]]),
      PerfCurve(-20.0, [[88.0, -485.0], [207.0, -390.0], [302.0, -321.0], [357.0, -283.0]]),
      PerfCurve(-10.0, [[51.0, -485.0], [135.0, -413.0], [221.0, -348.0], [296.0, -292.0], [356.0, -250.0]]),
      PerfCurve(0.0, [[11.0, -485.0], [115.0, -395.0], [213.0, -318.0], [294.0, -256.0], [357.0, -211.0]]),
      PerfCurve(10.0, [[1.0, -456.0], [96.0, -372.0], [192.0, -293.0], [279.0, -224.0], [356.0, -170.0]]),
      PerfCurve(20.0, [[28.0, -391.0], [127.0, -303.0], [226.0, -221.0], [299.0, -167.0], [356.0, -125.0]]),
      PerfCurve(30.0, [[113.0, -269.0], [201.0, -194.0], [279.0, -134.0], [356.0, -78.0]]),
      PerfCurve(40.0, [[200.0, -147.0], [267.0, -94.0], [356.0, -29.0]]),
      PerfCurve(50.0, [[293.0, -24.0], [326.0, 1.0]]),
    ],
  ),
  'hil_out': PerfChart(
    asset: 'assets/performance/ec_120_b_out.png',
    canvasWidth: 520,
    canvasHeight: 770,
    inicioEje: 2206.0,
    proporcion: 0.234614,
    alturaImagen: 645.0,
    inicioEjeX: 37.0,
    inicioEjeY: -56.0,
    temperaturas: [
      PerfCurve(-40.0, [[117.0, -481.0], [180.0, -433.0], [264.0, -371.0], [358.0, -307.0], [370.0, -283.0], [414.0, -195.0]]),
      PerfCurve(-30.0, [[93.0, -481.0], [173.0, -418.0], [265.0, -352.0], [353.0, -290.0], [371.0, -257.0], [414.0, -168.0]]),
      PerfCurve(-20.0, [[64.0, -481.0], [168.0, -398.0], [263.0, -329.0], [353.0, -267.0], [371.0, -233.0], [414.0, -142.0]]),
      PerfCurve(-10.0, [[26.0, -481.0], [162.0, -371.0], [263.0, -295.0], [361.0, -228.0], [371.0, -208.0], [414.0, -117.0]]),
      PerfCurve(0.0, [[1.0, -468.0], [68.0, -409.0], [152.0, -343.0], [258.0, -262.0], [370.0, -183.0], [414.0, -93.0]]),
      PerfCurve(10.0, [[1.0, -430.0], [67.0, -374.0], [144.0, -309.0], [252.0, -225.0], [371.0, -141.0], [385.0, -131.0], [414.0, -70.0]]),
      PerfCurve(20.0, [[0.0, -391.0], [63.0, -336.0], [138.0, -271.0], [248.0, -183.0], [370.0, -96.0], [400.0, -76.0], [414.0, -48.0]]),
      PerfCurve(30.0, [[87.0, -268.0], [189.0, -182.0], [298.0, -99.0], [370.0, -49.0], [414.0, -19.0]]),
      PerfCurve(40.0, [[173.0, -146.0], [238.0, -94.0], [315.0, -38.0], [370.0, 1.0]]),
      PerfCurve(50.0, [[264.0, -24.0], [298.0, 1.0]]),
    ],
  ),
  'ec_in': PerfChart(
    asset: 'assets/performance/ec_120_b_in.png',
    canvasWidth: 500,
    canvasHeight: 725,
    inicioEje: 2204.0,
    proporcion: 0.224683,
    alturaImagen: 636.0,
    inicioEjeX: 41.0,
    inicioEjeY: -52.0,
    temperaturas: [
      PerfCurve(-40.0, [[142.0, -485.0], [231.0, -415.0], [358.0, -327.0]]),
      PerfCurve(-30.0, [[118.0, -484.0], [219.0, -405.0], [286.0, -358.0], [357.0, -308.0]]),
      PerfCurve(-20.0, [[88.0, -485.0], [207.0, -390.0], [302.0, -321.0], [357.0, -283.0]]),
      PerfCurve(-10.0, [[51.0, -485.0], [135.0, -413.0], [221.0, -348.0], [296.0, -292.0], [356.0, -250.0]]),
      PerfCurve(0.0, [[11.0, -485.0], [115.0, -395.0], [213.0, -318.0], [294.0, -256.0], [357.0, -211.0]]),
      PerfCurve(10.0, [[1.0, -456.0], [96.0, -372.0], [192.0, -293.0], [279.0, -224.0], [356.0, -170.0]]),
      PerfCurve(20.0, [[28.0, -391.0], [127.0, -303.0], [226.0, -221.0], [299.0, -167.0], [356.0, -125.0]]),
      PerfCurve(30.0, [[113.0, -269.0], [201.0, -194.0], [279.0, -134.0], [356.0, -78.0]]),
      PerfCurve(40.0, [[200.0, -147.0], [267.0, -94.0], [356.0, -29.0]]),
      PerfCurve(50.0, [[293.0, -24.0], [326.0, 1.0]]),
    ],
  ),
  'ec_out': PerfChart(
    asset: 'assets/performance/ec_120_b_out.png',
    canvasWidth: 520,
    canvasHeight: 770,
    inicioEje: 2206.0,
    proporcion: 0.234614,
    alturaImagen: 645.0,
    inicioEjeX: 37.0,
    inicioEjeY: -56.0,
    temperaturas: [
      PerfCurve(-40.0, [[117.0, -481.0], [180.0, -433.0], [264.0, -371.0], [358.0, -307.0], [370.0, -283.0]]),
      PerfCurve(-30.0, [[93.0, -481.0], [173.0, -418.0], [265.0, -352.0], [353.0, -290.0], [371.0, -257.0]]),
      PerfCurve(-20.0, [[64.0, -481.0], [168.0, -398.0], [263.0, -329.0], [353.0, -267.0], [371.0, -233.0]]),
      PerfCurve(-10.0, [[26.0, -481.0], [162.0, -371.0], [263.0, -295.0], [361.0, -228.0], [371.0, -208.0]]),
      PerfCurve(0.0, [[1.0, -468.0], [68.0, -409.0], [152.0, -343.0], [258.0, -262.0], [370.0, -183.0]]),
      PerfCurve(10.0, [[1.0, -430.0], [67.0, -374.0], [144.0, -309.0], [252.0, -225.0], [371.0, -141.0]]),
      PerfCurve(20.0, [[0.0, -391.0], [63.0, -336.0], [138.0, -271.0], [248.0, -183.0], [370.0, -96.0]]),
      PerfCurve(30.0, [[87.0, -268.0], [189.0, -182.0], [298.0, -99.0], [370.0, -49.0]]),
      PerfCurve(40.0, [[173.0, -146.0], [238.0, -94.0], [315.0, -38.0], [370.0, 1.0]]),
      PerfCurve(50.0, [[264.0, -24.0], [298.0, 1.0]]),
    ],
  ),
  'r22_in': PerfChart(
    asset: 'assets/performance/r22_beta_in.png',
    canvasWidth: 500,
    canvasHeight: 725,
    inicioEje: 909.0,
    proporcion: 0.839722,
    alturaImagen: 720.0,
    inicioEjeX: 55.0,
    inicioEjeY: -185.0,
    temperaturas: [
      PerfCurve(-20.0, [[121.0, -468.0], [199.0, -396.0], [288.0, -318.0], [339.0, -275.0], [386.0, -236.0]]),
      PerfCurve(-10.0, [[146.0, -425.0], [215.0, -361.0], [285.0, -301.0], [342.0, -254.0], [387.0, -219.0]]),
      PerfCurve(0.0, [[169.0, -383.0], [233.0, -328.0], [298.0, -273.0], [386.0, -201.0]]),
      PerfCurve(10.0, [[188.0, -350.0], [235.0, -309.0], [294.0, -259.0], [339.0, -220.0], [386.0, -183.0]]),
      PerfCurve(20.0, [[209.0, -313.0], [254.0, -274.0], [305.0, -231.0], [344.0, -199.0], [386.0, -165.0]]),
      PerfCurve(30.0, [[228.0, -278.0], [256.0, -255.0], [295.0, -222.0], [343.0, -182.0], [386.0, -148.0]]),
      PerfCurve(40.0, [[246.0, -245.0], [258.0, -234.0], [297.0, -203.0], [342.0, -166.0], [386.0, -133.0]]),
    ],
  ),
  'r22_out': PerfChart(
    asset: 'assets/performance/r22_beta_out.png',
    canvasWidth: 520,
    canvasHeight: 770,
    inicioEje: 899.0,
    proporcion: 0.847732,
    alturaImagen: 770.0,
    inicioEjeX: 64.0,
    inicioEjeY: -134.0,
    temperaturas: [
      PerfCurve(-20.0, [[69.0, -568.0], [162.0, -485.0], [253.0, -405.0], [345.0, -324.0], [404.0, -273.0]]),
      PerfCurve(-10.0, [[91.0, -529.0], [170.0, -458.0], [251.0, -385.0], [341.0, -305.0], [404.0, -250.0]]),
      PerfCurve(0.0, [[109.0, -495.0], [181.0, -426.0], [252.0, -362.0], [340.0, -281.0], [404.0, -223.0]]),
      PerfCurve(10.0, [[132.0, -452.0], [194.0, -394.0], [250.0, -341.0], [342.0, -255.0], [404.0, -198.0]]),
      PerfCurve(20.0, [[151.0, -418.0], [211.0, -359.0], [248.0, -324.0], [338.0, -236.0], [398.0, -180.0], [404.0, -166.0]]),
      PerfCurve(30.0, [[173.0, -378.0], [248.0, -303.0], [339.0, -214.0], [397.0, -158.0], [404.0, -134.0]]),
      PerfCurve(40.0, [[192.0, -344.0], [252.0, -282.0], [341.0, -191.0], [395.0, -137.0], [404.0, -88.0]]),
    ],
  ),
  'r22_2_in': PerfChart(
    asset: 'assets/performance/r22_beta_2_in.png',
    canvasWidth: 500,
    canvasHeight: 717,
    inicioEje: 1100.0,
    proporcion: 1.118691,
    alturaImagen: 717.0,
    inicioEjeX: 71.0,
    inicioEjeY: -156.0,
    temperaturas: [
      PerfCurve(-20.0, [[100.0, -493.0], [210.0, -390.0], [306.0, -307.0]]),
      PerfCurve(-10.0, [[126.0, -435.0], [216.0, -352.0], [306.0, -274.0]]),
      PerfCurve(0.0, [[148.0, -385.0], [229.0, -310.0], [306.0, -242.0]]),
      PerfCurve(10.0, [[169.0, -338.0], [235.0, -276.0], [306.0, -213.0]]),
      PerfCurve(20.0, [[195.0, -281.0], [305.0, -179.0]]),
      PerfCurve(30.0, [[216.0, -233.0], [306.0, -153.0]]),
      PerfCurve(40.0, [[239.0, -183.0], [305.0, -123.0]]),
    ],
  ),
  'r22_2_out': PerfChart(
    asset: 'assets/performance/r22_beta_2_out.png',
    canvasWidth: 500,
    canvasHeight: 790,
    inicioEje: 1000.0,
    proporcion: 0.885823,
    alturaImagen: 790.0,
    inicioEjeX: 62.0,
    inicioEjeY: -141.0,
    temperaturas: [
      PerfCurve(-20.0, [[63.0, -579.0], [150.0, -495.0], [231.0, -418.0], [278.0, -375.0], [322.0, -341.0], [330.0, -319.0]]),
      PerfCurve(-10.0, [[82.0, -535.0], [151.0, -471.0], [229.0, -398.0], [283.0, -349.0], [316.0, -322.0], [330.0, -275.0]]),
      PerfCurve(0.0, [[101.0, -497.0], [162.0, -437.0], [229.0, -374.0], [268.0, -339.0], [309.0, -305.0], [329.0, -237.0]]),
      PerfCurve(10.0, [[120.0, -455.0], [186.0, -394.0], [246.0, -338.0], [304.0, -287.0], [330.0, -198.0]]),
      PerfCurve(20.0, [[138.0, -416.0], [211.0, -349.0], [250.0, -314.0], [299.0, -268.0], [329.0, -161.0]]),
      PerfCurve(30.0, [[152.0, -383.0], [202.0, -338.0], [247.0, -296.0], [294.0, -250.0], [307.0, -205.0], [329.0, -126.0]]),
      PerfCurve(40.0, [[170.0, -346.0], [210.0, -308.0], [250.0, -271.0], [290.0, -232.0], [306.0, -175.0], [329.0, -94.0]]),
    ],
  ),
  'r44_in': PerfChart(
    asset: 'assets/performance/R44_IGE_HOVER_CEILING_VS_GROSS_WEIGHT.png',
    canvasWidth: 620,
    canvasHeight: 900,
    inicioEje: 1500.0,
    proporcion: 0.485026,
    alturaImagen: 900.0,
    inicioEjeX: 86.0,
    inicioEjeY: -134.0,
    temperaturas: [
      PerfCurve(-20.0, [[213.0, -617.0], [341.0, -475.0], [440.0, -371.0]]),
      PerfCurve(-10.0, [[227.0, -569.0], [355.0, -429.0], [439.0, -339.0]]),
      PerfCurve(0.0, [[240.0, -526.0], [350.0, -406.0], [440.0, -310.0]]),
      PerfCurve(10.0, [[253.0, -480.0], [348.0, -375.0], [440.0, -279.0]]),
      PerfCurve(20.0, [[263.0, -439.0], [352.0, -339.0], [441.0, -245.0]]),
      PerfCurve(30.0, [[265.0, -391.0], [354.0, -289.0], [440.0, -198.0]]),
      PerfCurve(40.0, [[255.0, -351.0], [350.0, -245.0], [440.0, -156.0]]),
    ],
  ),
  'r44_out': PerfChart(
    asset: 'assets/performance/R44_OGE_HOVER_CEILING_VS_GROSS_WEIGHT.png',
    canvasWidth: 620,
    canvasHeight: 900,
    inicioEje: 1494.0,
    proporcion: 0.482723,
    alturaImagen: 900.0,
    inicioEjeX: 81.0,
    inicioEjeY: -134.0,
    temperaturas: [
      PerfCurve(-20.0, [[99.0, -623.0], [166.0, -538.0], [282.0, -400.0], [357.0, -316.0], [441.0, -228.0]]),
      PerfCurve(-10.0, [[112.0, -570.0], [199.0, -465.0], [294.0, -354.0], [367.0, -272.0], [441.0, -196.0]]),
      PerfCurve(0.0, [[122.0, -531.0], [212.0, -420.0], [302.0, -316.0], [373.0, -236.0], [442.0, -167.0]]),
      PerfCurve(10.0, [[134.0, -477.0], [223.0, -372.0], [304.0, -279.0], [375.0, -200.0], [431.0, -146.0], [440.0, -104.0]]),
      PerfCurve(20.0, [[140.0, -438.0], [233.0, -325.0], [304.0, -244.0], [380.0, -159.0], [414.0, -125.0], [440.0, -24.0]]),
      PerfCurve(30.0, [[145.0, -392.0], [245.0, -268.0], [312.0, -192.0], [395.0, -100.0], [423.0, 0.0]]),
      PerfCurve(40.0, [[140.0, -349.0], [212.0, -261.0], [310.0, -147.0], [365.0, -86.0], [392.0, 1.0]]),
    ],
  ),
  'r44_2_in': PerfChart(
    asset: 'assets/performance/R44_2_IGE_HOVER_CEILING_VS_GROSS_WEIGHT.jpg',
    canvasWidth: 500,
    canvasHeight: 725,
    inicioEje: 2000.0,
    proporcion: 0.535893,
    alturaImagen: 620.0,
    inicioEjeX: 53.0,
    inicioEjeY: -93.0,
    temperaturas: [
      PerfCurve(-30.0, [[98.0, -478.0], [271.0, -299.0]]),
      PerfCurve(-20.0, [[116.0, -426.0], [271.0, -264.0]]),
      PerfCurve(-10.0, [[131.0, -379.0], [271.0, -228.0]]),
      PerfCurve(0.0, [[148.0, -327.0], [271.0, -195.0]]),
      PerfCurve(10.0, [[164.0, -277.0], [271.0, -163.0]]),
      PerfCurve(20.0, [[179.0, -229.0], [271.0, -131.0]]),
      PerfCurve(30.0, [[195.0, -181.0], [271.0, -101.0]]),
      PerfCurve(40.0, [[210.0, -134.0], [271.0, -69.0]]),
    ],
  ),
  'r44_2_out': PerfChart(
    asset: 'assets/performance/R44_2_OGE_HOVER_CEILING_VD_GROSS_WEIGHT.jpg',
    canvasWidth: 520,
    canvasHeight: 770,
    inicioEje: 1700.0,
    proporcion: 0.403427,
    alturaImagen: 745.0,
    inicioEjeX: 46.0,
    inicioEjeY: -143.0,
    temperaturas: [
      PerfCurve(-30.0, [[86.0, -558.0], [162.0, -468.0], [248.0, -371.0], [324.0, -288.0]]),
      PerfCurve(-20.0, [[97.0, -519.0], [176.0, -426.0], [248.0, -344.0], [324.0, -263.0]]),
      PerfCurve(-10.0, [[107.0, -483.0], [193.0, -381.0], [250.0, -314.0], [324.0, -237.0]]),
      PerfCurve(0.0, [[118.0, -445.0], [193.0, -356.0], [262.0, -275.0], [318.0, -215.0], [324.0, -194.0]]),
      PerfCurve(10.0, [[130.0, -406.0], [198.0, -325.0], [260.0, -253.0], [311.0, -199.0], [324.0, -151.0]]),
      PerfCurve(20.0, [[141.0, -368.0], [204.0, -295.0], [267.0, -221.0], [305.0, -178.0], [324.0, -107.0]]),
      PerfCurve(30.0, [[152.0, -331.0], [208.0, -266.0], [267.0, -196.0], [298.0, -159.0], [324.0, -69.0]]),
      PerfCurve(40.0, [[162.0, -296.0], [209.0, -240.0], [267.0, -173.0], [292.0, -146.0], [323.0, -33.0]]),
    ],
  ),
  'cabri_in': PerfChart(
    asset: 'assets/performance/cabri_g2_in.png',
    canvasWidth: 500,
    canvasHeight: 725,
    inicioEje: 1033.0,
    proporcion: 0.794933,
    alturaImagen: 515.0,
    inicioEjeX: 49.0,
    inicioEjeY: -69.0,
    temperaturas: [
      PerfCurve(-20.0, [[70.0, -402.0], [132.0, -359.0], [201.0, -312.0], [254.0, -279.0], [298.0, -252.0], [348.0, -222.0], [379.0, -204.0], [406.0, -189.0]]),
      PerfCurve(-10.0, [[47.0, -402.0], [96.0, -367.0], [190.0, -303.0], [248.0, -265.0], [322.0, -219.0], [377.0, -188.0], [406.0, -171.0]]),
      PerfCurve(0.0, [[26.0, -402.0], [72.0, -368.0], [120.0, -334.0], [183.0, -292.0], [242.0, -253.0], [316.0, -206.0], [372.0, -173.0], [406.0, -154.0]]),
      PerfCurve(10.0, [[5.0, -402.0], [45.0, -372.0], [90.0, -340.0], [149.0, -298.0], [206.0, -259.0], [283.0, -211.0], [356.0, -166.0], [406.0, -137.0]]),
      PerfCurve(20.0, [[0.0, -391.0], [37.0, -364.0], [87.0, -325.0], [143.0, -287.0], [206.0, -245.0], [281.0, -196.0], [353.0, -152.0], [406.0, -121.0]]),
      PerfCurve(30.0, [[-1.0, -377.0], [37.0, -348.0], [81.0, -316.0], [139.0, -275.0], [193.0, -237.0], [254.0, -196.0], [320.0, -156.0], [406.0, -105.0]]),
    ],
  ),
  'cabri_out': PerfChart(
    asset: 'assets/performance/cabri_g2_out.png',
    canvasWidth: 520,
    canvasHeight: 770,
    inicioEje: 1033.0,
    proporcion: 0.794933,
    alturaImagen: 515.0,
    inicioEjeX: 49.0,
    inicioEjeY: -65.0,
    temperaturas: [
      PerfCurve(-20.0, [[27.0, -401.0], [69.0, -369.0], [118.0, -334.0], [168.0, -300.0], [231.0, -259.0], [315.0, -206.0], [377.0, -169.0], [406.0, -88.0]]),
      PerfCurve(-10.0, [[5.0, -401.0], [51.0, -366.0], [100.0, -330.0], [148.0, -297.0], [215.0, -252.0], [297.0, -201.0], [348.0, -170.0], [371.0, -155.0], [391.0, -101.0], [406.0, -56.0]]),
      PerfCurve(0.0, [[0.0, -389.0], [34.0, -362.0], [80.0, -329.0], [130.0, -293.0], [194.0, -249.0], [273.0, -197.0], [326.0, -165.0], [365.0, -142.0], [384.0, -89.0], [406.0, -24.0]]),
      PerfCurve(10.0, [[0.0, -373.0], [52.0, -333.0], [114.0, -288.0], [177.0, -245.0], [257.0, -192.0], [318.0, -154.0], [359.0, -128.0], [377.0, -77.0], [404.0, 1.0]]),
      PerfCurve(20.0, [[-1.0, -358.0], [63.0, -310.0], [144.0, -252.0], [247.0, -182.0], [314.0, -140.0], [354.0, -115.0], [371.0, -66.0], [384.0, -28.0], [395.0, 1.0]]),
      PerfCurve(30.0, [[0.0, -343.0], [54.0, -301.0], [141.0, -238.0], [245.0, -168.0], [316.0, -122.0], [348.0, -103.0], [364.0, -56.0], [384.0, 0.0]]),
    ],
  ),
};

/// Modelo de helicóptero (`leulit.vuelo.helicoptero_modelo`) → par de gráficas.
/// La clave `EC-HIL con gancho` se usa cuando la matrícula es EC-HIL y el W&B
/// tiene `gancho_carga_cb` marcado (ver spec §10).
const Map<String, ({String ige, String oge})> perfChartPorModelo = {
  'EC120B':          (ige: 'ec_in',     oge: 'ec_out'),
  'EC-HIL con gancho': (ige: 'hil_in',  oge: 'hil_out'),
  'R22 Beta':        (ige: 'r22_in',    oge: 'r22_out'),
  'R22 Beta II':     (ige: 'r22_2_in',  oge: 'r22_2_out'),
  'R44 Astro':       (ige: 'r44_in',    oge: 'r44_out'),
  'R44 Raven I':     (ige: 'r44_in',    oge: 'r44_out'),
  'R44 Clipper I':   (ige: 'r44_in',    oge: 'r44_out'),
  'R44 Raven II':    (ige: 'r44_2_in',  oge: 'r44_2_out'),
  'R44 Clipper II':  (ige: 'r44_2_in',  oge: 'r44_2_out'),
  'CABRI G2':        (ige: 'cabri_in',  oge: 'cabri_out'),
};
