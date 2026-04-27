/** @odoo-module **/
/********************  R22 IN (IGE)  ********************/
export const canvas_r22_in = "micanvas_r22_in";
export const src_r22_in = "/leulit_operaciones/static/src/img/r22_beta_in.png";

// Eje de peso
export const inicio_eje_r22_in = 909;
export const proporcion_r22_in = 0.839722;
// Uso: calc_peso(peso, inicio_eje_r22, proporcion_r22_in, false)

// Coordenadas de imagen (pixels)
export const altura_imagen_r22_in = 720;
export const inicio_eje_x_r22_in = 55;
export const inicio_eje_y_r22_in = -185;  // = 535 - 720

// Curvas de temperatura (7 curvas)
// Formato: cada fila = [...puntos [x,y] ordenados por x..., temperatura_exacta]
export const temperaturas_r22_in = new Array(
    new Array(new Array(121,-468),new Array(199,-396),new Array(288,-318),new Array(339,-275),new Array(386,-236),-20),
    new Array(new Array(146,-425),new Array(215,-361),new Array(285,-301),new Array(342,-254),new Array(387,-219),-10),
    new Array(new Array(169,-383),new Array(233,-328),new Array(298,-273),new Array(386,-201),0),
    new Array(new Array(188,-350),new Array(235,-309),new Array(294,-259),new Array(339,-220),new Array(386,-183),10),
    new Array(new Array(209,-313),new Array(254,-274),new Array(305,-231),new Array(344,-199),new Array(386,-165),20),
    new Array(new Array(228,-278),new Array(256,-255),new Array(295,-222),new Array(343,-182),new Array(386,-148),30),
    new Array(new Array(246,-245),new Array(258,-234),new Array(297,-203),new Array(342,-166),new Array(386,-133),40)
);

/********************  R22 OUT (OGE)  ********************/
export const canvas_r22_out = "micanvas_r22_out";
export const src_r22_out = "/leulit_operaciones/static/src/img/r22_beta_out.png";

// Eje de peso
export const inicio_eje_r22_out = 899;
export const proporcion_r22_out = 0.847732;
// Uso: calc_peso(peso, inicio_eje_r22, proporcion_r22_out, false)

// Coordenadas de imagen (pixels)
export const altura_imagen_r22_out = 770;
export const inicio_eje_x_r22_out = 64;
export const inicio_eje_y_r22_out = -134;  // = 636 - 770

// Curvas de temperatura (7 curvas)
// Formato: cada fila = [...puntos [x,y] ordenados por x..., temperatura_exacta]
export const temperaturas_r22_out = new Array(
    new Array(new Array(69,-568),new Array(162,-485),new Array(253,-405),new Array(345,-324),new Array(404,-273),-20),
    new Array(new Array(91,-529),new Array(170,-458),new Array(251,-385),new Array(341,-305),new Array(404,-250),-10),
    new Array(new Array(109,-495),new Array(181,-426),new Array(252,-362),new Array(340,-281),new Array(404,-223),0),
    new Array(new Array(132,-452),new Array(194,-394),new Array(250,-341),new Array(342,-255),new Array(404,-198),10),
    new Array(new Array(151,-418),new Array(211,-359),new Array(248,-324),new Array(338,-236),new Array(398,-180),new Array(404,-166),20),
    new Array(new Array(173,-378),new Array(248,-303),new Array(339,-214),new Array(397,-158),new Array(404,-134),30),
    new Array(new Array(192,-344),new Array(252,-282),new Array(341,-191),new Array(395,-137),new Array(404,-88),40)
);

/********************  R22_2 IN (IGE)  ********************/
export const canvas_r22_2_in = "micanvas_r22_2_in";
export const src_r22_2_in = "/leulit_operaciones/static/src/img/r22_beta_2_in.png";

// Eje de peso
export const inicio_eje_r22_2_in = 1100;
export const proporcion_r22_2_in = 1.118691;
// Uso: calc_peso(peso, inicio_eje_r22_2, proporcion_r22_2_in, false)

// Coordenadas de imagen (pixels)
export const altura_imagen_r22_2_in = 717;
export const inicio_eje_x_r22_2_in = 71;
export const inicio_eje_y_r22_2_in = -156;  // = 561 - 717

