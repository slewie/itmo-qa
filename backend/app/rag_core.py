import os
from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_llm7 import ChatLLM7
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain

from .prompts import QA_PROMPT, RECOMMENDATION_PROMPT

load_dotenv()


class RAGCore:
    def __init__(self):
        print("[RAGCore] Initializing...")
        self.embedding_model = HuggingFaceEmbeddings(
            model_name=os.environ["EMBEDDING_MODEL"], model_kwargs={"device": "cpu"}
        )

        self.vectordb = Chroma(
            persist_directory=os.environ["VECTOR_DB_PATH"],
            embedding_function=self.embedding_model,
        )

        self.llm = ChatLLM7(
            model=os.environ["LLM_MODEL_NAME"],
            temperature=0.0,
        )

        self.combine_docs_chain = create_stuff_documents_chain(self.llm, QA_PROMPT)

        retriever = self.vectordb.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 8},
        )
        self.qa_chain = create_retrieval_chain(retriever, self.combine_docs_chain)
        print("[RAGCore] Initialized successfully.")

    def answer_query(self, query: str) -> dict:
        """Отвечает на общий вопрос с использованием RAG."""
        print(f"[RAGCore] Answering general query: {query}")
        result = self.qa_chain.invoke({"input": query})
        return {
            "answer": result["answer"],
            "source_documents": [
                {"page_content": doc.page_content, "metadata": doc.metadata}
                for doc in result["context"]
            ],
        }

    def get_recommendations(self, user_background: str) -> dict:
        """Генерирует персонализированные рекомендации по курсам."""
        print(
            f"[RAGCore] Generating recommendations for background: {user_background[:50]}..."
        )
        elective_retriever = self.vectordb.as_retriever(
            search_kwargs={"k": 30}
        )
        docs = elective_retriever.invoke(f"Дисцпилины для человека с опытом: {user_background}")

        if not docs:
            return {
                "answer": "К сожалению, я не смог найти информацию о курсах по выбору.",
                "source_documents": [],
            }

        courses_list = "\n".join(
            f"- {doc.metadata['course_name']} (Программа: {doc.metadata['program_title']}, Семестр: {doc.metadata['semester']})"
            for doc in docs
        )

        recommendation_chain = RECOMMENDATION_PROMPT | self.llm
        result = recommendation_chain.invoke(
            {"user_background": user_background, "courses_list": courses_list}
        )

        return {
            "answer": result.content,
            "source_documents": [
                {"page_content": doc.page_content, "metadata": doc.metadata}
                for doc in docs
            ],
        }


rag_core_instance = RAGCore()
