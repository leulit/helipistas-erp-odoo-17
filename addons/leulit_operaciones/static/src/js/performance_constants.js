/** @odoo-module **/
export const canvas_hil_in = "micanvas_hil_in";
export const canvas_hil_out = "micanvas_hil_out";
export const canvas_ec_in = "micanvas_ec_in";
export const canvas_ec_out = "micanvas_ec_out";
export const canvas_r22_in = "micanvas_r22_in";
export const canvas_r22_out = "micanvas_r22_out";
export const canvas_r22_2_in = "micanvas_r22_2_in";
export const canvas_r22_2_out = "micanvas_r22_2_out";
export const canvas_r44_2_in = "micanvas_r44_2_in";
export const canvas_r44_2_out = "micanvas_r44_2_out";
export const canvas_r44_in = "micanvas_r44_in";
export const canvas_r44_out = "micanvas_r44_out";
export const canvas_cabri_in= "micanvas_cabri_in";
export const canvas_cabri_out= "micanvas_cabri_out";

export const src_cabri_in = "leulit_operaciones/static/src/img/cabri_g2_in.png";
export const src_cabri_out = "leulit_operaciones/static/src/img/cabri_g2_out.png";
export const src_ec_in = "leulit_operaciones/static/src/img/ec_120_b_in.png";
export const src_ec_out = "leulit_operaciones/static/src/img/ec_120_b_out.png";
export const src_hil_in = "leulit_operaciones/static/src/img/ec_120_b_in.png";
export const src_hil_out = "leulit_operaciones/static/src/img/hil_hook_out.png";
export const src_r22_in = "leulit_operaciones/static/src/img/r22_beta_in.png";
export const src_r22_out = "leulit_operaciones/static/src/img/r22_beta_out.png";
export const src_r22_2_in = "leulit_operaciones/static/src/img/r22_beta_2_in.png";
export const src_r22_2_out = "leulit_operaciones/static/src/img/r22_beta_2_out.png";
export const src_r44_2_in = "leulit_operaciones/static/src/img/R44_2_IGE_HOVER_CEILING_VS_GROSS_WEIGHT.jpg";
export const src_r44_2_out = "leulit_operaciones/static/src/img/R44_2_OGE_HOVER_CEILING_VD_GROSS_WEIGHT.jpg";
export const src_r44_in = "leulit_operaciones/static/src/img/R44_IGE_HOVER_CEILING_VS_GROSS_WEIGHT.png";
export const src_r44_out = "leulit_operaciones/static/src/img/R44_OGE_HOVER_CEILING_VS_GROSS_WEIGHT.png";
/********************  R22 Beta IN ********************/
export const inicio_eje_r22 = 900;           // PESO INICIAL DE LA GRAFICA
export const proporcion_beta_in = 0.818;     // NI IDEA

export const altura_imagen_beta_in = 720;    // ALTURA DE LA IMAGEN
export const inicio_eje_x_beta_in = 54;      // POSICIÓN X DEL INICIO DE LA GRAFICA
export const inicio_eje_y_beta_in = -184;    // POSICIÓN Y DEL INICIO DE LA GRAFICA (SE LEE AL INVERSO, RESTAR LOS PIXELES DE ALTURA DEL INICIO DEL EJE MENOS LA ALTURA DE LA IMAGEN)
// PARA CALCULAR UN PUNTO CON CUALQUIER EDITOR DE IMAGEN, BUSCAMOS EL PUNTO DE PIXELES QUE QUEREMOS, POR EJEMPLO (X=177,Y=68):
// CALCULO DEL PUNTO X --> punto x (de la imagen) - inicio_eje_x_beta_in = x   -->  177-54= 123  
// CALCULO DEL PUNTO Y --> punto y (de la imagen) - altura_imagen_beta_in + inicio_eje_y_beta_in = y    --> 68-720+184= -468
export const temperaturas_beta_in = new Array(new Array(new Array(123,-468),new Array(386,-237),new Array(386,-219),new Array(147,-425),new Array(-20,-10)),
                                            new Array(new Array(147,-425),new Array(386,-219),new Array(386,-202),new Array(170,-354),new Array(-10,0)),
                                            new Array(new Array(170,-384),new Array(386,-202),new Array(386,-184),new Array(189,-351),new Array(0,10)),
                                            new Array(new Array(189,-351),new Array(386,-184),new Array(386,-165),new Array(210,-313),new Array(10,20)),
                                            new Array(new Array(210,-313),new Array(386,-165),new Array(386,-148),new Array(228,-279),new Array(20,30)),
                                            new Array(new Array(228,-279),new Array(386,-148),new Array(386,-133),new Array(247,-245),new Array(30,40)));

