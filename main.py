from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_gemini import GeminiAPIWrapper

load_dotenv()

llm = GeminiAPIWrapper(model="gemini-3.5-flash")
response = llm.invoke("What is the capital of France?")
print(response)
