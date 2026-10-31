import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).with_name('billing.py')
# Portable replay: original Windows byte hash remains in the QA reports.
EXPECTED = '860477b54ac610fead9e0f9c0f674ef0b2471045173d8be9987c61ebcc52d2a4'
assert hashlib.sha256(SOURCE.read_text(encoding='utf-8').encode('utf-8')).hexdigest() == EXPECTED
spec = importlib.util.spec_from_file_location('billing', SOURCE)
billing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(billing)

class InvoiceContract(unittest.TestCase):
    def lookup(self, records, tenant, invoice_id, expected=None, missing=False):
        before = copy.deepcopy(records)
        identities = [id(record) for record in records]
        if missing:
            with self.assertRaises(KeyError):
                billing.invoice_total(records, tenant, invoice_id)
        else:
            self.assertEqual(billing.invoice_total(records, tenant, invoice_id), expected)
        self.assertEqual(records, before)
        self.assertEqual([id(record) for record in records], identities)

    def test_normal_integer_cents(self):
        self.lookup([{'tenant': 'a', 'id': 'i', 'amount': 12345}], 'a', 'i', 12345)

    def test_zero(self):
        self.lookup([{'tenant': 'a', 'id': 'i', 'amount': 0}], 'a', 'i', 0)

    def test_duplicate_id_both_orders_and_tenants(self):
        records = [{'tenant': 'a', 'id': 'i', 'amount': 11}, {'tenant': 'b', 'id': 'i', 'amount': 22}]
        for ordered in (records, list(reversed(records))):
            for tenant, amount in [('a', 11), ('b', 22)]:
                with self.subTest(order=ordered, tenant=tenant):
                    self.lookup(ordered, tenant, 'i', amount)

    def test_other_tenant_only(self):
        self.lookup([{'tenant': 'b', 'id': 'i', 'amount': 22}], 'a', 'i', missing=True)

    def test_absent_id(self):
        self.lookup([{'tenant': 'a', 'id': 'i', 'amount': 11}], 'a', 'missing', missing=True)

    def test_joint_match_required(self):
        self.lookup([{'tenant': 'a', 'id': 'j', 'amount': 11}, {'tenant': 'b', 'id': 'i', 'amount': 22}], 'a', 'i', missing=True)

    def test_empty(self):
        self.lookup([], 'a', 'i', missing=True)

    def test_exact_identifier_equality(self):
        self.lookup([{'tenant': 'a', 'id': 7, 'amount': 11}], 'a', '7', missing=True)

if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(InvoiceContract))
    assert hashlib.sha256(SOURCE.read_text(encoding='utf-8').encode('utf-8')).hexdigest() == EXPECTED
    raise SystemExit(0 if result.wasSuccessful() else 1)


