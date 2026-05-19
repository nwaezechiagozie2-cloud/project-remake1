import sys
from pathlib import Path

# Ensure project root is on sys.path so sibling package `app` can be imported
# when this file is executed directly (sys.path[0] is the script's directory).
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI


from langchain_community.document_loaders import TextLoader
from app.config import Settings

settings=Settings()

gemini = None
if settings.gemini_api_key:
    gemini = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.7,
    )
        
nvidia = None
if settings.nvidia_api_key:
    nvidia = ChatOpenAI(
        api_key=settings.nvidia_api_key,
        model=settings.nvidia_model,
        base_url=settings.nvidia_base_url,
        temperature=0.7,
    )

loader = TextLoader("practice agent/business_policies.txt")
document=loader.load()
print(document)


from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)

splitted_docs=text_splitter.split_documents(document)
for doc in splitted_docs:
    print(doc)
    print("\n\n")


