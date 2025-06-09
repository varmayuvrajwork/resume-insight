import os
import pandas as pd
from typing import TypedDict, List, Union
from langgraph.graph import StateGraph, END
from data_loader import DataLoader
from azure_llm import parse_query_with_azure_llm

loader = DataLoader("csv_tables")
tables = loader.get_all_tables()
schema_map = loader.get_schema_map()
priority_tables = loader.get_priority_tables()

class WorkflowState(TypedDict, total=False):
      query: str
      table: str
      tables: List[str]
      data: pd.DataFrame
      result: str

def select_relevant_tables(state: WorkflowState) -> dict:
      query = state["query"].lower()
      matched_tables = []

      for table_name, columns in schema_map.items():
            if any(col.lower() in query for col in columns) or table_name in query:
                  matched_tables.append(table_name)

      if not matched_tables and "worker" in query:
            matched_tables = ["worker_attachment"]

      return {"tables": matched_tables or priority_tables}

def search_tables(state: WorkflowState) -> dict:
      query = state["query"].strip()
      dfs = []

      # Step 1: LLM parses query into structured filters
      filter = parse_query_with_azure_llm(query)
      if not filter:
            return {"result": "❌ Unable to understand query. Please try something else."}

      # Step 2: Normalize to 'field', 'value', 'filter_type'
      filters = []
      if "field" in filter and "value" in filter:
            filters.append({
                  "field": filter["field"],
                  "value": str(filter["value"]).lower(),
                  "filter_type": filter.get("filter_type", "contains")
            })
      elif isinstance(filter, dict):
            for k, v in filter.items():
                  if isinstance(v, list) and v:
                        filters.append({
                              "field": k,
                              "value": str(v[0]).lower(),
                              "filter_type": "contains"
                  })
                  elif isinstance(v, str):
                        filters.append({
                              "field": k,
                              "value": v.lower(),
                              "filter_type": "contains"
                  })
      else:
            return {"result": "❌ Unable to understand query. Please try something else."}

      fallback_fields = ["job_title", "skills_extracted", "location", "file_name", "created_date", "updated_date"]

      for table in state["tables"]:
            df = tables.get(table)
            if df is None or df.empty:
                  continue

            try:
                  mask = pd.Series([True] * len(df))

                  for f in filters:
                        field = f["field"]
                        value = f["value"]
                        filter_type = f.get("filter_type", "contains")

                        # Field fallback
                        if field not in df.columns:
                              for fallback in fallback_fields:
                                    if fallback in df.columns:
                                          field = fallback
                                    break

                        if field not in df.columns:
                              continue

                        series = df[field].fillna("").astype(str).str.lower()
                        if filter_type == "contains":
                              match = series.str.contains(value, na=False)
                        elif filter_type == "equals":
                              match = series == value
                        elif filter_type == "startswith":
                              match = series.str.startswith(value)
                        elif filter_type == "endswith":
                              match = series.str.endswith(value)
                        else:
                              match = series.str.contains(value, na=False)

                        mask &= match

                  filtered = df[mask]
                  if not filtered.empty:
                        display_cols = [col for col in ["file_name", "job_title", "skills_extracted", "location", "created_date", "updated_date"] if col in df.columns]
                        filtered_display = filtered[display_cols].copy()
                        dfs.append((table, filtered_display))

            except Exception as e:
                  print(f"❌ Error filtering {table}: {e}")

      if not dfs:
            return {"result": "No results found."}

      # Step: Prioritize workers_attachment for natural summary
      summary_text = ""
      for table, df in dfs:
            if table == "worker_attachment":
                  summary_df = df.head(10)
                  summary_prompt = f"Summarize this resume data in plain language for a user query: '{query}'. Be brief, focus on job titles, locations, and skills:\n\n{summary_df.to_string(index=False)}"
                  
                  try:
                        from azure_llm import client
                        response = client.chat.completions.create(
                        model=os.getenv("AZURE_DEPLOYMENT_NAME"),
                        messages=[
                              {"role": "system", "content": "You summarize resume data into simple conversational summaries."},
                              {"role": "user", "content": summary_prompt}
                        ],
                        temperature=0.3,
                        max_tokens=250
                        )
                        summary_text = response.choices[0].message.content.strip()
                  except Exception as e:
                        summary_text = "Error generating summary."

      # Fallback if no worker_attachment found
      if not summary_text:
            summary_text = "I found some resumes matching your query, but couldn’t summarize them clearly."

      return {
      "result": summary_text,
      "dataframes": [df for _, df in dfs if df is not None]
      }




def build_graph():
      workflow = StateGraph(WorkflowState)
      workflow.add_node("select_tables", select_relevant_tables)
      workflow.add_node("search_data", search_tables)
      workflow.set_entry_point("select_tables")
      workflow.add_edge("select_tables", "search_data")
      workflow.set_finish_point("search_data")
      return workflow.compile()