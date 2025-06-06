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

      combined_results = []
      for table, df in dfs:
            html_table = df.head(10).to_html(index=False, classes="table table-bordered table-sm table-striped")
            combined_results.append(f"<h5>🗂️ Table: <code>{table}</code></h5>{html_table}")

      return {
            "result": "<br><br>".join(combined_results),
            "dataframes": [df for _, df in dfs]
      }



def build_graph():
      workflow = StateGraph(WorkflowState)
      workflow.add_node("select_tables", select_relevant_tables)
      workflow.add_node("search_data", search_tables)
      workflow.set_entry_point("select_tables")
      workflow.add_edge("select_tables", "search_data")
      workflow.set_finish_point("search_data")
      return workflow.compile()