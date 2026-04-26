# Nhập thư viện numpy để thực hiện các phép toán và tạo số ngẫu nhiên
import numpy as np
# Nhập thư viện pandas để làm việc với dữ liệu dưới dạng bảng (DataFrame)
import pandas as pd

# Nhập đường dẫn dữ liệu nơi chúng ta muốn lưu tệp tin đã tạo
from config import DATA_PATH

def generate_data(n_samples=500, random_state=42):
    """
    Tạo một bộ dữ liệu giả lập về các ngôi nhà để thực hành máy học.
    
    Tham số:
        n_samples: Số lượng ngôi nhà muốn tạo (mặc định là 500)
        random_state: Một hạt giống (seed) để đảm bảo kết quả ngẫu nhiên là giống nhau mỗi khi chạy
    """
    # Khởi tạo bộ tạo số ngẫu nhiên
    rng = np.random.default_rng(random_state)

    # 1. Tạo các đặc trưng ngẫu nhiên cho mỗi ngôi nhà:
    # Diện tích ngẫu nhiên từ 30 đến 220 mét vuông
    size_m2 = rng.uniform(30, 220, n_samples)
    # Số phòng ngủ ngẫu nhiên từ 1 đến 6
    bedrooms = rng.integers(1, 7, n_samples)
    # Khoảng cách từ trung tâm thành phố ngẫu nhiên từ 1 đến 25 km
    distance_km = rng.uniform(1, 25, n_samples)
    # Tuổi của ngôi nhà ngẫu nhiên từ 0 đến 40 năm
    age_years = rng.uniform(0, 40, n_samples)

    # 2. Tạo một đặc trưng 'dư thừa' (diện tích tính bằng feet vuông)
    # Chúng ta nhân m2 với 10.764 và cộng thêm một chút nhiễu ngẫu nhiên
    size_ft2 = size_m2 * 10.764 + rng.normal(0, 50, n_samples)

    # 3. Tạo một chút 'nhiễu' (noise) để dữ liệu trông thực tế hơn
    # Trong thế giới thực, giá cả không bao giờ được dự đoán chính xác hoàn toàn
    noise = rng.normal(0, 30000, n_samples)

    # 4. Tính toán 'giá' bằng một công thức toán học (Logic bí mật)
    # Chúng ta giả định: 
    # + $3000 cho mỗi m2
    # + $18000 cho mỗi phòng ngủ
    # - $5500 cho mỗi km cách xa trung tâm
    # - $2200 cho mỗi năm tuổi của nhà
    price = (
        3000 * size_m2
        + 18000 * bedrooms
        - 5500 * distance_km
        - 2200 * age_years
        + noise
    )

    # 5. Đưa tất cả các danh sách này vào một Bảng (DataFrame)
    df = pd.DataFrame({
        "size_m2": size_m2,
        "bedrooms": bedrooms,
        "distance_km": distance_km,
        "age_years": age_years,
        "size_ft2": size_ft2,
        "price": price
    })

    # 6. Lưu dữ liệu vào tệp CSV
    # Đảm bảo thư mục lưu trữ đã tồn tại
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Lưu bảng mà không kèm theo số thứ tự dòng (index=False)
    df.to_csv(DATA_PATH, index=False)

    print(f"--- Đã lưu thành công {n_samples} ngôi nhà vào: {DATA_PATH} ---")
    # Hiển thị 5 dòng đầu tiên để kiểm tra xem dữ liệu có đúng không
    print(df.head())


# Khối mã này chỉ chạy nếu chúng ta thực thi trực tiếp tệp này
if __name__ == "__main__":
    generate_data()
