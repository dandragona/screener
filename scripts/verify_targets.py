import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from backend.data_provider import YFinanceProvider
import json

provider = YFinanceProvider()
details = provider.get_ticker_details("AAPL")
print(json.dumps({k: v for k, v in details.items() if "target" in k}, indent=2))
