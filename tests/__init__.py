import unittest
from tests.pySDC.__init__ import *

class pySDCTestSuite( unittest.TestSuite ):
    def __init__( self ):
        self.addTests( pySDCTests() )

if __name__ == "__main__":
    unittest.main()
