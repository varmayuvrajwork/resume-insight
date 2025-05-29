import os
import openai
import json
from dotenv import load_dotenv
load_dotenv()
# Azure credentials
AZURE_API_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o")
AZURE_API_VERSION = "2024-12-01-preview"

client = openai.AzureOpenAI(
    api_key=AZURE_API_KEY,
    api_version=AZURE_API_VERSION,
    azure_endpoint=AZURE_ENDPOINT
)

def parse_query_with_azure_llm(query: str) -> dict:
    try:
        system_prompt = (
            "You are a resume filter parser. Convert user queries into structured filters "
            "as JSON like: {\"field\": \"skills_extracted\", \"value\": \"ux designer\", \"filter_type\": \"contains\"}. "
            "No explanation. No markdown. No triple backticks. Only valid JSON."
        )

        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.2,
            max_tokens=150
        )

        reply = response.choices[0].message.content.strip("` \n")
        print("🧠 Azure LLM response:", reply)
        return json.loads(reply)

    except Exception as e:
        print(f"❌ Error from Azure OpenAI: {e}")
        return {}