/********************  R22 Beta OUT  ********************/

export const proporcion_beta_out = 0.86;

export const altura_imagen_beta_out = 770;
export const inicio_eje_x_beta_out = 67;
export const inicio_eje_y_beta_out = -133;
export const temperaturas_beta_out = new Array(new Array(new Array(65,-573),new Array(402,-275),new Array(402,-253),new Array(89,-531),new Array(-20,-10)),
                                            new Array(new Array(89,-531),new Array(402,-253),new Array(402,-225),new Array(108,-495),new Array(-10,0)),
                                            new Array(new Array(108,-495),new Array(402,-225),new Array(402,-199),new Array(130,-453),new Array(0,10)),
                                            new Array(new Array(130,-453),new Array(402,-199),new Array(396,-181),new Array(151,-418),new Array(402,-168),new Array(10,20)),
                                            new Array(new Array(151,-418),new Array(396,-181),new Array(396,-159),new Array(171,-381),new Array(402,-169),new Array(402,-140),new Array(20,30)),
                                            new Array(new Array(171,-381),new Array(396,-159),new Array(394,-137),new Array(192,-343),new Array(402,-104),new Array(402,-99),new Array(30,40)));

/********************  R22 2 Beta IN ********************/
export const inicio_eje_r22_2_in = 1100;
export const proporcion_beta_2_in = 0.9;

export const altura_imagen_beta_2_in = 717;
export const inicio_eje_x_beta_2_in = 72;
export const inicio_eje_y_beta_2_in = -156;
export const temperaturas_beta_2_in = new Array(new Array(new Array(105,-485),new Array(305,-305),new Array(305,-273),new Array(128,-431),new Array(-20,-10)),
                                            new Array(new Array(128,-431),new Array(305,-273),new Array(305,-243),new Array(150,-382),new Array(-10,0)),
                                            new Array(new Array(150,-382),new Array(305,-243),new Array(305,-211),new Array(171,-336),new Array(0,10)),
                                            new Array(new Array(171,-336),new Array(305,-211),new Array(305,-179),new Array(196,-279),new Array(10,20)),
                                            new Array(new Array(196,-279),new Array(305,-179),new Array(305,-153),new Array(218,-232),new Array(20,30)),
                                            new Array(new Array(218,-232),new Array(305,-153),new Array(305,-122),new Array(240,-182),new Array(30,40)));

/********************  R22 2 Beta OUT  ********************/
export const inicio_eje_r22_2_out = 1000;
export const proporcion_beta_2_out = 0.89;

export const altura_imagen_beta_2_out = 790;
export const inicio_eje_x_beta_2_out = 62;
export const inicio_eje_y_beta_2_out = -141;
export const temperaturas_beta_2_out = new Array(new Array(new Array(62,-579),new Array(322,-341),new Array(316,-323),new Array(84,-533),new Array(330,-320),new Array(330,-279),new Array(-20,-10)),
                                            new Array(new Array(84,-533),new Array(316,-323),new Array(309,-305),new Array(102,-496),new Array(330,-279),new Array(330,-240),new Array(-10,0)),
                                            new Array(new Array(102,-496),new Array(309,-305),new Array(303,-288),new Array(121,-454),new Array(330,-240),new Array(330,-202),new Array(0,10)),
                                            new Array(new Array(121,-454),new Array(303,-288),new Array(299,-268),new Array(137,-417),new Array(330,-202),new Array(330,-161),new Array(10,20)),
                                            new Array(new Array(137,-417),new Array(299,-268),new Array(295,-251),new Array(154,-383),new Array(330,-161),new Array(330,-125),new Array(20,30)),
                                            new Array(new Array(154,-383),new Array(295,-251),new Array(290,-232),new Array(171,-346),new Array(330,-125),new Array(330,-93),new Array(30,40)));

/********************  Cabri G2 IN  ********************/

