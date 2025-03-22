from langchain_anthropic.chat_models import ChatAnthropic
from langchain.prompts import ChatPromptTemplate

from app.services.store import VectorStore
from app.core.config import get_settings
from langchain.schema import StrOutputParser
from app.models.api import ChatMessage
from typing import List
from uuid import UUID
from app.core.logging import setup_logging

logger = setup_logging(__name__)


class ChatService:
    def __init__(self):
        self.settings = get_settings()
        self.store = VectorStore()
        self.llm = ChatAnthropic(
            model_name="claude-3-7-sonnet-20250219",
            temperature=0.1,
            timeout=None,
            stop=None,
        )
        # self.llm = ChatOllama(
        #     model="llama3.1",
        #     temperature=0.1
        # )
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                    You are tech expert who can answer questions related to docs. You'll be given some context, use that to answer their questions
                    """,
                ),
                ("human", "Context:\n{context}\n\nQuestion: {question}"),
            ]
        )

        async def get_context_and_question(inputs):
            context = await self._get_context(inputs["doc_set_id"], inputs["question"])
            return {"context": context, "question": inputs["question"]}

        self.chain = (
            get_context_and_question | self.prompt | self.llm | StrOutputParser()
        )

    async def _get_context(self, doc_set_id: UUID, question: str) -> str:
        chunks = await self.store.similarity_search(
            query=question,
            doc_set_id=doc_set_id,
            k=4,  # retrieve top 4 chunks
        )

        formatted_chunks = [
            f"From {chunk.title} ({chunk.url}):\n{chunk.content}\n" for chunk in chunks
        ]

        context = "\n---\n".join(formatted_chunks)
        logger.info(f"context for incoming message: {context}")
        return context

    async def chat(
        self, doc_set_id: UUID, message: str, chat_history: List[ChatMessage] = []
    ) -> str:
        # get relevant chunks from vector store
        logger.info(f"inside chat service, message: {message}, history: {chat_history}")

        response = await self.chain.ainvoke(
            {"doc_set_id": doc_set_id, "question": message}
        )

        print(f"received response: {response}")
        return response
