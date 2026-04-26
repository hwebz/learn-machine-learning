# 🏠 Dự Án Dự Đoán Giá Nhà (Housing Price Prediction)

Chào mừng bạn đến với dự án **Dự đoán giá nhà**! Đây là một dự án Máy học (Machine Learning) cơ bản dành cho người mới bắt đầu, nhằm trình bày quy trình làm việc đầy đủ của một dự án khoa học dữ liệu: từ tạo dữ liệu đến triển khai mô hình.

## 📖 Tổng quan dự án
Dự án này sử dụng thuật toán **Hồi quy Tuyến tính (Ridge)** để dự đoán giá thị trường của một ngôi nhà dựa trên một số đặc điểm. Chúng tôi sử dụng một bộ dữ liệu giả lập được tạo riêng cho dự án này để đảm bảo dữ liệu sạch sẽ và dễ học.

### 📊 Các đặc trưng được sử dụng (Đầu vào)
- **Diện tích (m²)**: Tổng diện tích ngôi nhà tính bằng mét vuông.
- **Phòng ngủ**: Số lượng phòng.
- **Khoảng cách (km)**: Khoảng cách từ ngôi nhà đến trung tâm thành phố.
- **Tuổi (năm)**: Tuổi đời của tòa nhà.
- **Diện tích (ft²)**: Diện tích tính bằng feet vuông (tương quan với m²).

### 🎯 Mục tiêu (Đầu ra)
- **Giá**: Giá trị thị trường ước tính tính bằng USD ($).

---

## 🛠️ Công nghệ sử dụng
- **Python 3.10+**
- **Pandas**: Để xử lý dữ liệu và bảng biểu.
- **NumPy**: Cho các phép toán và tạo dữ liệu ngẫu nhiên.
- **Scikit-Learn**: Thư viện cho các mô hình máy học và quy trình xử lý (pipelines).
- **Joblib**: Để lưu và tải "bộ não" của mô hình đã huấn luyện.

---

## 🚀 Cách chạy dự án

### 1. Tạo và kích hoạt môi trường ảo (Virtual Environment)
Việc tạo môi trường ảo giúp giữ cho các thư viện của dự án này không bị xung đột với các dự án khác trên máy tính của bạn.

**Trên Windows:**
```powershell
# Tạo môi trường ảo có tên là .venv
python -m venv .venv

# Kích hoạt môi trường ảo
.\.venv\Scripts\Activate.ps1
```

**Trên macOS/Linux:**
```bash
# Tạo môi trường ảo
python3 -m venv .venv

# Kích hoạt môi trường ảo
source .venv/bin/activate
```

### 2. Cài đặt thư viện
Sau khi đã kích hoạt môi trường ảo (bạn sẽ thấy chữ `(.venv)` ở đầu dòng lệnh), hãy cài đặt các thư viện cần thiết:
```bash
pip install -r requirements.txt
```

### 3. Tạo dữ liệu
Tạo bộ dữ liệu giả lập bằng cách chạy script:
```bash
python generate_data.py
```
Lệnh này sẽ tạo một tệp `data/housing.csv` với 500 dòng thông tin về nhà cửa.

### 4. Huấn luyện mô hình
Huấn luyện mô hình máy học bằng dữ liệu đã tạo:
```bash
python train.py
```
**Điều gì xảy ra ở đây?**
- Dữ liệu được tải và chia thành bộ **Huấn luyện (80%)** và bộ **Kiểm tra (20%)**.
- Một **Pipeline** được xây dựng để chuẩn hóa dữ liệu và đơn giản hóa đặc trưng (PCA).
- Mô hình được đánh giá bằng **Điểm R²** và **RMSE**.
- "Bộ não" được lưu vào `model/model.joblib`.

### 5. Thực hiện dự đoán (Script)
Sử dụng mô hình đã huấn luyện để dự đoán giá cho một ngôi nhà cụ thể thông qua script:
```bash
python predict.py
```

### 6. Triển khai API với FastAPI
Dự án này cũng cung cấp một giao diện API để bạn có thể tích hợp mô hình vào các ứng dụng web hoặc di động khác.

**Khởi chạy server API:**
```bash
uvicorn app.main:app --reload
```
Sau khi chạy, API sẽ mặc định hoạt động tại địa chỉ: `http://127.0.0.1:8000`

**Kiểm tra API bằng `curl`:**

1. **Kiểm tra trạng thái hệ thống (Health Check):**
```bash
curl http://127.0.0.1:8000/health
```

2. **Dự đoán giá nhà qua API:**
```bash
curl -X POST http://127.0.0.1:8000/predict ^
     -H "Content-Type: application/json" ^
     -d "{\"size_m2\": 120, \"bedrooms\": 3, \"distance_km\": 4, \"age_years\": 10, \"size_ft2\": 1291.668}"
```
*(Lưu ý: Nếu bạn dùng Linux/macOS, hãy thay dấu `^` bằng dấu `\` và bỏ các dấu backslash `\` trước dấu ngoặc kép trong chuỗi JSON nếu cần thiết tùy theo shell của bạn)*

**Tài liệu API tự động (Swagger UI):**
FastAPI tự động tạo tài liệu cho bạn. Hãy mở trình duyệt và truy cập:
- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 7. Đóng gói với Docker (Dockerization)
Bạn có thể đóng gói toàn bộ ứng dụng (bao gồm cả quy trình tạo dữ liệu, huấn luyện và chạy API) vào một Docker container để dễ dàng triển khai ở bất cứ đâu.

**Xây dựng Docker image:**
```bash
docker build -t housing-prediction .
```

**Chạy Docker container:**
```bash
docker run -p 8000:8000 housing-prediction
```
Khi chạy lệnh này, Docker sẽ tự động:
1. Cài đặt môi trường Python.
2. Cài đặt các thư viện cần thiết.
3. Chạy `generate_data.py` để tạo dữ liệu.
4. Chạy `train.py` để huấn luyện mô hình.
5. Khởi chạy FastAPI server trên cổng 8000.

Sau đó, bạn có thể truy cập API tại `http://localhost:8000` như bình thường.

---

## 📈 Giải thích kết quả
Khi bạn chạy `train.py`, bạn sẽ thấy hai con số quan trọng:

1. **Điểm R² (R-squared)**: 
   - Giá trị từ 0 đến 1.
   - Điểm **0.92** có nghĩa là mô hình giải thích được **92%** sự biến động của giá. Càng gần 1.0 thì mô hình càng tốt!
2. **RMSE (Root Mean Squared Error)**:
   - Đây là sai số trung bình của mô hình.
   - Nếu RMSE là **$50,000**, điều đó có nghĩa là trung bình các dự đoán của chúng ta bị lệch khoảng $50,000.

---

## 📂 Cấu trúc dự án
- `config.py`: Các cài đặt trung tâm và đường dẫn tệp.
- `generate_data.py`: Script để tạo bộ dữ liệu CSV.
- `train.py`: Logic huấn luyện Máy học cốt lõi.
- `predict.py`: Script để tải mô hình và kiểm tra một dự đoán duy nhất.
- `data/`: Thư mục chứa dữ liệu CSV.
- `model/`: Thư mục chứa tệp mô hình đã lưu.