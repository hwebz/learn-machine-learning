# Sử dụng base image nhẹ nhàng
FROM python:3.11-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy dependency và cài đặt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code vào container
COPY . .

# Mở port cho FastAPI
EXPOSE 8000

# Lệnh chạy server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]