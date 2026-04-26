# Nhập joblib để tải 'bộ não' (mô hình) đã lưu của chúng ta
import joblib
# Nhập pandas để định dạng dữ liệu đầu vào của ngôi nhà
import pandas as pd

# Nhập đường dẫn mô hình đã lưu và danh sách các đặc trưng cần thiết
from config import MODEL_PATH, NUMBERIC_FEATURES

def predict_one_house():
    """
    Sử dụng mô hình đã huấn luyện để dự đoán giá của một ngôi nhà cụ thể.
    """
    # 1. Tải mô hình đã lưu từ tệp tin
    model = joblib.load(MODEL_PATH)

    # 2. Định nghĩa chi tiết về ngôi nhà mà chúng ta muốn định giá
    # Hãy tưởng tượng một ngôi nhà rộng 120m2, 3 phòng ngủ, cách trung tâm 4km, 10 năm tuổi
    house_data = {
        "size_m2": 120,
        "bedrooms": 3,
        "distance_km": 4,
        "age_years": 10,
        "size_ft2": 120 * 10.7639 # Chuyển đổi m2 sang ft2 thủ công cho đầu vào
    }

    # 3. Chuyển đổi từ điển (dictionary) thành DataFrame (định dạng mà mô hình mong đợi)
    house_df = pd.DataFrame([house_data])

    # 4. Đảm bảo các cột nằm đúng thứ tự như khi chúng ta huấn luyện
    house_df = house_df[NUMBERIC_FEATURES]

    # 5. Yêu cầu mô hình đưa ra dự đoán
    # .predict() trả về một danh sách, vì vậy chúng ta lấy phần tử đầu tiên [0]
    prediction = model.predict(house_df)[0]

    # 6. Hiển thị kết quả
    print("--- Thông tin ngôi nhà đầu vào ---")
    print(house_df)
    print("\n" + "="*35)
    print(f"💰 GIÁ DỰ ĐOÁN: ${prediction:,.2f}")
    print("="*35)

if __name__ == "__main__":
    predict_one_house()