// Curvas de temperatura (7 curvas)
// Formato: cada fila = [...puntos [x,y] ordenados por x..., temperatura_exacta]
export const temperaturas_r22_2_in = new Array(
    new Array(new Array(100,-493),new Array(210,-390),new Array(306,-307),-20),
    new Array(new Array(126,-435),new Array(216,-352),new Array(306,-274),-10),
    new Array(new Array(148,-385),new Array(229,-310),new Array(306,-242),0),
    new Array(new Array(169,-338),new Array(235,-276),new Array(306,-213),10),
    new Array(new Array(195,-281),new Array(305,-179),20),
    new Array(new Array(216,-233),new Array(306,-153),30),
    new Array(new Array(239,-183),new Array(305,-123),40)
);
/********************  R22_2 OUT (OGE)  ********************/
export const canvas_r22_2_out = "micanvas_r22_2_out";
export const src_r22_2_out = "/leulit_operaciones/static/src/img/r22_beta_2_out.png";

// Eje de peso
export const inicio_eje_r22_2_out = 1000;
export const proporcion_r22_2_out = 0.885823;
// Uso: calc_peso(peso, inicio_eje_r22_2, proporcion_r22_2_out, false)

// Coordenadas de imagen (pixels)
export const altura_imagen_r22_2_out = 790;
export const inicio_eje_x_r22_2_out = 62;
export const inicio_eje_y_r22_2_out = -141;  // = 649 - 790

// Curvas de temperatura (7 curvas)
// Formato: cada fila = [...puntos [x,y] ordenados por x..., temperatura_exacta]
export const temperaturas_r22_2_out = new Array(
    new Array(new Array(63,-579),new Array(150,-495),new Array(231,-418),new Array(278,-375),new Array(322,-341),new Array(330,-319),-20),
    new Array(new Array(82,-535),new Array(151,-471),new Array(229,-398),new Array(283,-349),new Array(316,-322),new Array(330,-275),-10),
    new Array(new Array(101,-497),new Array(162,-437),new Array(229,-374),new Array(268,-339),new Array(309,-305),new Array(329,-237),0),
    new Array(new Array(120,-455),new Array(186,-394),new Array(246,-338),new Array(304,-287),new Array(330,-198),10),
    new Array(new Array(138,-416),new Array(211,-349),new Array(250,-314),new Array(299,-268),new Array(329,-161),20),
    new Array(new Array(152,-383),new Array(202,-338),new Array(247,-296),new Array(294,-250),new Array(307,-205),new Array(329,-126),30),
    new Array(new Array(170,-346),new Array(210,-308),new Array(250,-271),new Array(290,-232),new Array(306,-175),new Array(329,-94),40)
);

/********************  CABRI IN (IGE)  ********************/
export const canvas_cabri_in = "micanvas_cabri_in";
export const src_cabri_in = "/leulit_operaciones/static/src/img/cabri_g2_in.png";

// Eje de peso
export const inicio_eje_cabri = 1033;
export const proporcion_cabri_in = 0.794933;
// Uso: calc_peso(peso, inicio_eje_cabri, proporcion_cabri_in, false, false)

// Coordenadas de imagen (pixels)
export const altura_imagen_cabri_in = 515;
export const inicio_eje_x_cabri_in = 49;
export const inicio_eje_y_cabri_in = -69;  // = 446 - 515

// Curvas de temperatura (6 curvas)
// Formato: cada fila = [...puntos [x,y] ordenados por x..., temperatura_exacta]
export const temperaturas_cabri_in = new Array(
    new Array(new Array(70,-402),new Array(132,-359),new Array(201,-312),new Array(254,-279),new Array(298,-252),new Array(348,-222),new Array(379,-204),new Array(406,-189),-20),
    new Array(new Array(47,-402),new Array(96,-367),new Array(190,-303),new Array(248,-265),new Array(322,-219),new Array(377,-188),new Array(406,-171),-10),
    new Array(new Array(26,-402),new Array(72,-368),new Array(120,-334),new Array(183,-292),new Array(242,-253),new Array(316,-206),new Array(372,-173),new Array(406,-154),0),
    new Array(new Array(5,-402),new Array(45,-372),new Array(90,-340),new Array(149,-298),new Array(206,-259),new Array(283,-211),new Array(356,-166),new Array(406,-137),10),
    new Array(new Array(0,-391),new Array(37,-364),new Array(87,-325),new Array(143,-287),new Array(206,-245),new Array(281,-196),new Array(353,-152),new Array(406,-121),20),
    new Array(new Array(-1,-377),new Array(37,-348),new Array(81,-316),new Array(139,-275),new Array(193,-237),new Array(254,-196),new Array(320,-156),new Array(406,-105),30)
);
/********************  CABRI OUT (OGE)  ********************/
export const canvas_cabri_out = "micanvas_cabri_out";
export const src_cabri_out = "/leulit_operaciones/static/src/img/cabri_g2_out.png";