export const inicio_eje_cabri = 470;
export const proporcion_cabri = 0.5714;

export const altura_imagen_cabri_in = 515;
export const inicio_eje_x_cabri_in = 49;
export const inicio_eje_y_cabri_in = -69;
export const temperaturas_cabri_in = new Array(new Array(new Array(71,-403),new Array(230,-296),new Array(220,-285),new Array(49,-403),new Array(407,-189),new Array(407,-171),new Array(141,-352),new Array(-20,-10)),
                                    new Array(new Array(49,-403),new Array(220,-285),new Array(211,-274),new Array(27,-403),new Array(407,-171),new Array(407,-154),new Array(-10,0)),
                                    new Array(new Array(27,-403),new Array(211,-274),new Array(202,-263),new Array(6,-403),new Array(407,-154),new Array(407,-137),new Array(0,10)),
                                    new Array(new Array(6,-403),new Array(202,-263),new Array(194,-253),new Array(0,-392),new Array(407,-137),new Array(407,-121),new Array(10,20)),
                                    new Array(new Array(0,-392),new Array(194,-253),new Array(184,-245),new Array(0,-377),new Array(407,-121),new Array(407,-105),new Array(20,30)));

/********************  Cabri G2 OUT  ********************/

export const altura_imagen_cabri_out = 515;
export const inicio_eje_x_cabri_out = 49;
export const inicio_eje_y_cabri_out = -64;
export const temperaturas_cabri_out = new Array(new Array(new Array(29,-403),new Array(158,-309),new Array(156,-293),new Array(7,-403),new Array(378,-170),new Array(371,-156),new Array(407,-90),new Array(407,-346),new Array(-20,-10)),
                                    new Array(new Array(7,-401),new Array(156,-293),new Array(155,-277),new Array(0,-389),new Array(371,-156),new Array(364,-143),new Array(407,-57),new Array(407,-25),new Array(-10,0)),
                                    new Array(new Array(0,-389),new Array(155,-277),new Array(154,-263),new Array(0,-374),new Array(364,-143),new Array(360,-128),new Array(407,-25),new Array(404,0),new Array(0,10)),
                                    new Array(new Array(0,-374),new Array(154,-263),new Array(154,-248),new Array(0,-359),new Array(360,-128),new Array(354,-116),new Array(404,0),new Array(395,0),new Array(10,20)),
                                    new Array(new Array(0,-359),new Array(154,-248),new Array(153,-232),new Array(0,-344),new Array(354,-116),new Array(348,-103),new Array(395,0),new Array(384,0),new Array(20,30)));

/********************  EC 120 IN  ********************/

export const inicio_eje_ec = 1000;
export const proporcion_ec_in = 0.5;

export const altura_imagen_ec_in = 636;
export const inicio_eje_x_ec_in = 40;
export const inicio_eje_y_ec_in = -52;
export const temperaturas_ec_in = new Array(new Array(new Array(144,-484),new Array(205,-435),new Array(192,-425),new Array(119,-484),new Array(310,-360),new Array(271,-368),new Array(357,-327),new Array(357,-308),new Array(-40,-30)),
                                new Array(new Array(119,-484),new Array(192,-425),new Array(161,-425),new Array(90,-484),new Array(271,-368),new Array(251,-359),new Array(357,-308),new Array(357,-283),new Array(-30,-20)),
                                new Array(new Array(90,-484),new Array(161,-425),new Array(162,-393),new Array(53,-484),new Array(251,-359),new Array(261,-368),new Array(357,-283),new Array(357,-249),new Array(-20,-10)),
                                new Array(new Array(53,-484),new Array(162,-393),new Array(156,-363),new Array(13,-484),new Array(261,-369),new Array(255,-285),new Array(357,-235),new Array(357,-273),new Array(-10,0)),
                                new Array(new Array(13,-484),new Array(156,-363),new Array(123,-351),new Array(2,-455),new Array(255,-285),new Array(249,-248),new Array(357,-211),new Array(357,-169),new Array(0,10)),
                                new Array(new Array(2,-455),new Array(123,-351),new Array(138,-294),new Array(28,-392),new Array(249,-248),new Array(267,-190),new Array(357,-169),new Array(357,-359),new Array(10,20)),
                                new Array(new Array(28,-392),new Array(138,-294),new Array(209,-189),new Array(114,-269),new Array(267,-190),new Array(300,-119),new Array(357,-125),new Array(357,-77),new Array(20,30)),
                                new Array(new Array(114,-264),new Array(209,-189),new Array(250,-108),new Array(201,-147),new Array(300,-118),new Array(308,-64),new Array(357,-77),new Array(357,-28),new Array(30,40)),
                                new Array(new Array(201,-147),new Array(250,-108),new Array(303,-17),new Array(293,-25),new Array(308,-64),new Array(313,-10),new Array(357,-28),new Array(326,0),new Array(40,50)));

