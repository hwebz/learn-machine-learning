from system_predictor import SystemPredictor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
import pandas as pd
import uvicorn

app = FastAPI(title="System Load Predictor API")

# Khởi tạo model sẵn (trong thực tế có thể load dữ liệu từ file .pkl)
# Ở đây ta giả lập dữ liệu để train ngay khi khởi động
predictor = SystemPredictor(model_type='huber')

# Giả lập dữ liệu huấn luyện
raw_data = pd.DataFrame({
    'RPS': np.random.randint(100, 2000, 500),
    'Memory_MB': np.random.randint(1024, 8192, 500),
    'DB_Connections': np.random.randint(20, 200, 500),
    'CPU_Usage': np.random.uniform(10, 90, 500)
})
predictor.train(raw_data)

class PredictionRequest(BaseModel):
    rps: float
    memory_mb: float
    db_connections: float

class ComparisonResponse(BaseModel):
    standard_lr_r2: float
    huber_r2: float

@app.get("/")
def read_root():
    return {
        "message": "AI System Predictor is running",
        "metrics": predictor.metrics
    }

@app.post("/predict")
def predict_cpu(data: PredictionRequest):
    try:
        cpu_val = predictor.predict(
            data.rps,
            data.memory_mb,
            data.db_connections
        )
        return {
            "predicted_cpu_usage": round(cpu_val, 2),
            "model_used": predictor.model_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/compare")
def compare_models():
    # Model Standard
    std_p = SystemPredictor(model_type='standard')
    m1 = std_p.train(raw_data, clean_data=False)

    # Model Huber + Clean
    h_p = SystemPredictor(model_type='huber')
    m2 = h_p.train(raw_data, clean_data=True)

    return {
        "standard_no_clean": m1,
        "huber_with_clean": m2,
        "verdict": "Huber is better" if m2["r2"] > m1["r2"] else "Standard is better"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)