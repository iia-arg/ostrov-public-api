import unittest
class PublicImport(unittest.TestCase):
 def test_documented_import_exposes_working_client(self):
  from ostrov_api import Client
  self.assertEqual(Client().base,'https://ostrov.center/api/public/v1')