/********************  EC 120 OUT  ********************/
export const proporcion_ec_out = 0.5187;

export const altura_imagen_ec_out = 645;
export const inicio_eje_x_ec_out = 38;
export const inicio_eje_y_ec_out = -56;
export const temperaturas_ec_out = new Array(new Array(new Array(118,-482),new Array(209,-412),new Array(200,-399),new Array(93,-482),new Array(359,-306),new Array(354,-290),new Array(371,-285),new Array(371,-257),new Array(-40,-30)),
                                new Array(new Array(93,-482),new Array(200,-399),new Array(186,-385),new Array(64,-482),new Array(354,-290),new Array(355,-265),new Array(371,-257),new Array(371,-235),new Array(-30,-20)),
                                new Array(new Array(64,-482),new Array(186,-385),new Array(178,-361),new Array(27,-482),new Array(355,-265),new Array(361,-228),new Array(371,-235),new Array(371,-211),new Array(-20,-10)),
                                new Array(new Array(27,-482),new Array(178,-361),new Array(162,-336),new Array(1,-469),new Array(361,-228),new Array(262,-260),new Array(371,-211),new Array(371,-184),new Array(-10,0)),
                                new Array(new Array(0,-464),new Array(162,-336),new Array(133,-318),new Array(0,-431),new Array(262,-260),new Array(262,-218),new Array(371,-184),new Array(371,-141),new Array(0,10)),
                                new Array(new Array(0,-51),new Array(133,-318),new Array(97,-306),new Array(0,-392),new Array(262,-218),new Array(260,-175),new Array(371,-141),new Array(371,-96),new Array(10,20)),
                                new Array(new Array(0,-392),new Array(97,-306),new Array(198,-176),new Array(88,-268),new Array(260,-176),new Array(297,-100),new Array(371,-96),new Array(371,-49),new Array(20,30)),
                                new Array(new Array(88,-268),new Array(198,-176),new Array(236,-96),new Array(175,-145),new Array(297,-100),new Array(312,-40),new Array(371,-49),new Array(371,0),new Array(30,40)),
                                new Array(new Array(175,-145),new Array(236,-96),new Array(276,-16),new Array(264,-25),new Array(312,-40),new Array(286,-8),new Array(371,0),new Array(371,0),new Array(40,50)));

/********************  EC-HIL HOOK IN  ********************/
export const inicio_eje_hil = 1000;
export const proporcion_hil_in = 0.5;

export const altura_imagen_hil_in = 636;
export const inicio_eje_x_hil_in = 40;
export const inicio_eje_y_hil_in = -52;
export const temperaturas_hil_in = new Array(new Array(new Array(144,-484),new Array(205,-435),new Array(192,-425),new Array(119,-484),new Array(310,-360),new Array(271,-368),new Array(357,-327),new Array(357,-308),new Array(-40,-30)),
                                new Array(new Array(119,-484),new Array(192,-425),new Array(161,-425),new Array(90,-484),new Array(271,-368),new Array(251,-359),new Array(357,-308),new Array(357,-283),new Array(-30,-20)),
                                new Array(new Array(90,-484),new Array(161,-425),new Array(162,-393),new Array(53,-484),new Array(251,-359),new Array(261,-320),new Array(357,-283),new Array(357,-249),new Array(-20,-10)),
                                new Array(new Array(53,-484),new Array(162,-393),new Array(156,-363),new Array(13,-484),new Array(261,-320),new Array(255,-285),new Array(357,-249),new Array(357,-211),new Array(-10,0)),
                                new Array(new Array(13,-484),new Array(156,-363),new Array(123,-351),new Array(2,-455),new Array(255,-285),new Array(249,-248),new Array(357,-211),new Array(357,-169),new Array(0,10)),
                                new Array(new Array(2,-455),new Array(123,-351),new Array(138,-294),new Array(28,-392),new Array(249,-248),new Array(267,-190),new Array(357,-169),new Array(357,-125),new Array(10,20)),
                                new Array(new Array(28,-392),new Array(138,-294),new Array(209,-189),new Array(114,-269),new Array(267,-190),new Array(300,-119),new Array(357,-125),new Array(357,-77),new Array(20,30)),
                                new Array(new Array(114,-264),new Array(209,-189),new Array(250,-108),new Array(201,-147),new Array(300,-118),new Array(308,-64),new Array(357,-77),new Array(357,-28),new Array(30,40)),
                                new Array(new Array(201,-147),new Array(250,-108),new Array(303,-17),new Array(293,-25),new Array(308,-64),new Array(313,-10),new Array(357,-28),new Array(326,0),new Array(40,50)));

