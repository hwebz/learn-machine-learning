import joblib
import numpy as np 
from sklearn.linear_model import HuberRegressor
from sklearn.preprocessing import StandardScaler
from prometheus_client import Gauge

# Định nghĩa các chỉ số cho Prometheus
MODEL_ACCURACY = Gauge("model_r2_score", "R2 score of the current running model")
CPU_PREDICTION = Gauge("cpu_usage_predicted", "Predicted CPU Usage percentage")

MODEL_PATH = "/models/prod_model.pkl"
SCALER_PATH = "/models/scaler.pkl"

class AIModelEngine:
    def __init__(self, model_path=MODEL_PATH, scaler_path=SCALER_PATH):
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.model = None
        self.scaler = StandardScaler()

    def train_and_save(self, df):
        # Logic làm sạch dữ liệu
        Q1, Q3 = df['CPU_Usage'].quantile([0.25, 0.75])
        iqr = Q3 - Q1
        df_clean = df[
            ~((df['CPU_Usage'] < (Q1 - 1.5*iqr)) | (df['CPU_Usage'] > (Q3 + 1.5*iqr)))
        ]

        X = df_clean[['RPS', 'Memory_MB', 'DB_Connections']]
        y = df_clean['CPU_Usage']

        X_scaled = self.scaler.fit_transform(X)
        self.model = HuberRegressor().fit(X_scaled, y)

        # Lưu lại để dùng cho lần sau (Persistance)
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)

        # Cập nhật Prometheus metric
        score = self.model.score(X_scaled, y)
        MODEL_ACCURACY.set(score)
        return score

    def load_prod_model(self):
        try:
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            return True
        except:
            return False

    def predict(self, rps, memory, db_conn):
        if not self.model: return 0.0
        X_scaled = self.scaler.transform([[rps, memory, db_conn]])
        pred = self.model.predict(X_scaled)[0]
        val = float(np.clip(pred, 0, 100))
        CPU_PREDICTION.set(val)
        return val

    
    