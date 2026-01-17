from data_provider import YFinanceProvider
import json

provider = YFinanceProvider()
details = provider.get_ticker_details("AAPL")
print(json.dumps({k: v for k, v in details.items() if "target" in k}, indent=2))
