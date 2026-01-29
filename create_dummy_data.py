import pandas as pd
import numpy as np

# Create Dummy Sales Data
dates = pd.date_range(start="2023-01-01", periods=100)
sales = np.random.randint(100, 1000, size=100)
regions = np.random.choice(['North', 'South', 'East', 'West'], size=100)

df = pd.DataFrame({'Date': dates, 'Sales': sales, 'Region': regions})
df.to_csv('sales_data.csv', index=False)

print("Created sales_data.csv")
