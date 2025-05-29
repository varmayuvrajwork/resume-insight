import re
import csv
import os
import pandas as pd
import sqlparse
from collections import defaultdict

def parse_sql_to_parquet_relaxed(sql_file_path, output_dir="tables"):
      os.makedirs(output_dir, exist_ok=True)

      with open(sql_file_path, "r", encoding="utf-8", errors="ignore") as f:
            sql_text = f.read()

      statements = sqlparse.split(sql_text)
      create_table_defs = {}
      insert_blocks = defaultdict(list)

      # Pass 1: Capture all CREATE TABLE column names
      for stmt in statements:
            stmt = stmt.strip()
            if stmt.upper().startswith("CREATE TABLE"):
                  match = re.search(r"CREATE TABLE `(.*?)` \((.*)\)\s*(ENGINE|DEFAULT|CHARSET)?", stmt, re.DOTALL)
                  if match:
                        table_name, cols_block, _ = match.groups()
                        # Split on commas not inside parentheses
                        col_lines = re.split(r",\s*(?![^()]*\))", cols_block.strip())
                        columns = []
                        for col in col_lines:
                              col = col.strip()
                              if col.startswith("`"):
                                    col_name = re.match(r"`(.*?)`", col)
                                    if col_name:
                                          columns.append(col_name.group(1))
                        create_table_defs[table_name] = columns

            # Capture INSERT INTO
            elif stmt.upper().startswith("INSERT INTO"):
                  table_match = re.match(r"INSERT INTO `(.*?)`", stmt)
                  if table_match:
                        table_name = table_match.group(1)
                        values_part = stmt[stmt.find("VALUES") + 6:].strip().rstrip(";")
                        values_cleaned = values_part.replace("),(", ")\n(")
                        lines = values_cleaned.splitlines()
                        insert_blocks[table_name].extend(lines)


      # Pass 3: Parse and save each table
      for table, lines in insert_blocks.items():
            parsed_rows = []
            for line in lines:
                  line = line.strip()
                  if line.endswith(","):
                        line = line[:-1]
                  line = line.strip("(),")

                  try:
                        reader = csv.reader([line], delimiter=",", quotechar="'", escapechar='\\')
                        parsed = next(reader)
                        parsed_rows.append(parsed)
                  except Exception as e:
                        print(f"⚠️ Error parsing line in table `{table}`: {e}")
                        continue

            if not parsed_rows:
                  continue

            # Use real columns if match, otherwise fallback
            headers = create_table_defs.get(table, [])
            if len(headers) != len(parsed_rows[0]):
                  headers = [f"col_{i+1}" for i in range(len(parsed_rows[0]))]

            try:
                  df = pd.DataFrame(parsed_rows, columns=headers)
                  df.to_parquet(os.path.join(output_dir, f"{table}.parquet"), index=False)
                  print(f"✅ Saved: {table} ({len(df)} rows)")
            except Exception as e:
                  print(f"❌ Failed to save {table}: {e}")

if __name__ == "__main__":
      sql_path = "final_dump.sql"
      output_folder = "tables"
      parse_sql_to_parquet_relaxed(sql_path, output_folder)
