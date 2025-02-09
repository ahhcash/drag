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
            model_name="claude-3-5-sonnet-20241022",
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
                    """You are an AI assistant specialized in answering questions about technical documentation. Your responses must be based ONLY on the provided documentation context. Follow these guidelines:

                        1. Only answer based on the given context - if you're unsure or the context doesn't contain relevant information, say so clearly
                        2. Always cite your sources by including relevant documentation page URLs
                        3. For code-related questions, include relevant code snippets from the documentation
                        4. Keep responses clear and concise while maintaining technical accuracy
                        5. When citing multiple sources, specify which information comes from where
                        6. If the user's question is ambiguous, ask for clarification
                        7. If the context seems insufficient, indicate what additional information would help
                        8. Format code blocks and technical terms appropriately using markdown

                        Your goal is to help users understand the documentation quickly and accurately. Avoid speculation or information from outside the provided context.""",
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

        return response
