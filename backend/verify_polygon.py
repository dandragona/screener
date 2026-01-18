from data_provider import HybridProvider, PolygonProvider
from config import POLYGON_API_KEY
import sys

def verify_polygon():
    print(f"Checking API Key... {POLYGON_API_KEY[:4]}***")
    
    try:
        poly = PolygonProvider()
        print("PolygonProvider initialized.")
        
        # Test Config Check
        # User only has Options API. 
        # Test: Fetch contracts for TSLA
        print("Fetching TSLA Option Contracts...")
        
        # v3/reference/options/contracts
        params = {
            "underlying_ticker": "TSLA",
            "limit": 1
        }
        res = poly._get_json("/v3/reference/options/contracts", params)
        
        results = res.get("results")
        if not results:
             print("FAILED: No contracts found. Key might be invalid.")
             print(f"Response: {res}")
             sys.exit(1)
             
        
        # Test 2: Hybrid IV Rank Calculation
        print("\nTesting Hybrid Provider IV Rank (YF Stock + Poly Options)...")
        hybrid = HybridProvider()
        metrics = hybrid.get_advanced_metrics("TSLA")
        
        print("Metrics Result:")
        print(f"IV Rank: {metrics.get('iv_rank')}")
        print(f"IV Short: {metrics.get('iv_short')}")
        
        if metrics.get('iv_rank') is not None:
             print("SUCCESS: IV Rank calculated!")
        else:
             print("WARNING: IV Rank is None (might be missing history or valid options)")
             
        print("SUCCESS: Hybrid Verification Complete.")
        
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_polygon()
