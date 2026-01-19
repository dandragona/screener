import sys
import os
import unittest
import math

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from options_lib import IVEstimator, OptionPricingModel

class TestIVCalculation(unittest.TestCase):
    def test_call_iv(self):
        # Known Black-Scholes values
        S = 100
        K = 100
        T = 1.0 # 1 year
        r = 0.05
        sigma_true = 0.30
        
        # Calculate price with true sigma
        price = OptionPricingModel.black_scholes_call(S, K, T, r, sigma_true)
        
        # Back out IV
        iv_calc = IVEstimator.impl_vol_call(price, S, K, T, r)
        
        self.assertAlmostEqual(iv_calc, sigma_true, places=4)

    def test_put_iv(self):
        # Known Black-Scholes values
        S = 100
        K = 100
        T = 1.0 # 1 year
        r = 0.05
        sigma_true = 0.30
        
        # Calculate price with true sigma
        price = OptionPricingModel.black_scholes_put(S, K, T, r, sigma_true)
        
        # Back out IV
        iv_calc = IVEstimator.impl_vol_put(price, S, K, T, r)
        
        self.assertAlmostEqual(iv_calc, sigma_true, places=4)

    def test_itm_contracts(self):
        # Test ITM Call
        S = 120
        K = 100
        T = 0.5
        r = 0.05
        sigma = 0.25
        
        price = OptionPricingModel.black_scholes_call(S, K, T, r, sigma)
        iv = IVEstimator.impl_vol_call(price, S, K, T, r)
        self.assertAlmostEqual(iv, sigma, places=4)

    def test_otm_contracts(self):
        # Test OTM Put
        S = 120
        K = 100
        T = 0.5
        r = 0.05
        sigma = 0.25
        
        price = OptionPricingModel.black_scholes_put(S, K, T, r, sigma)
        iv = IVEstimator.impl_vol_put(price, S, K, T, r)
        self.assertAlmostEqual(iv, sigma, places=4)

if __name__ == '__main__':
    unittest.main()
