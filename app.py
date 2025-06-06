from flask import Flask, request, render_template, send_file, jsonify
import pandas as pd
import os
import io
from data_loader import DataLoader
from azure_llm import parse_query_with_azure_llm

app = Flask(__name__, template_folder="template")
CSV_DIR = os.path.join(os.getcwd(), "csv_tables")
loader = DataLoader(CSV_DIR)
tables = loader.get_all_tables()

last_filtered_df = pd.DataFrame()

def apply_filters(query):
      global last_filtered_df
      highlight_word = ""
      result_html = ""
      result_json = []

      state = {"query": query, "tables": list(tables.keys())}
      from graph import search_tables  # Delayed import in case of circulars
      output = search_tables(state)

      result_html = output.get("result", "")
      result_json = []
      if "dataframes" in output and output["dataframes"]:
            last_filtered_df = pd.concat(output["dataframes"], ignore_index=True)
            for _, row in last_filtered_df.iterrows():
                  result_json.append({
                  "file_name": row.get("file_name", ""),
                  "job_title": row.get("job_title", ""),
                  "skills": row.get("skills_extracted", ""),
                  "location": row.get("location", ""),
                  "created_date": row.get("created_date", ""),
                  "updated_date": row.get("updated_date", "")
                  })

      # Highlight keyword for HTML
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
            result_html = result_html.replace(highlight_word, f"<mark>{highlight_word}</mark>")

      return result_html, result_json

@app.route("/", methods=["GET", "POST"])
def index():
      result_html = ""
      if request.method == "POST":
            query = request.form["query"]
            result_html, _ = apply_filters(query)
      return render_template("index.html", result=result_html)

@app.route("/chat", methods=["POST"])
def chat():
      user_query = request.json.get("message", "")
      if not user_query:
            return jsonify({"error": "No message provided"}), 400
      _, flashcards = apply_filters(user_query)
      return jsonify({"flashcards": flashcards})

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
