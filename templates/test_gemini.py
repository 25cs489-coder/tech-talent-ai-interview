from google import genai
import os

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

response = client.models.generate_content(
    model="gemini-1.5-flash",
    contents="Generate one Python interview question"
)

print(response.text)