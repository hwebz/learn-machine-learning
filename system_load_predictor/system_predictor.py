import numpy as np
import pandas as pd

from sklearn.linear_model import LinearRegression, HuberRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

class SystemPredictor:
    def __init__(self, model_type='huber'):
        self.model_type = model_type
        self.scaler = StandardScaler()
        if model_type == 'huber':
            self.model = HuberRegressor(epsilon=1.35)
        else:
            self.model = LinearRegression()

    def _remove_outliners(self, df, column='CPU_Usage'):
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)

        IQR = Q3 - Q1
        return df[~((df[column] < (Q1 - 1.5 * IQR)) | (df[column] > (Q3 + 1.5 * IQR)))]

    def train(self, df, clean_data=True):
        if clean_data:
            df = self._remove_outliners(df)

        X = df[['RPS', 'Memory_MB', 'DB_Connections']]
        y = df['CPU_Usage']

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Fit scaler và transform dữ liệu
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Huấn luyện
        self.model.fit(X_train_scaled, y_train)

        # Đánh giá
        y_pred = self.model.predict(X_test_scaled)
        self.metrics = {
            "mse": mean_squared_error(y_test, y_pred),
            "r2": r2_score(y_test, y_pred),
            "model_type": self.model_type
        }
        return self.metrics
    
    def predict(self, rps, memory, db_conn):
        input_data = self.scaler.transform([[rps, memory, db_conn]])
        prediction = self.model.predict(input_data)[0]

        return float(np.clip(prediction, 0, 100))