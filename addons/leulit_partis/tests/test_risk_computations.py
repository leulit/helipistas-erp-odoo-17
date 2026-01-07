"""Tests for PART-IS (SGSI) risk computations over MAGERIT metrics."""

from odoo.tests.common import TransactionCase


class TestRiskComputations(TransactionCase):
    """Ensure PART-IS calculations derived from MAGERIT behave as expected."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["ir.config_parameter"].sudo()
        cls.asset_model = cls.env["mgmtsystem.hazard"].sudo()  # OCA: activos Y riesgos
        cls.risk_model = cls.env["mgmtsystem.hazard"].sudo()   # Mismo modelo
        cls.threat_model = cls.env["mgmtsystem.risk.threat"].sudo()
        cls.vulnerability_model = cls.env["mgmtsystem.risk.vulnerability"].sudo()
        cls.control_model = cls.env["mgmtsystem.risk.control"].sudo()

    def test_asset_threshold_customization(self):
        """Asset criticity follows configurable PART-IS thresholds."""
        self.config.set_param(
            "leulit_partis.asset_level_low", 1.0
        )
        self.config.set_param(
            "leulit_partis.asset_level_medium", 2.0
        )
        self.config.set_param(
            "leulit_partis.asset_level_high", 3.0
        )
        self.config.set_param(
            "leulit_partis.asset_level_critical", 4.0
        )

        asset = self.asset_model.create(
            {
                "name": "Servidor SGSI",
                "magerit_confidentiality": "5",
                "magerit_integrity": "4",
                "magerit_availability": "4",
            }
        )
        self.assertAlmostEqual(asset.magerit_asset_score, 4.33, places=2)
        self.assertEqual(asset.magerit_asset_level, "critical")

    def test_risk_computation_and_residual(self):
        """Risk levels react to asset, threat, and residual inputs."""
        threat = self.threat_model.create(
            {
                "name": "Ciberataque",
                "default_probability": "4",
            }
        )
        vulnerability = self.vulnerability_model.create(
            {
                "name": "Patch pendiente",
            }
        )
        control = self.control_model.create(
            {
                "name": "Gestión de parches",
                "control_type": "preventive",
            }
        )
        asset = self.asset_model.create(
            {
                "name": "Servidor Aplicaciones",
                "magerit_confidentiality": "4",
                "magerit_integrity": "4",
                "magerit_availability": "3",
            }
        )

        risk = self.risk_model.create(
            {
                "name": "Ataque al servidor",
                "magerit_asset_id": asset.id,
                "magerit_threat_id": threat.id,
                "magerit_vulnerability_id": vulnerability.id,
                "magerit_probability": "4",
                "magerit_impact": "4",
                "pilar_treatment_strategy": "reduce",
                "pilar_control_ids": [(6, 0, control.ids)],
                "pilar_residual_probability": "2",
                "pilar_residual_impact": "2",
            }
        )

        self.assertEqual(risk.magerit_inherent_score, 16)
        self.assertEqual(risk.magerit_inherent_level, "high")
        self.assertEqual(risk.pilar_residual_score, 4)
        self.assertEqual(risk.pilar_residual_level, "low")
        self.assertIn("[PREVENTIVE] Gestión de parches", risk.pilar_control_summary)
