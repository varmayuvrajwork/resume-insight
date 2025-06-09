from flask import Flask, request, render_template, send_file, jsonify, session
import pandas as pd
import os
import io
from data_loader import DataLoader
from azure_llm import parse_query_with_azure_llm
from openai import AzureOpenAI

app = Flask(__name__, template_folder="template")
app.secret_key = "resume-insight-2025-key"

CSV_DIR = os.path.join(os.getcwd(), "csv_tables")
loader = DataLoader(CSV_DIR)
tables = loader.get_all_tables()

last_filtered_df = pd.DataFrame()

@app.route("/", methods=["GET"])
def index():
      return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
      global last_filtered_df
      user_message = request.json.get("message", "")
      mode = request.json.get("mode", "llm")

      if not user_message:
            return jsonify({"error": "No message provided"}), 400

      if mode == "resume":
            from graph import search_tables
            state = {"query": user_message, "tables": list(tables.keys())}
            output = search_tables(state)

            result_html = output.get("result", "No matching resumes found.")
            if "dataframes" in output and output["dataframes"]:
                  last_filtered_df = pd.concat(output["dataframes"], ignore_index=True)
            return jsonify({"reply": result_html})

      # Chat mode (LLM)
      if "chat_history" not in session:
            session["chat_history"] = []

      history = session["chat_history"]

      try:
            client = AzureOpenAI(
                  api_key=os.getenv("AZURE_OPENAI_KEY"),
                  api_version="2024-12-01-preview",
                  azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
            )

            response = client.chat.completions.create(
                  model=os.getenv("AZURE_DEPLOYMENT_NAME"),
                  messages=[
                  {"role": "system", "content": "You are a helpful assistant for resume and hiring-related queries."},
                  *history,
                  {"role": "user", "content": user_message}
                  ],
                  temperature=0.4
            )

            assistant_reply = response.choices[0].message.content.strip()

            # Update session memory
            history.extend([
                  {"role": "user", "content": user_message},
                  {"role": "assistant", "content": assistant_reply}
            ])
            session["chat_history"] = history

            return jsonify({"reply": assistant_reply})

      except Exception as e:
            print("❌ Chat error:", e)
            return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route("/clear", methods=["POST"])
def clear_chat():
      session["chat_history"] = []
      return jsonify({"status": "cleared"})

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
