import requests

url = "http://127.0.0.1:8080/predict"
data = {"tickers": ["SPY", "AAPL", "QQQ"]}

response = requests.post(url, json=data)
print(response.json())
