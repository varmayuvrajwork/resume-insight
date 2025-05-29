import os
import json
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-12-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

def parse_query_with_azure_llm(query: str) -> dict:
    try:
        system_prompt = (
            "You are a resume filter parser. Convert user queries into structured filters "
            "as JSON like: {\"field\": \"skills_extracted\", \"value\": \"ux designer\", \"filter_type\": \"contains\"}. "
            "Respond only with valid JSON — no explanations, no markdown, no extra characters."
        )

        response = client.chat.completions.create(
            model=os.getenv("AZURE_DEPLOYMENT_NAME"),  # e.g., "gpt-35-turbo"
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.2,
            max_tokens=150
        )

        reply = response.choices[0].message.content.strip("` \n")
        print("🧠 Azure LLM response:", reply)

        # Defensive parsing
        return json.loads(reply)

    except json.JSONDecodeError:
        print("❌ JSON decode error — model likely returned unexpected content.")
        return {}
    except Exception as e:
        print(f"❌ General error from Azure OpenAI: {e}")
        return {}
