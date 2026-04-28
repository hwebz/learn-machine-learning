# AI-Ops Lab: Dự đoán tải hệ thống (System Load Predictor)

Chào bạn! Để "phá đảo" bài toán này trên local, chúng ta sẽ xây dựng một **AI-Ops Lab** thu nhỏ. Lộ trình của chúng ta sẽ đi từ việc dựng hạ tầng (Minikube), cài đặt "mắt thần" (Prometheus/Grafana), cho đến việc tạo một con Bot "quậy phá" để sinh dữ liệu.

---

## 🏗️ Bước 1: Chuẩn bị "Đại bản doanh" (Minikube & Docker)

Đầu tiên, hãy khởi động Minikube. Một mẹo nhỏ cho dân chuyên là sử dụng chính Docker daemon của Minikube để build image, tránh việc phải push lên Docker Hub mất thời gian.

```bash
# Khởi động Minikube
minikube start

# "Trỏ" terminal vào Docker của Minikube
eval $(minikube docker-env)
```

---

## 🚀 Bước 2: Build Image cho AI-Ops Engine

Hãy build image ngay trên local:
```bash
docker build -t ai-ops-engine:v2.0 .
```

Sau đó, triển khai lên k8s bằng file `deployment.yml`:
```bash
kubectl apply -f deployment.yml
```

---

## 📊 Bước 3: Cài đặt "Mắt thần" (Prometheus & Grafana)

Cách nhanh nhất và chuẩn nhất hiện nay là dùng **Helm**. Nếu bạn chưa có Helm, hãy cài đặt nó trước.

### 3.1. Cài đặt Prometheus & Grafana qua Helm Chart
```bash
# Thêm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Cài đặt toàn bộ stack (bao gồm cả Prometheus và Grafana)
helm install monitoring prometheus-community/kube-prometheus-stack
```

### 3.2. Cấu hình Prometheus nhận diện App của bạn
Trong file `deployment.yml` hiện tại, phần metadata để Prometheus "cào" dữ liệu đã được cấu hình sẵn rất chuẩn, bạn không cần phải thêm nữa:
```yaml
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/path: "/metrics"
    prometheus.io/port: "8000"
```

---

## 🤖 Bước 4: Tạo "Data Faker" (Workload Simulator)

Trong thư mục đã có sẵn file `faker_app.py` với nội dung được đồng bộ chuẩn xác với API như sau:

```python
import requests
import time
import random

API_URL = "http://localhost:8000/predict" # Sau khi port-forward

def simulate_workload():
    while True:
        # Giả lập dữ liệu ngẫu nhiên nhưng có quy luật
        payload = {
            "rps": random.uniform(100, 2000),
            "mem": random.uniform(1024, 8192),
            "db": random.randint(20, 200)
        }
        try:
            # Sử dụng params=payload cho API
            response = requests.post(API_URL, params=payload)
            result = response.json()
            print(f"Sent: {payload} -> Predicted CPU: {result.get('predicted_cpu_usage', 'N/A')}%")
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(1) # Gửi mỗi giây 1 request

if __name__ == "__main__":
    simulate_workload()
```

---

## 🔗 Bước 5: Kết nối các dấu chấm (Wiring everything)

Bây giờ là lúc "lên đèn" cho hệ thống:

**1. Mở cổng để truy cập vào App và Grafana từ máy local:**
```bash
# Mở cổng cho AI App (Terminal 1)
kubectl port-forward svc/predictor-service 8000:8000

# Mở cổng cho Grafana (Terminal 2)
kubectl port-forward svc/monitoring-grafana 3000:80
```

**2. Truy cập Grafana:**
* Địa chỉ: `http://localhost:3000`
* User: `admin` / Pass: `prom-operator` (mặc định của Helm chart).

**3. Tạo Dashboard:**
* Vào mục **Explore**, chọn source là **Prometheus**.
* Gõ query: `cpu_usage_predicted` (đây là metric đã được định nghĩa chuẩn xác trong `ai_model_engine.py`).
* Bạn sẽ thấy biểu đồ CPU nhảy múa theo dữ liệu từ con Bot `faker_app.py` đang gửi lên.

---

## 🎯 Tổng kết Lab của bạn

Bây giờ bạn đã có một hệ sinh thái hoàn chỉnh:
* **Hạ tầng:** Minikube.
* **Ứng dụng:** FastAPI AI Engine (Predictor).
* **Giả lập:** Python Faker script.
* **Quan trắc:** Prometheus & Grafana.

> **Gợi ý cực "hay ho":** Bạn hãy thử vào file `faker_app.py`, tăng vọt thông số `rps` lên mức 5000, sau đó quan sát biểu đồ trên Grafana. Bạn sẽ thấy đường dự đoán CPU vọt lên. Đây chính là cách các kỹ sư DevOps thiết lập **Alerting** — nếu `cpu_usage_predicted > 80%` trong 1 phút, hãy bắn tin nhắn về Telegram ngay lập tức!

Bạn có gặp khó khăn ở bước "port-forward" hay cấu hình Grafana không? Cứ hỏi, mình sẽ cùng bạn fix!
