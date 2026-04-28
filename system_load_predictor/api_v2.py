from fastapi import FastAPI
from ai_model_engine import AIModelEngine
from prometheus_client import make_asgi_app

app = FastAPI(title="AI-Ops Engine v2.0")
engine = AIModelEngine()

# Gắn Prometheus vào FastAPI
prometheus_app = make_asgi_app()
app.mount("/metrics", prometheus_app)

@app.on_even("startup")
def startup_event():
    if not engine.load_prod_model():
        print("Không tìm thấy model có sẵn. Cần thực hiện training.")

@app.post("/predict")
def get_prediction(rps: float, mem: float, db: int):
    val = engine.predict(rps, mem, db)
    return {
        "predicted_cpu_usage": round(val, 2)
    }