import math
from scipy.stats import norm

class OptionPricingModel:
    @staticmethod
    def black_scholes_call(S, K, T, r, sigma):
        """
        Calculate Black-Scholes price for a call option.
        S: Underlying Price
        K: Strike Price
        T: Time to Expiration (in years)
        r: Risk-free rate
        sigma: Implied Volatility
        """
        if T <= 0:
            return max(0, S - K)
            
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        call_price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
        return call_price

class IVEstimator:
    @staticmethod
    def impl_vol_call(market_price, S, K, T, r=0.05):
        """
        Calculate Implied Volatility for a call option using Newton-Raphson.
        """
        sigma = 0.5 # Initial guess
        max_iterations = 100
        precision = 1.0e-5

        for i in range(max_iterations):
            price = OptionPricingModel.black_scholes_call(S, K, T, r, sigma)
            diff = market_price - price
            
            if abs(diff) < precision:
                return sigma
                
            # Calculate Vega (sensitivity to volatility)
            d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            vega = S * norm.pdf(d1) * math.sqrt(T)
            
            if vega == 0:
                return None # Avoid division by zero
                
            sigma = sigma + diff / vega
            
        return sigma # Return best guess if not converged
