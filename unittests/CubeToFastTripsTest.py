import sys, os, unittest

# test this version of Wrangler
curdir = os.path.dirname(__file__)
sys.path.insert(1, os.path.normpath(os.path.join(curdir, "..", "..")))

import Wrangler

class TestCubeToFastTrips(unittest.TestCase):
    def setUp(self):