from config import LOGS_PATH
import logging
from datetime import datetime
from contextlib import asynccontextmanager

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException

from app.schemas import HouseFeatures, PredictionResponse
from config import MODEL_PATH, NUMBERIC_FEATURES

# Đảm bảo thư mục chứa logs tồn tại trước khi thiết lập logging
LOGS_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOGS_PATH, encoding='utf-8'),
        logging.StreamHandler(),
    ]
)

model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model

    logging.info("Loading model...")

    if not MODEL_PATH.exists():
        raise RuntimeError(f"Model file not found at {MODEL_PATH}. Run `python train.py` first.")
    
    model = joblib.load(MODEL_PATH)
    logging.info("Model loaded successfully.")

    yield
    logging.info("Shutting down API...")

app = FastAPI(
    title="Housing Price Prediction API",
    description="API du doan gia nha bang scikit-learn Pipeline",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "model_loaded": model is not None
    }

@app.get("/model-info")
def model_info():
    model_info = {
        "model_type": model.__class__.__name__,
        "features": NUMBERIC_FEATURES,
        "path": str(MODEL_PATH.resolve()),
    }
    print(model)

    return model_info

@app.post("/predict", response_model=PredictionResponse)
def predict(features: HouseFeatures):
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded")

    input_df = pd.DataFrame([features.model_dump()])[NUMBERIC_FEATURES]
    input_df = input_df[NUMBERIC_FEATURES]

    try:
        prediction = model.predict(input_df)[0]
        now = datetime.now()
        logging.info(f"[{now}] Prediction for {features}: {prediction}")
    except Exception as e:
        logging.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=str(e))

    return PredictionResponse(
        predicted_price=float(prediction),
        currency="USD"
    )

@app.post("/predict-batch", response_model=list[PredictionResponse])
def predict_batch(list_features: list[HouseFeatures]):
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded")

    input_df = pd.DataFrame([features.model_dump() for features in list_features])[NUMBERIC_FEATURES]
    input_df = input_df[NUMBERIC_FEATURES]

    try:
        predictions = model.predict(input_df)
        now = datetime.now()
        logging.info(f"[{now}] Batch prediction for {list_features}: {predictions}")
    except Exception as e:
        logging.exception("Batch prediction failed")
        raise HTTPException(status_code=500, detail=str(e))

    results = [
        PredictionResponse(
            # Neu gia du doan < 0 thi tra ve 0
            predicted_price=float(prediction) if float(prediction) > 0 else 0,
            currency="USD"
        ) for prediction in predictions
    ]

    return results