import pytest
import math
from options_lib import OptionPricingModel, IVEstimator

class TestOptionPricingModel:
    def test_black_scholes_call_basic(self):
        # Known value: S=100, K=100, T=1, r=0.05, sigma=0.2
        # Online calculators give ~10.45
        price = OptionPricingModel.black_scholes_call(100, 100, 1, 0.05, 0.2)
        assert math.isclose(price, 10.45, rel_tol=0.01)

    def test_black_scholes_call_expired(self):
        # T=0, S=110, K=100 -> intrinsic value 10
        price = OptionPricingModel.black_scholes_call(110, 100, 0, 0.05, 0.2)
        assert price == 10

    def test_black_scholes_call_otm_expired(self):
        # T=0, S=90, K=100 -> 0
        price = OptionPricingModel.black_scholes_call(90, 100, 0, 0.05, 0.2)
        assert price == 0

class TestIVEstimator:
    def test_impl_vol_call_basic(self):
        # Reverse the BS calculation
        # If sigma=0.2 gives price ~10.4506
        target_price = 10.4506
        sigma = IVEstimator.impl_vol_call(target_price, 100, 100, 1, 0.05)
        # Should converge close to 0.2
        assert math.isclose(sigma, 0.2, rel_tol=0.01)

    def test_impl_vol_call_low_vol(self):
        # S=100, K=100, T=1, r=0.05, sigma=0.05
        # Price ~ 5.63
        target_price = 5.2833
        sigma = IVEstimator.impl_vol_call(target_price, 100, 100, 1, 0.05)
        assert math.isclose(sigma, 0.05, rel_tol=0.1)