/********************  EC-HIL HOOK OUT  ********************/
export const proporcion_hil_out = 0.5187;

export const altura_imagen_hil_out = 645;
export const inicio_eje_x_hil_out = 38;
export const inicio_eje_y_hil_out = -56;
export const temperaturas_hil_out = new Array(new Array(new Array(118,-482),new Array(209,-412),new Array(200,-399),new Array(93,-482),new Array(359,-306),new Array(354,-290),new Array(412,-195),new Array(412,-169),new Array(-40,-30)),
                                new Array(new Array(93,-482),new Array(200,-399),new Array(186,-385),new Array(64,-482),new Array(354,-290),new Array(355,-265),new Array(412,-169),new Array(412,-143),new Array(-30,-20)),
                                new Array(new Array(64,-482),new Array(186,-385),new Array(178,-361),new Array(27,-482),new Array(355,-265),new Array(361,-228),new Array(412,-143),new Array(412,-118),new Array(-20,-10)),
                                new Array(new Array(27,-482),new Array(178,-361),new Array(162,-336),new Array(1,-469),new Array(361,-228),new Array(370,-180),new Array(412,-118),new Array(412,-94),new Array(-10,0)),
                                new Array(new Array(0,-464),new Array(162,-336),new Array(133,-318),new Array(0,-431),new Array(370,-180),new Array(384,-130),new Array(412,-94),new Array(412,-70),new Array(0,10)),
                                new Array(new Array(0,-51),new Array(133,-318),new Array(97,-306),new Array(0,-392),new Array(384,-130),new Array(400,-75),new Array(412,-70),new Array(412,-48),new Array(10,20)),
                                new Array(new Array(0,-392),new Array(97,-306),new Array(198,-176),new Array(88,-268),new Array(400,-75),new Array(297,-100),new Array(412,-48),new Array(412,-18),new Array(20,30)),
                                new Array(new Array(88,-268),new Array(258,-128),new Array(258,-76),new Array(175,-145),new Array(412,-18),new Array(412,0),new Array(30,40)),
                                new Array(new Array(175,-145),new Array(236,-96),new Array(276,-16),new Array(264,-25),new Array(40,50)));

/********************  R44 CLIPPER 2 / RAVEN 2 IN ********************/

export const inicio_eje_r44_2_in = 2000;
export const proporcion_r44_2_in = 0.5387158;

export const altura_imagen_r44 = 0;
export const inicio_eje_x_r44_2_in = 53;
export const inicio_eje_y_r44_2_in = 528;
export const temperaturas_r44_2_ige = new Array(new Array(new Array(99,-478),new Array(269,-299),new Array(269,-265),new Array(116,-423),new Array(-30,-20)),
                                    new Array(new Array(116,-423),new Array(269,-265),new Array(269,-229),new Array(133,-374),new Array(-20,-10)),
                                    new Array(new Array(133,-374),new Array(269,-229),new Array(269,-196),new Array(150,-322),new Array(-10,0)),
                                    new Array(new Array(150,-322),new Array(269,-196),new Array(269,-164),new Array(164,-274),new Array(0,10)),
                                    new Array(new Array(164,-274),new Array(269,-164),new Array(269,-131),new Array(181,-225),new Array(10,20)),
                                    new Array(new Array(181,-225),new Array(269,-131),new Array(269,-101),new Array(196,-179),new Array(20,30)),
                                    new Array(new Array(196,-179),new Array(269,-101),new Array(269,-69),new Array(212,-130),new Array(30,40)));

