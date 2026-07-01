FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Ensure model + scaler are included inside the image
COPY models/lstm_model.h5 /app/models/lstm_model.h5
COPY models/scaler.pkl /app/models/scaler.pkl

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
