import pandas as pd

df = pd.read_csv("all_instrument 2025-09-02.csv")

print("=== Columns in file ===")
print(df.columns.tolist())

print("\n=== First 5 rows ===")
print(df.head())