// Eje de peso (inicio_eje_cabri definido en la sección IN, mismo valor: 1033)
export const proporcion_cabri_out = 0.794933;
// Uso: calc_peso(peso, inicio_eje_cabri, proporcion_cabri_out, false, false)

// Coordenadas de imagen (pixels)
export const altura_imagen_cabri_out = 515;
export const inicio_eje_x_cabri_out = 49;
export const inicio_eje_y_cabri_out = -65;  // = 450 - 515

// Curvas de temperatura (6 curvas)
// Formato: cada fila = [...puntos [x,y] ordenados por x..., temperatura_exacta]
export const temperaturas_cabri_out = new Array(
    new Array(new Array(27,-401),new Array(69,-369),new Array(118,-334),new Array(168,-300),new Array(231,-259),new Array(315,-206),new Array(377,-169),new Array(406,-88),-20),
    new Array(new Array(5,-401),new Array(51,-366),new Array(100,-330),new Array(148,-297),new Array(215,-252),new Array(297,-201),new Array(348,-170),new Array(371,-155),new Array(391,-101),new Array(406,-56),-10),
    new Array(new Array(0,-389),new Array(34,-362),new Array(80,-329),new Array(130,-293),new Array(194,-249),new Array(273,-197),new Array(326,-165),new Array(365,-142),new Array(384,-89),new Array(406,-24),0),
    new Array(new Array(0,-373),new Array(52,-333),new Array(114,-288),new Array(177,-245),new Array(257,-192),new Array(318,-154),new Array(359,-128),new Array(377,-77),new Array(404,1),10),
    new Array(new Array(-1,-358),new Array(63,-310),new Array(144,-252),new Array(247,-182),new Array(314,-140),new Array(354,-115),new Array(371,-66),new Array(384,-28),new Array(395,1),20),
    new Array(new Array(0,-343),new Array(54,-301),new Array(141,-238),new Array(245,-168),new Array(316,-122),new Array(348,-103),new Array(364,-56),new Array(384,0),30)
);
/********************  EC120 IN (IGE)  ********************/
export const canvas_ec_in = "micanvas_ec_in";
export const src_ec_in = "/leulit_operaciones/static/src/img/ec_120_b_in.png";

// Eje de peso
export const inicio_eje_ec_in = 2204;
export const proporcion_ec_in = 0.224683;
// Uso: calc_peso(peso, inicio_eje_ec_in, proporcion_ec_in, false)

// Coordenadas de imagen (pixels)
export const altura_imagen_ec_in = 636;
export const inicio_eje_x_ec_in = 41;
export const inicio_eje_y_ec_in = -52;  // = 584 - 636

// Curvas de temperatura (10 curvas)
// Formato: cada fila = [...puntos [x,y] ordenados por x..., temperatura_exacta]
export const temperaturas_ec_in = new Array(
    new Array(new Array(142,-485),new Array(231,-415),new Array(358,-327),-40),
    new Array(new Array(118,-484),new Array(219,-405),new Array(286,-358),new Array(357,-308),-30),
    new Array(new Array(88,-485),new Array(207,-390),new Array(302,-321),new Array(357,-283),-20),
    new Array(new Array(51,-485),new Array(135,-413),new Array(221,-348),new Array(296,-292),new Array(356,-250),-10),
    new Array(new Array(11,-485),new Array(115,-395),new Array(213,-318),new Array(294,-256),new Array(357,-211),0),
    new Array(new Array(1,-456),new Array(96,-372),new Array(192,-293),new Array(279,-224),new Array(356,-170),10),
    new Array(new Array(28,-391),new Array(127,-303),new Array(226,-221),new Array(299,-167),new Array(356,-125),20),
    new Array(new Array(113,-269),new Array(201,-194),new Array(279,-134),new Array(356,-78),30),
    new Array(new Array(200,-147),new Array(267,-94),new Array(356,-29),40),
    new Array(new Array(293,-24),new Array(326,1),50)
);
/********************  EC120 OUT (OGE)  ********************/
export const canvas_ec_out = "micanvas_ec_out";
export const src_ec_out = "/leulit_operaciones/static/src/img/ec_120_b_out.png";

