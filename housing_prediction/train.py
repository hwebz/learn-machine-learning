# Nhập các công cụ cần thiết từ thư viện sklearn (scikit-learn) cho Máy học
import logging
import joblib
import numpy as np
import pandas as pd

# Các công cụ để xây dựng một 'công thức' huấn luyện (Pipeline)
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Nhập các cài đặt của chúng ta từ tệp config
from config import (
    DATA_PATH,
    MODEL_PATH,
    TARGET,
    NUMBERIC_FEATURES,
    TEST_SIZE,
    RANDOM_STATE
)

# Thiết lập ghi log để in ra các thông báo hữu ích khi mã chạy
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def load_data():
    """
    Đọc dữ liệu nhà từ tệp CSV và tách riêng các đặc trưng và mục tiêu.
    """
    # Tải tệp CSV vào một bảng (DataFrame)
    df = pd.read_csv(DATA_PATH)

    # Kiểm tra xem tất cả các cột yêu cầu có thực sự tồn tại trong tệp không
    missing_cols = set(NUMBERIC_FEATURES + [TARGET]) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Ối! Thiếu cột trong tệp CSV: {missing_cols}")

    # X = Dữ liệu đầu vào (các đặc trưng như diện tích, số phòng ngủ, v.v.)
    X = df[NUMBERIC_FEATURES]
    # y = Kết quả chúng ta muốn dự đoán (giá nhà)
    y = df[TARGET]

    return X, y

def build_pipeline(use_pca: bool = True):
    """
    Tạo một 'Pipeline' (đường ống), đây là một chuỗi các bước áp dụng cho dữ liệu.
    Hãy tưởng tượng nó như một dây chuyền lắp ráp trong nhà máy.
    """
    
    # BƯỚC 1: Tiền xử lý (Preprocessing)
    # Chúng ta sử dụng StandardScaler để đưa tất cả các con số về dạng 'có thể so sánh được'. 
    # Ví dụ: nó giúp 'diện tích' (số lớn) không lấn át 'số phòng ngủ' (số nhỏ).
    preprocessing = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMBERIC_FEATURES),
        ],
        remainder="drop" # Bỏ qua bất kỳ cột nào mà chúng ta không chỉ định
    )

    # Bắt đầu danh sách các bước trong dây chuyền lắp ráp
    steps = [
        ("preprocessing", preprocessing)
    ]

    # BƯỚC 2: Giảm chiều dữ liệu (Tùy chọn)
    # PCA (Phân tích thành phần chính) giúp đơn giản hóa dữ liệu bằng cách kết hợp các đặc trưng tương tự.
    # Vì chúng ta có cả size_m2 và size_ft2 (gần như giống nhau), PCA giúp loại bỏ sự dư thừa.
    if use_pca:
        steps.append(("pca", PCA(n_components=3)))

    # BƯỚC 3: Bộ não (Mô hình)
    # Ridge là một loại Hồi quy Tuyến tính giúp mô hình 'ổn định' và tránh học vẹt (overfitting).
    steps.append(("model", Ridge(alpha=1.0)))

    # Kết nối tất cả các bước thành một đối tượng Pipeline duy nhất
    pipeline = Pipeline(steps=steps)
    return pipeline

def evaluate_model(model, X_test, y_test):
    """
    Tính toán xem mô hình chính xác đến mức nào bằng cách sử dụng dữ liệu nó chưa từng thấy.
    """
    # Yêu cầu mô hình đoán giá cho những ngôi nhà trong bộ kiểm tra
    y_pred = model.predict(X_test)

    # RMSE (Sai số bình phương trung bình căn): Khoảng cách trung bình giữa dự đoán và thực tế (Càng thấp càng tốt)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    
    # R2 Score: Tỷ lệ phần trăm sự biến động của giá được giải thích bởi mô hình (1.0 là hoàn hảo)
    r2 = r2_score(y_test, y_pred)

    return rmse, r2

def main():
    # 1. Tải dữ liệu
    logging.info("Bước 1: Đang tải dữ liệu từ CSV....")
    X, y = load_data()

    # 2. Chia dữ liệu
    # Chúng ta giữ lại một phần dữ liệu (TEST_SIZE = 20%) để kiểm tra mô hình sau này.
    logging.info("Bước 2: Đang chia dữ liệu thành bộ Huấn luyện (80%) và bộ Kiểm tra (20%)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    # 3. Tạo công thức
    logging.info("Bước 3: Đang xây dựng dây chuyền máy học (Pipeline)...")
    model = build_pipeline(use_pca=True)

    # 4. Kiểm tra chéo (Cross-Validation)
    # Chúng ta thử nghiệm công thức nhiều lần trên các phần nhỏ khác nhau của dữ liệu huấn luyện
    # để đảm bảo kết quả là ổn định.
    logging.info("Bước 4: Đang chạy kiểm tra chéo để kiểm tra độ ổn định...")
    cv_scores = cross_val_score(
        model, X_train, y_train, cv=5, scoring="r2"
    )

    logging.info(f"--- Điểm R2 kiểm tra chéo: {cv_scores}")
    logging.info(f"--- Điểm R2 trung bình: {cv_scores.mean():.4f}")

    # 5. Huấn luyện cuối cùng
    # Bây giờ chúng ta huấn luyện mô hình trên TẤT CẢ dữ liệu huấn luyện.
    logging.info("Bước 5: Đang huấn luyện mô hình cuối cùng trên bộ huấn luyện...")
    model.fit(X_train, y_train)

    # 6. Kiểm tra cuối cùng
    # Nó hoạt động tốt thế nào trên 20% dữ liệu mà nó chưa bao giờ thấy?
    rmse, r2 = evaluate_model(model, X_test, y_test)

    logging.info("Bước 6: Kết quả kiểm tra cuối cùng:")
    logging.info(f"--- RMSE: ${rmse:,.2f} (Sai số trung bình trên mỗi căn nhà)")
    logging.info(f"--- Điểm R2: {r2:.4f} (Độ chính xác {r2 * 100:.2f}%)")

    # 7. Lưu bộ não
    # Chúng ta lưu pipeline đã huấn luyện (công thức + mô hình) vào một tệp để có thể sử dụng sau này mà không cần huấn luyện lại.
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    logging.info(f"Bước 7: Mô hình đã được lưu thành công tại {MODEL_PATH}")

if __name__ == "__main__":
    main()
