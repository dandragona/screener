import requests
import time
import json
import statistics

def verify_streaming():
    url = "http://localhost:8000/screen"
    print(f"Connecting to {url}...")
    
    start_time = time.time()
    response = requests.get(url, stream=True)
    
    if response.status_code != 200:
        print(f"Failed to connect: {response.status_code}")
        print(response.text)
        return

    print("Connected! Reading stream...")
    
    count = 0
    arrival_times = []
    last_arrival = start_time
    
    # Read line by line
    for line in response.iter_lines():
        if line:
            current_time = time.time()
            decoded_line = line.decode('utf-8')
            try:
                data = json.loads(decoded_line)
                symbol = data.get("symbol", "UNKNOWN")
                
                diff = current_time - last_arrival
                arrival_times.append(diff)
                
                print(f"[{current_time - start_time:.3f}s] Received {symbol} (+{diff:.3f}s)")
                
                last_arrival = current_time
                count += 1
                
                # Stop after 10 to prove it works without waiting for all
                if count >= 10:
                    print("Received 10 symbols, stopping early for verification.")
                    break
            except json.JSONDecodeError:
                print(f"Received invalid JSON: {decoded_line}")

    if count == 0:
        print("No data received.")
    else:
        print(f"\nTotal received: {count}")
        if len(arrival_times) > 1:
            avg_diff = statistics.mean(arrival_times[1:]) # Skip first which includes connection time
            print(f"Average time between items: {avg_diff:.3f}s")
            
            # Simple heuristic: if they all arrive instantly (e.g. < 0.01s), it might not be streaming effectively 
            # OR the machine is just very fast/mocked.
            if avg_diff < 0.005:
                print("WARNING: Items arrived very, very fast. Verify if this is expected.")
            else:
                print("Streaming confirmed: items arrived with measurable delays.")

if __name__ == "__main__":
    verify_streaming()
