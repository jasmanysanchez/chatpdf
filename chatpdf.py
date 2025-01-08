import json
import os
import warnings
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
import sys
import argparse
from dotenv import load_dotenv
import re

warnings.filterwarnings('ignore')
sys.stderr = open('nul' if sys.platform == 'win32' else '/dev/null', 'w')

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text


# Splitting text into small chunks to create embeddings
def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks


# Using Google's embedding004 model to create embeddings and FAISS to store the embeddings
def get_vectorstore(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore


# Handling user questions
def handle_userinput(question, conversation):
    response = conversation({"question": question})
    return response

# Storing converstations as chain of outputs
def get_conversation_chain(vectorstore):
    # model = 'gemini-1.5-pro-latest'
    # model = 'gemini-2.0-flash-thinking-exp-1219'
    # model = 'gemma-2-27b-it'
    model = 'gemini-1.5-flash-8b'
    llm = ChatGoogleGenerativeAI(model=model, convert_system_message_to_human=True, temperature=0, generation_config={"response_mime_type": "application/json"})
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory,
    )
    return conversation_chain

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description='Leer pdf con gemini y langchain')
    parser.add_argument('--path_file', nargs='+', type=str, help='Ruta absoluta del archivo en pdf')
    parser.add_argument('--prompt', type=str, help='Prompt')
    args = parser.parse_args()
    raw_text = get_pdf_text(args.path_file)
    text_chunks = get_text_chunks(raw_text)
    vectorstore = get_vectorstore(text_chunks)
    conversation = get_conversation_chain(vectorstore)
    response = handle_userinput(args.prompt, conversation)
    answer = response.get('answer')
    if isinstance(answer, str):
        answer = answer.replace('\n', '')
        if answer.startswith('```json'):
            answer = answer.replace('```json', '', 1)
            answer = answer.replace('```', '', 1)
        try:
            d = json.loads(answer)
            print(json.dumps(d))
            return 1
        except Exception as ex:
            pass
        return 0
    if isinstance(answer, list) or isinstance(answer, tuple):
        for i, x in enumerate(response.get('answer') or []):
            text = x['text']
            text = text.replace('\n', '')
            if text.startswith('```json'):
                text = answer.replace('```json', '', 1)
                text = answer.replace('```', '', 1)
            try:
                d = json.loads(text)
                print(json.dumps(d))
            except Exception as ex:
                continue
    return 1

if __name__ == '__main__':
    sys.exit(main())