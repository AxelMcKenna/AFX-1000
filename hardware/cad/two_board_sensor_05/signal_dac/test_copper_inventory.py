import unittest
from hardware.cad.two_board_sensor_05.signal_dac.copper_inventory import validate_inventory

class CopperInventoryTests(unittest.TestCase):
    def setUp(self):
        self.original={'original':{'kind':'segment','authored':'original path'}}
        self.before={**self.original,'agent':{'kind':'via','authored':'agent via'}}
        self.after={**self.original,'replacement':{'kind':'segment','authored':'new path'}}
        self.declared=[{'uuid':'agent','before_sexpr':'agent via'}]
    def test_declared_agent_replacement(self):
        self.assertEqual(validate_inventory(self.before,self.after,self.original,self.declared,self.after)['removed'],['agent'])
    def test_original_removal_rejected(self):
        after={'agent':self.before['agent'],'replacement':self.after['replacement']}
        with self.assertRaisesRegex(AssertionError,'original copper'):
            validate_inventory(self.before,after,self.original,[{'uuid':'original','before_sexpr':'original path'}],after)
    def test_retained_edit_rejected(self):
        after={**self.after,'original':{'kind':'segment','authored':'shifted original'}}
        with self.assertRaisesRegex(AssertionError,'retained checkpoint'):
            validate_inventory(self.before,after,self.original,self.declared,after)
    def test_undeclared_native_addition_rejected(self):
        after={**self.after,'surprise':{'kind':'via','authored':'unexpected via'}}
        with self.assertRaisesRegex(AssertionError,'inventory differs'):
            validate_inventory(self.before,after,self.original,self.declared,self.after)
    def test_stale_declaration_rejected(self):
        with self.assertRaisesRegex(AssertionError,'stale removal'):
            validate_inventory(self.before,self.after,self.original,[{'uuid':'agent','before_sexpr':'different via'}],self.after)
if __name__=='__main__':unittest.main()
