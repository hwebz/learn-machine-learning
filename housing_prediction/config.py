# Nhập lớp Path từ thư viện pathlib để xử lý đường dẫn tệp tin một cách dễ dàng
from pathlib import Path

# Lấy đường dẫn tuyệt đối đến thư mục chứa tệp hiện tại (config.py)
# .resolve() giúp lấy đường dẫn đầy đủ, .parent giúp đi ngược lên một cấp thư mục
BASE_DIR = Path(__file__).resolve().parent

# Định nghĩa đường dẫn đến tệp dữ liệu (housing.csv) nằm trong thư mục "data"
# Sử dụng toán tử / là cách viết sạch sẽ để nối các đường dẫn trong Python
DATA_PATH = BASE_DIR / "data" / "housing.csv"

# Định nghĩa nơi sẽ lưu trữ mô hình máy học sau khi đã được huấn luyện
MODEL_PATH = BASE_DIR / "model" / "model.joblib"

# Tên của cột mà chúng ta muốn dự đoán (đây là "mục tiêu" hoặc "nhãn")
TARGET = "price"

# Danh sách tên các cột chứa thông tin số của ngôi nhà
# Đây là các "đặc trưng" (features) hoặc "đầu vào" dùng để dự đoán giá
NUMBERIC_FEATURES = [
    "size_m2",      # Diện tích nhà tính bằng mét vuông
    "bedrooms",     # Số lượng phòng ngủ
    "distance_km",  # Khoảng cách từ trung tâm thành phố tính bằng km
    "age_years",    # Tuổi đời của ngôi nhà tính theo năm
    "size_ft2",     # Diện tích nhà tính bằng feet vuông (được tính từ m2)
]

# Chúng ta sẽ dành ra 20% dữ liệu để kiểm tra xem mô hình học tốt đến mức nào
TEST_SIZE = 0.2

# Một con số "hạt giống" để đảm bảo các thao tác ngẫu nhiên (như chia dữ liệu)
# luôn cho ra cùng một kết quả mỗi khi chúng ta chạy mã
RANDOM_STATE = 42