// Eje de peso
export const inicio_eje_ec_out = 2206;
export const proporcion_ec_out = 0.234614;
// Uso: calc_peso(peso, inicio_eje_ec, proporcion_ec_out, false)

// Coordenadas de imagen (pixels)
export const altura_imagen_ec_out = 645;
export const inicio_eje_x_ec_out = 37;
export const inicio_eje_y_ec_out = -56;  // = 589 - 645

// Curvas de temperatura (10 curvas)
// Formato: cada fila = [...puntos [x,y] ordenados por x..., temperatura_exacta]
export const temperaturas_ec_out = new Array(
    new Array(new Array(117,-481),new Array(180,-433),new Array(264,-371),new Array(358,-307),new Array(370,-283),-40),
    new Array(new Array(93,-481),new Array(173,-418),new Array(265,-352),new Array(353,-290),new Array(371,-257),-30),
    new Array(new Array(64,-481),new Array(168,-398),new Array(263,-329),new Array(353,-267),new Array(371,-233),-20),
    new Array(new Array(26,-481),new Array(162,-371),new Array(263,-295),new Array(361,-228),new Array(371,-208),-10),
    new Array(new Array(1,-468),new Array(68,-409),new Array(152,-343),new Array(258,-262),new Array(370,-183),0),
    new Array(new Array(1,-430),new Array(67,-374),new Array(144,-309),new Array(252,-225),new Array(371,-141),10),
    new Array(new Array(0,-391),new Array(63,-336),new Array(138,-271),new Array(248,-183),new Array(370,-96),20),
    new Array(new Array(87,-268),new Array(189,-182),new Array(298,-99),new Array(370,-49),30),
    new Array(new Array(173,-146),new Array(238,-94),new Array(315,-38),new Array(370,1),40),
    new Array(new Array(264,-24),new Array(298,1),50)
);

/********************  EC-HIL HOOK IN  ********************/
export const canvas_hil_in = "micanvas_hil_in";
export const src_hil_in = "/leulit_operaciones/static/src/img/ec_120_b_in.png";

// Eje de peso
export const inicio_eje_hil_in = 2204;
export const proporcion_hil_in = 0.224683;
// Uso: calc_peso(peso, inicio_eje_hil_in, proporcion_hil_in, false)

// Coordenadas de imagen (pixels)
export const altura_imagen_hil_in = 636;
export const inicio_eje_x_hil_in = 41;
export const inicio_eje_y_hil_in = -52;  // = 584 - 636

// Curvas de temperatura (10 curvas)
// Formato: cada fila = [...puntos [x,y] ordenados por x..., temperatura_exacta]
export const temperaturas_hil_in = new Array(
    new Array(new Array(142,-485),new Array(231,-415),new Array(358,-327),-40),
    new Array(new Array(118,-484),new Array(219,-405),new Array(286,-358),new Array(357,-308),-30),
    new Array(new Array(88,-485),new Array(207,-390),new Array(302,-321),new Array(357,-283),-20),
    new Array(new Array(51,-485),new Array(135,-413),new Array(221,-348),new Array(296,-292),new Array(356,-250),-10),
    new Array(new Array(11,-485),new Array(115,-395),new Array(213,-318),new Array(294,-256),new Array(357,-211),0),
    new Array(new Array(1,-456),new Array(96,-372),new Array(192,-293),new Array(279,-224),new Array(356,-170),10),
    new Array(new Array(28,-391),new Array(127,-303),new Array(226,-221),new Array(299,-167),new Array(356,-125),20),
    new Array(new Array(113,-269),new Array(201,-194),new Array(279,-134),new Array(356,-78),30),
    new Array(new Array(200,-147),new Array(267,-94),new Array(356,-29),40),
    new Array(new Array(293,-24),new Array(326,1),50)
);
/********************  EC-HIL HOOK OUT  ********************/
export const canvas_hil_out = "micanvas_hil_out";
export const src_hil_out = "/leulit_operaciones/static/src/img/ec_120_b_out.png";

// Eje de peso
export const inicio_eje_hil_out = 2206;
export const proporcion_hil_out = 0.234614;
// Uso: calc_peso(peso, inicio_eje_hil, proporcion_hil_out, false)

