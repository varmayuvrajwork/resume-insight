import os
import pandas as pd

class DataLoader:
      def __init__(self, csv_dir="csv_tables"):
            self.csv_dir = os.path.abspath(csv_dir)
            self.tables = {}
            self.schema_map = {}
            self.priority_tables = ["worker_attachment"]
            self.load_tables()

      def load_tables(self):
            for filename in os.listdir(self.csv_dir):
                  if filename.endswith(".csv"):
                        table_name = filename.replace(".csv", "")
                  try:
                        df = pd.read_csv(os.path.join(self.csv_dir, filename), low_memory=False)
                        self.tables[table_name] = df
                        self.schema_map[table_name] = list(df.columns)
                  except Exception as e:
                        print(f"❌ Error loading {filename}: {e}")

      def get_table(self, name):
            return self.tables.get(name)

      def get_all_tables(self):
            return self.tables

      def get_schema_map(self):
            return self.schema_map

      def get_priority_tables(self):
            return self.priority_tables
