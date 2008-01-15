import unittest

from mtmud.MudObjects import *

class MudObjectsTestCase(unittest.TestCase):
    def test_base(self):
        o = MudObject()
        self.assertEqual(o.__class__, MudObject)

if __name__ == '__main__':
    unittest.main()