// Coordenadas de imagen (pixels)
export const altura_imagen_hil_out = 645;
export const inicio_eje_x_hil_out = 37;
export const inicio_eje_y_hil_out = -56;  // = 589 - 645

// Curvas de temperatura (10 curvas)
// Formato: cada fila = [...puntos [x,y] ordenados por x..., temperatura_exacta]
export const temperaturas_hil_out = new Array(
    new Array(new Array(117,-481),new Array(180,-433),new Array(264,-371),new Array(358,-307),new Array(370,-283),new Array(414,-195),-40),
    new Array(new Array(93,-481),new Array(173,-418),new Array(265,-352),new Array(353,-290),new Array(371,-257),new Array(414,-168),-30),
    new Array(new Array(64,-481),new Array(168,-398),new Array(263,-329),new Array(353,-267),new Array(371,-233),new Array(414,-142),-20),
    new Array(new Array(26,-481),new Array(162,-371),new Array(263,-295),new Array(361,-228),new Array(371,-208),new Array(414,-117),-10),
    new Array(new Array(1,-468),new Array(68,-409),new Array(152,-343),new Array(258,-262),new Array(370,-183),new Array(414,-93),0),
    new Array(new Array(1,-430),new Array(67,-374),new Array(144,-309),new Array(252,-225),new Array(371,-141),new Array(385,-131),new Array(414,-70),10),
    new Array(new Array(0,-391),new Array(63,-336),new Array(138,-271),new Array(248,-183),new Array(370,-96),new Array(400,-76),new Array(414,-48),20),
    new Array(new Array(87,-268),new Array(189,-182),new Array(298,-99),new Array(370,-49),new Array(414,-19),30),
    new Array(new Array(173,-146),new Array(238,-94),new Array(315,-38),new Array(370,1),40),
    new Array(new Array(264,-24),new Array(298,1),50)
);

/********************  R44 CLIPPER 2 / RAVEN 2 IN ********************/
export const canvas_r44_2_in = "micanvas_r44_2_in";
export const src_r44_2_in = "/leulit_operaciones/static/src/img/R44_2_IGE_HOVER_CEILING_VS_GROSS_WEIGHT.jpg";

// Eje de peso
export const inicio_eje_r44_2_in = 2000;
export const proporcion_r44_2_in = 0.535893;
// Uso: calc_peso(peso, inicio_eje_r44_2, proporcion_r44_2_in, false)

// Coordenadas de imagen (pixels)
export const altura_imagen_r44_2_in = 620;
export const inicio_eje_x_r44_2_in = 53;
export const inicio_eje_y_r44_2_in = -93;  // = 527 - 620

// Curvas de temperatura (8 curvas)
// Formato: cada fila = [...puntos [x,y] ordenados por x..., temperatura_exacta]
export const temperaturas_r44_2_in = new Array(
    new Array(new Array(98,-478),new Array(271,-299),-30),
    new Array(new Array(116,-426),new Array(271,-264),-20),
    new Array(new Array(131,-379),new Array(271,-228),-10),
    new Array(new Array(148,-327),new Array(271,-195),0),
    new Array(new Array(164,-277),new Array(271,-163),10),
    new Array(new Array(179,-229),new Array(271,-131),20),
    new Array(new Array(195,-181),new Array(271,-101),30),
    new Array(new Array(210,-134),new Array(271,-69),40)
);

/********************  R44 CLIPPER 2 / RAVEN 2 OUT ********************/
export const canvas_r44_2_out = "micanvas_r44_2_out";
export const src_r44_2_out = "/leulit_operaciones/static/src/img/R44_2_OGE_HOVER_CEILING_VD_GROSS_WEIGHT.jpg";

// Eje de peso
export const inicio_eje_r44_2_out = 1700;
export const proporcion_r44_2_out = 0.403427;
// Uso: calc_peso(peso, inicio_eje_r44_2, proporcion_r44_2_out, false)

// Coordenadas de imagen (pixels)
export const altura_imagen_r44_2_out = 745;
export const inicio_eje_x_r44_2_out = 46;
export const inicio_eje_y_r44_2_out = -143;  // = 602 - 745

