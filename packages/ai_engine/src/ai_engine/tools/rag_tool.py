import os
import tempfile
from typing import List

import nest_asyncio
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders.sitemap import SitemapLoader
from langchain_community.vectorstores import SKLearnVectorStore
from langchain_openai import OpenAIEmbeddings
from langsmith import traceable
from openai import OpenAI

load_dotenv()

MODEL_NAME = "gpt-4o-mini"
MODEL_PROVIDER = "openai"
APP_VERSION = 1.0
RAG_SYSTEM_PROMPT = """You are an assistant for question-answering tasks. 
Use the following pieces of retrieved context to answer the latest question in the conversation. 
If you don't know the answer, just say that you don't know. 
Use three sentences maximum and keep the answer concise.
"""

openai_client = OpenAI()


def get_vector_db_retriever():
    persist_path = os.path.join(tempfile.gettempdir(), "union.parquet")
    embd = OpenAIEmbeddings(base_url=os.getenv("BASE_URL"))

    # If vector store exists, then load it
    if os.path.exists(persist_path):
        vectorstore = SKLearnVectorStore(embedding=embd, persist_path=persist_path, serializer="parquet")
        return vectorstore.as_retriever(lambda_mult=0)

    # Otherwise, index LangSmith documents and create new vector store
    ls_docs_sitemap_loader = SitemapLoader(
        web_path="https://docs.smith.langchain.com/sitemap.xml", continue_on_failure=True
    )
    ls_docs = ls_docs_sitemap_loader.load()

    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=500, chunk_overlap=0)
    doc_splits = text_splitter.split_documents(ls_docs)
    print("number of documents: ", len(doc_splits))

    vectorstore = SKLearnVectorStore.from_documents(
        documents=doc_splits, embedding=embd, persist_path=persist_path, serializer="parquet"
    )
    vectorstore.persist()
    return vectorstore.as_retriever(lambda_mult=0)


nest_asyncio.apply()
retriever = get_vector_db_retriever()

"""
retrieve_documents
- Returns documents fetched from a vectorstore based on the user's question
"""


@traceable(run_type="chain")
def retrieve_documents(question: str):
    return retriever.invoke(question)


"""
generate_response
- Calls `call_openai` to generate a model response after formatting inputs
"""


@traceable(run_type="chain")
def generate_response(question: str, documents):
    formatted_docs = "\n\n".join(doc.page_content for doc in documents)
    messages = [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {"role": "user", "content": f"Context: {formatted_docs} \n\n Question: {question}"},
    ]
    return call_openai(messages)


"""
call_openai
- Returns the chat completion output from OpenAI
"""


@traceable(run_type="llm", metadata={"ls_provider": MODEL_PROVIDER, "ls_model_name": MODEL_NAME})
def call_openai(messages: List[dict]) -> str:
    return openai_client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
    )


"""
langsmith_rag
- Calls `retrieve_documents` to fetch documents
- Calls `generate_response` to generate a response based on the fetched documents
- Returns the model response
"""


@traceable(run_type="chain")
def langsmith_rag(question: str):
    documents = retrieve_documents(question)
    response = generate_response(question, documents)
    return response.choices[0].message.content


if __name__ == "__main__":
    # print("first run to embed the documents")
    print(langsmith_rag("Can i run custom evaluator target function in the UI?"))

    # from langsmith import Client

    # lg_client = Client()
    # lg_client.create_example(
    #     dataset_name="LANGSMITH RAG APP DATASET",
    #     inputs={"question": "how to give name to a run?"},
    #     outputs={"output": "you can give a name to a run by using the run_name parameter in the tracing metadata"},
    # )
