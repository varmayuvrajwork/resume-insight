from flask import Flask, request, render_template, send_file
import pandas as pd
import os
import io
from data_loader import DataLoader
from graph import search_tables
from azure_llm import parse_query_with_azure_llm

app = Flask(__name__, template_folder="template")
CSV_DIR = os.path.join(os.getcwd(), "csv_tables")
loader = DataLoader(CSV_DIR)
tables = loader.get_all_tables()

last_filtered_df = pd.DataFrame()

@app.route("/", methods=["GET", "POST"])
def index():
      global last_filtered_df
      result = ""
      highlight_word = ""

      if request.method == "POST":
            query = request.form["query"]
            state = {"query": query, "tables": list(tables.keys())}
            output = search_tables(state)

            result = output.get("result", "")
            if "dataframes" in output and output["dataframes"]:
                  last_filtered_df = pd.concat(output["dataframes"], ignore_index=True)

            # Optional keyword highlighting
            filter = parse_query_with_azure_llm(query)
            if isinstance(filter, dict):
                  for val in filter.values():
                        if isinstance(val, str):
                              highlight_word = val.strip()
                              break
                        elif isinstance(val, list) and val:
                              highlight_word = str(val[0]).strip()
                              break

            if highlight_word:
                  result = result.replace(highlight_word, f"<mark>{highlight_word}</mark>")

      return render_template("index.html", result=result)

@app.route("/download", methods=["GET"])
def download_csv():
      global last_filtered_df
      if last_filtered_df.empty:
            return "No data available to download.", 400

      csv_io = io.StringIO()
      last_filtered_df.to_csv(csv_io, index=False)
      csv_io.seek(0)

      return send_file(
            io.BytesIO(csv_io.getvalue().encode()),
            mimetype="text/csv",
            as_attachment=True,
            download_name="filtered_results.csv"
      )

if __name__ == "__main__":
      app.run(debug=True)
