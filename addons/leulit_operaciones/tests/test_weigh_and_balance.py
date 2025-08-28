from odoo.tests import common 
 
 
class TestWeightAndBalance(common.TransactionCase):
 
    def setUp(self):
        super(TestWeightAndBalance, self).setUp()
        # Add the set up code here...
        self.wandb = self.env['leulit.weight_and_balance']
    
        # create an employee record
        self.wandb1 = self.employee.create({
            'emptyweight': 398.26,
            'frs': 75,
        })

 
    def test_validate_semaforos(self):
        # check position of the employee1
        self.assertEqual(self.wandb1.valid_takeoff_longcg, True)
        self.assertEqual(self.wandb1.valid_takeoff_latcg, True)
        self.assertEqual(self.wandb1.valid_landing_longcg, True)
        self.assertEqual(self.wandb1.valid_landing_latcg, True)
        
