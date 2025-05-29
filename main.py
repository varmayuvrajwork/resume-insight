from graph import build_graph
from typing import Any

# Build the graph agent
workflow = build_graph()

def run_agent_query(query: str) -> Any:
      state = {"query": query}
      result = workflow.invoke(state)
      return result.get("result")

if __name__ == "__main__":
      while True:
            user_input = input("🧠 Ask a question: ")
            if user_input.lower() in ["exit", "quit"]:
                  break

            try:
                  print("\n📊 Insight:\n")
                  output = run_agent_query(user_input)
                  print(output)
            except Exception as e:
                  print(f"\n❌ Error: {e}")
