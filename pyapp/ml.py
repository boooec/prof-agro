import os
import time
import json
import tomli
import requests
import threading
import warnings
import contextlib
import proto.api_pb2_grpc as api_grpc
import proto.api_pb2 as api

from PyPDF2 import PdfReader
from urllib.parse import urlencode
from urllib3.exceptions import InsecureRequestWarning

from langchain_core.messages import SystemMessage
from langchain_community.chat_models import GigaChat
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import HumanMessagePromptTemplate

from config import ParametrsAndPromts

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams
from langchain.text_splitter import RecursiveCharacterTextSplitter


@contextlib.contextmanager
def no_ssl_verification():
    old_merge_environment_settings = requests.Session.merge_environment_settings

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        settings["verify"] = False
        return settings
    requests.Session.merge_environment_settings = merge_environment_settings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InsecureRequestWarning)
            yield
    finally:
        requests.Session.merge_environment_settings = old_merge_environment_settings


def get_token():
    RQUID = os.getenv('GPT_RQUID')
    AUTH_DATA = os.getenv('GPT_AUTH_DATA')
    OAUTH_URL = 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'
    API_URL = 'https://gigachat.devices.sberbank.ru/api/v1'
    TOKEN = None

    headers = {'RqUID': RQUID,
               'Content-Type': 'application/x-www-form-urlencoded',
               'Authorization': f'Bearer {AUTH_DATA}'}
    body = urlencode({'scope': 'GIGACHAT_API_CORP'})
    with no_ssl_verification():
        response = requests.post(OAUTH_URL, data=body, headers=headers)
    response.raise_for_status()
    return response.json()['access_token']


def update_token():
    global TOKEN_EMB
    TOKEN_EMB = get_token()


TOKEN_EMB = get_token()
TOKEN = os.getenv('GPT_TOKEN')
URL = 'https://gigachat.devices.sberbank.ru/api/v1'

model = GigaChat(
    base_url=URL,
    credentials=TOKEN,
    scope='GIGACHAT_API_CORP',
    model='GigaChat-Max',
    profanity_check=False,
    streaming=False,
    timeout=180,
    verify_ssl_certs=False,
)

parametrsandprompts = ParametrsAndPromts.model_validate(tomli.load(open('model.toml', 'rb')))
prompt_chtodelat = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=parametrsandprompts.prompts.system_prompt_template),
        HumanMessagePromptTemplate.from_template(parametrsandprompts.prompts.user_prompt_template.format(
            instruction=parametrsandprompts.prompts.instructions.chtodelat))
    ]
)
prompt_checklist = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=parametrsandprompts.prompts.system_prompt_template),
        HumanMessagePromptTemplate.from_template(parametrsandprompts.prompts.user_prompt_template.format(
            instruction=parametrsandprompts.prompts.instructions.checklist))
    ]
)

chain_chtodelat = prompt_chtodelat | model | StrOutputParser()
chain_checklist = prompt_checklist | model | StrOutputParser()


def get_gigachat_embeddings(text,
                            model: str = 'Embeddings',
                            profanity_check: bool = False):
    url = URL + '/embeddings'
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json',
               'Authorization': f'Bearer {TOKEN_EMB}'}
    body = {'model': model,
            'input': text,
            'profanity_check': profanity_check}
    with no_ssl_verification():
        response = requests.post(url, data=json.dumps(body), headers=headers)
    response.raise_for_status()
    data_dict = response.json()
    return data_dict['data'][0]['embedding']


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Извлекает текст из PDF-файла.
    """
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text


def load_all_pdfs(directory: str) -> list:
    """
    Загружает все PDF-файлы из указанной директории и извлекает текст.
    """
    texts = []
    for filename in os.listdir(directory):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(directory, filename)
            text = extract_text_from_pdf(pdf_path)
            texts.append((filename, text))
    return texts


# Инициализация Qdrant
qdrant_client = QdrantClient(
    url="https://653b43b7-8f16-426a-9ecd-9bf4b5c981dc.us-west-2-0.aws.cloud.qdrant.io:6333",
    api_key="Fj0CZ72rhxPm4f2HxXUqwqDVB1wY5jH6wn5FcgMNH14O4M-1yuM4_g"
)
collection_name = "documentation"


def search_relevant_docs(query: str, top_k: int = 10):
    """
    Поиск релевантных документов в Qdrant с использованием эмбеддингов GigaChat.
    """
    query_vector = get_gigachat_embeddings(query)

    search_results = qdrant_client.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=top_k,
    )
    return [
        {"text": result.payload["text"], "source": result.payload["source"]}
        for result in search_results
    ]


def giga_invoke(req: api.Request) -> str:
    # Поиск релевантных фрагментов
    relevant_docs = search_relevant_docs(req.question)
    context = "\n".join([f"Источник: {doc['source']}\n{doc['text']}" for doc in relevant_docs])

    # Формирование запроса с контекстом
    full_query = f"Контекст:\n{context}\n\nВопрос: {req.question}"

    # Обращение к GigaChat
    answer = ""
    if req.question_type == api.QUESTION_TYPE_QUESTION:
        answer = chain_chtodelat.invoke(full_query)
    elif req.question_type == api.QUESTION_TYPE_CHECKLIST:
        answer = chain_checklist.invoke(full_query)
    else:
        answer = "Такой задачи не существует"
    return answer
