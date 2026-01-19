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

    @staticmethod
    def black_scholes_put(S, K, T, r, sigma):
        """
        Calculate Black-Scholes price for a put option.
        """
        if T <= 0:
            return max(0, K - S)
            
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        put_price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        return put_price

class IVEstimator:
    @staticmethod
    def impl_vol_call(market_price, S, K, T, r=0.05):
        """
        Calculate Implied Volatility for a call option using Newton-Raphson.
        """
        return IVEstimator._impl_vol_generic(market_price, S, K, T, r, is_call=True)

    @staticmethod
    def impl_vol_put(market_price, S, K, T, r=0.05):
        """
        Calculate Implied Volatility for a put option using Newton-Raphson.
        """
        return IVEstimator._impl_vol_generic(market_price, S, K, T, r, is_call=False)

    @staticmethod
    def _impl_vol_generic(market_price, S, K, T, r, is_call):
        sigma = 0.5 # Initial guess
        max_iterations = 100
        precision = 1.0e-5

        if T <= 0:
            return None

        for i in range(max_iterations):
            if is_call:
                price = OptionPricingModel.black_scholes_call(S, K, T, r, sigma)
            else:
                price = OptionPricingModel.black_scholes_put(S, K, T, r, sigma)
                
            diff = market_price - price
            
            if abs(diff) < precision:
                return sigma
                
            # Calculate Vega (same for Call and Put)
            try:
                d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
                vega = S * norm.pdf(d1) * math.sqrt(T)
            except ValueError:
                # Math domain error or overflow
                return None
            
            if vega < 1.0e-8:
                return None # Avoid division by zero or overflow
                
                
            sigma = sigma + diff / vega
            
            # Clamp sigma to prevent overflow and negative values
            if sigma <= 0:
                sigma = 0.001
            elif sigma > 20: # Cap at 2000% volatility
                sigma = 20
            
        return sigma
