import requests
import pandas as pd

# Mengambil data harga harian Bitcoin selama 365 hari terakhir
url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=365&interval=daily"
response = requests.get(url)
data = response.json()

# Mengubah data ke pandas DataFrame
prices = data['prices']
df = pd.DataFrame(prices, columns=['timestamp', 'price'])
df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
df['month'] = df['date'].dt.month_name()
df['day_of_week'] = df['date'].dt.day_name()

# Menghitung rerata harga berdasarkan hari dalam seminggu
seasonal_pattern = df.groupby('day_of_week')['price'].mean()
print(seasonal_pattern)