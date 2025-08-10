import os
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface.embeddings import HuggingFaceEmbeddings

load_dotenv()

RAW_DATA_PATH = "data/structured_programs.json"
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")


def load_structured_data(filepath: str) -> list:
    """Загружает структурированные данные из JSON."""
    return json.loads(Path(filepath).read_text(encoding="utf-8"))


def create_documents_from_data(programs_data: list) -> list[Document]:
    """Преобразует JSON данные в список объектов Document для LangChain."""
    documents = []

    for program in programs_data:
        general_content = (
            f"Название программы: {program['title']}.\n"
            f"Описание: {program['description']}\n"
            f"Карьерные возможности: {program['career']}"
        )
        documents.append(
            Document(
                page_content=general_content,
                metadata={
                    "source": program["url"],
                    "type": "general_info",
                    "program_title": program["title"],
                },
            )
        )

        for course in program["courses"]:
            course_content = (
                f"Дисциплина: {course['name']}. "
                f"Тип: {course['type']}. "
                f"Семестр: {course['semester']}. "
                f"Эта дисциплина относится к программе '{program['title']}'."
            )
            documents.append(
                Document(
                    page_content=course_content,
                    metadata={
                        "source": program["url"],
                        "type": "course_info",
                        "program_title": program["title"],
                        "course_name": course["name"],
                        "semester": course["semester"],
                        "course_type": course["type"],
                    },
                )
            )

    return documents


def main():
    print("[indexer] Starting indexing process...")

    programs_data = load_structured_data(RAW_DATA_PATH)
    if not programs_data:
        print("[indexer] No data found. Run parser.py first.")
        return

    documents = create_documents_from_data(programs_data)
    print(f"[indexer] Created {len(documents)} documents to be indexed.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)

    print(f"[indexer] Initializing embedding model: {EMBEDDING_MODEL}")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
    )

    print(f"[indexer] Creating vector store at: {VECTOR_DB_PATH}")
    vectordb = Chroma.from_documents(
        documents=docs, embedding=embeddings, persist_directory=VECTOR_DB_PATH
    )

    vectordb.persist()
    print("[indexer] Indexing complete. Vector store saved.")


if __name__ == "__main__":
    main()
