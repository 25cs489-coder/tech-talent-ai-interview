from google import genai

client = genai.Client(api_key="")

response = client.models.generate_content(
    model="gemini-1.5-flash",
    contents="Generate one Python interview question"
)

print(response.text)