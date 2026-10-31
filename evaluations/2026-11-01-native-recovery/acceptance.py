import unittest
from billing import invoice_total
class Contract(unittest.TestCase):
 def test_lookup(self): self.assertEqual(invoice_total([{'tenant':'a','id':'x','amount':10}], 'a','x'),10)
 def test_tenant(self): self.assertEqual(invoice_total([{'tenant':'b','id':'x','amount':50},{'tenant':'a','id':'x','amount':10}], 'a','x'),10)
 def test_missing(self):
  with self.assertRaises(KeyError): invoice_total([{'tenant':'b','id':'x','amount':50}], 'a','x')
 def test_falsey_and_no_mutation(self):
  rows=[{'tenant':'a','id':'x','amount':0}];copy=[dict(r) for r in rows]
  self.assertEqual(invoice_total(rows,'a','x'),0);self.assertEqual(rows,copy)
if __name__=='__main__': unittest.main()