/********************  R44 CLIPPER 2 / RAVEN 2 OUT ********************/

export const inicio_eje_r44_2_out = 1700;
export const proporcion_r44_2_out = 0.4078;

export const inicio_eje_x_r44_2_out = 46.2; 
export const inicio_eje_y_r44_2_out = 601.6;
export const temperaturas_r44_2_oge= new Array(new Array(new Array(85.8,-557.6),new Array(323.8,-289.6),new Array(323.8,-263.6),new Array(96.8,-519.6),new Array(-30,-20)),
                                new Array(new Array(96.8,-519.6),new Array(323.8,-263.6),new Array(323.8,-236.6),new Array(108.8,-481.6),new Array(-20,-10)),
                                new Array(new Array(108.8,-481.6),new Array(323.8,-236.6),new Array(318.8,-215.6),new Array(118.8,-443.6),new Array(323.8,-195.6),new Array(-10,0)),
                                new Array(new Array(118.8,-443.6),new Array(318.8,-215.6),new Array(311.8,-198.6),new Array(130.8,-404.6),new Array(323.8,-195.6),new Array(323.8,-151.6),new Array(0,10)),
                                new Array(new Array(130.8,-404.6),new Array(311.8,-198.6),new Array(304.8,-177.6),new Array(140.8,-367.6),new Array(323.8,-151.6),new Array(323.8,-107.6),new Array(10,20)),
                                new Array(new Array(140.8,-367.6),new Array(304.8,-177.6),new Array(296.8,-159.6),new Array(152.8,-329.6),new Array(323.8,-107.6),new Array(323.8,-71.6),new Array(20,30)),
                                new Array(new Array(152.8,-329.6),new Array(296.8,-159.6),new Array(291.8,-145.6),new Array(162.8,-294.6),new Array(323.8,-71.6),new Array(323.8,-36.6),new Array(30,40)));

/********************  R44 ASTRO IN ********************/

export const inicio_eje_r44 = 1500;
export const proporcion_r44 = 0.49;

export const inicio_eje_x_r44_in = 86;
export const inicio_eje_y_r44_in = 766;
export const temperaturas_r44_ige = new Array(new Array(new Array(213,-614),new Array(437,-374),new Array(437,-341),new Array(228,-567),new Array(-20,-10)),
                                new Array(new Array(228,-567),new Array(437,-341),new Array(437,-313),new Array(241,-523),new Array(-10,0)),
                                new Array(new Array(241,-523),new Array(437,-313),new Array(437,-280),new Array(254,-477),new Array(0,10)),
                                new Array(new Array(254,-477),new Array(437,-280),new Array(437,-249),new Array(263,-437),new Array(10,20)),
                                new Array(new Array(263,-437),new Array(437,-249),new Array(437,-199),new Array(266,-389),new Array(20,30)),
                                new Array(new Array(266,-389),new Array(437,-199),new Array(437,-158),new Array(256,-349),new Array(30,40)));

/********************  R44 ASTRO OUT ********************/

export const inicio_eje_x_r44_out = 82;
export const inicio_eje_y_r44_out = 766;
export const temperaturas_r44_oge = new Array(new Array(new Array(99,-619),new Array(441,-226),new Array(441,-194),new Array(113,-568),new Array(-20,-10)),
                                new Array(new Array(113,-568),new Array(441,-194),new Array(441,-165),new Array(122,-528),new Array(-10,0)),
                                new Array(new Array(122,-528),new Array(441,-165),new Array(432,-145),new Array(133,-476),new Array(441,-105),new Array(0,10)),
                                new Array(new Array(133,-476),new Array(432,-145),new Array(414,-123),new Array(140,-437),new Array(441,-105),new Array(441,-24),new Array(10,20)),
                                new Array(new Array(140,-437),new Array(414,-123),new Array(396,-97),new Array(145,-390),new Array(441,-24),new Array(423,0),new Array(20,30)),
                                new Array(new Array(145,-390),new Array(396,-97),new Array(364,-85),new Array(140,-347),new Array(423,0),new Array(392,0),new Array(30,40)));
    