// Curvas de temperatura (8 curvas)
// Formato: cada fila = [...puntos [x,y] ordenados por x..., temperatura_exacta]
export const temperaturas_r44_2_out = new Array(
    new Array(new Array(86,-558),new Array(162,-468),new Array(248,-371),new Array(324,-288),-30),
    new Array(new Array(97,-519),new Array(176,-426),new Array(248,-344),new Array(324,-263),-20),
    new Array(new Array(107,-483),new Array(193,-381),new Array(250,-314),new Array(324,-237),-10),
    new Array(new Array(118,-445),new Array(193,-356),new Array(262,-275),new Array(318,-215),new Array(324,-194),0),
    new Array(new Array(130,-406),new Array(198,-325),new Array(260,-253),new Array(311,-199),new Array(324,-151),10),
    new Array(new Array(141,-368),new Array(204,-295),new Array(267,-221),new Array(305,-178),new Array(324,-107),20),
    new Array(new Array(152,-331),new Array(208,-266),new Array(267,-196),new Array(298,-159),new Array(324,-69),30),
    new Array(new Array(162,-296),new Array(209,-240),new Array(267,-173),new Array(292,-146),new Array(323,-33),40)
);

/********************  R44 ASTRO IN ********************/
export const canvas_r44_in = "micanvas_r44_in";
export const src_r44_in = "/leulit_operaciones/static/src/img/R44_IGE_HOVER_CEILING_VS_GROSS_WEIGHT.png";

// Eje de peso
export const inicio_eje_r44_in = 1500;
export const proporcion_r44_in = 0.485026;
// Uso: calc_peso(peso, inicio_eje_r44, proporcion_r44_in, false)

// Coordenadas de imagen (pixels)
export const altura_imagen_r44_in = 900;
export const inicio_eje_x_r44_in = 86;
export const inicio_eje_y_r44_in = -134;  // = 766 - 900

// Curvas de temperatura (7 curvas)
// Formato: cada fila = [...puntos [x,y] ordenados por x..., temperatura_exacta]
export const temperaturas_r44_in = new Array(
    new Array(new Array(213,-617),new Array(341,-475),new Array(440,-371),-20),
    new Array(new Array(227,-569),new Array(355,-429),new Array(439,-339),-10),
    new Array(new Array(240,-526),new Array(350,-406),new Array(440,-310),0),
    new Array(new Array(253,-480),new Array(348,-375),new Array(440,-279),10),
    new Array(new Array(263,-439),new Array(352,-339),new Array(441,-245),20),
    new Array(new Array(265,-391),new Array(354,-289),new Array(440,-198),30),
    new Array(new Array(255,-351),new Array(350,-245),new Array(440,-156),40)
);

/********************  R44 ASTRO OUT ********************/
export const canvas_r44_out = "micanvas_r44_out";
export const src_r44_out = "/leulit_operaciones/static/src/img/R44_OGE_HOVER_CEILING_VS_GROSS_WEIGHT.png";

// Eje de peso
export const inicio_eje_r44_out = 1494;
export const proporcion_r44_out = 0.482723;
// Uso: calc_peso(peso, inicio_eje_r44, proporcion_r44_out, false)

// Coordenadas de imagen (pixels)
export const altura_imagen_r44_out = 900;
export const inicio_eje_x_r44_out = 81;
export const inicio_eje_y_r44_out = -134;  // = 766 - 900

// Curvas de temperatura (7 curvas)
// Formato: cada fila = [...puntos [x,y] ordenados por x..., temperatura_exacta]
export const temperaturas_r44_out = new Array(
    new Array(new Array(99,-623),new Array(166,-538),new Array(282,-400),new Array(357,-316),new Array(441,-228),-20),
    new Array(new Array(112,-570),new Array(199,-465),new Array(294,-354),new Array(367,-272),new Array(441,-196),-10),
    new Array(new Array(122,-531),new Array(212,-420),new Array(302,-316),new Array(373,-236),new Array(442,-167),0),
    new Array(new Array(134,-477),new Array(223,-372),new Array(304,-279),new Array(375,-200),new Array(431,-146),new Array(440,-104),10),
    new Array(new Array(140,-438),new Array(233,-325),new Array(304,-244),new Array(380,-159),new Array(414,-125),new Array(440,-24),20),
    new Array(new Array(145,-392),new Array(245,-268),new Array(312,-192),new Array(395,-100),new Array(423,0),30),
    new Array(new Array(140,-349),new Array(212,-261),new Array(310,-147),new Array(365,-86),new Array(392,1),40)
);
