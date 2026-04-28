import requests
import time
import random

API_URL = "http://localhost:8000/predict"

def simulate_workload():
    while True:
        # Giả lập dữ liệu ngẫu nhiên nhưng có quy luật
        payload = {
            "rps": random.uniform(100, 2000),
            "mem": random.uniform(1024, 8192),
            "db": random.randint(20, 200),
        }

        try:
            response = requests.post(API_URL, params=payload)
            result = response.json()
            print(f"Sent: {payload} -> Predicted CPU: {result.get('predicted_cpu_usage', 'N/A')}%")
        except Exception as e:
            print(f"Error: {str(e)}")

        # Gửi mỗi request/1s
        time.sleep(1) 

if __name__ == "__main__":
    simulate_workload()