# Stage 1: Build & Install dependencies
FROM python:3.11-slim AS builder

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy dependency và cài đặt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Stage 2: Runtime - Sử dụng base image nhẹ nhàng
FROM python:3.11-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy dependency và cài đặt
COPY --from=builder /root/.local /root/.local

# Copy toàn bộ code vào container Stage 2
COPY . .

# Cập nhật PATH để Python nhận diện các packages đã cài
ENV PATH=/root/.local/bin:$PATH

# Mở port cho FastAPI
EXPOSE 8000

# Lệnh chạy server
CMD ["uvicorn", "api_v2:app", "--host", "0.0.0.0", "--port", "8000"]