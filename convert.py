import os
import pandas as pd

parquet_dir = "tables"           
csv_output_dir = "csv_tables"
os.makedirs(csv_output_dir, exist_ok=True)

for filename in os.listdir(parquet_dir):
      if filename.endswith(".parquet"):
            table_name = filename.replace(".parquet", "")
            df = pd.read_parquet(os.path.join(parquet_dir, filename))
            df.to_csv(os.path.join(csv_output_dir, f"{table_name}.csv"), index=False)
            print(f"✅ Converted {filename} to {table_name}.csv")
