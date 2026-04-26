from pydantic import BaseModel, Field

# FastAPI dùng Pydantic để định nghĩa cấu trúc dữ liệu đầu vào và đầu ra
# đồng thời để validate dữ liệu in/out rất tiện
# và tự động sinh ra API documentation (Swagger UI)
class HouseFeatures(BaseModel):
    size_m2: float = Field(..., gt=0, description="Dien tich nha theo m2")
    bedrooms: int = Field(..., ge=0, le=20, description="So phong ngu")
    distance_km: float = Field(..., ge=0, description="Khoang cach toi trung tam")
    age_years: int = Field(..., ge=0, description="Tuoi can nha")
    size_ft2: float = Field(..., ge=0, description="Dien tich theo ft2")

class PredictionResponse(BaseModel):
    predicted_price: float
    currency: str = "USD"