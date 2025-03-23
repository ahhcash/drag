from select import select

from langchain_anthropic.chat_models import ChatAnthropic
from langchain.prompts import ChatPromptTemplate

from app.models.db import Message, Conversation
from app.services.store import VectorStore
from app.core.config import get_settings
from langchain.schema import StrOutputParser
from app.models.api import ChatMessage, ConversationRead
from typing import List, Dict, Tuple
from uuid import UUID
from app.core.logging import setup_logging
from sqlmodel.ext.asyncio.session import AsyncSession

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
                        You are an AI assistant specialized in answering questions about technical documentation. Follow these guidelines:

                        1. Answer the question as accurately as possible
                        2. Always cite your sources by including relevant documentation page URLs
                        3. For code-related questions, include relevant code snippets from the documentation
                        4. Keep responses clear and concise while maintaining technical accuracy
                        5. When citing multiple sources, specify which information comes from where
                        7. If the context seems insufficient, search the web to determine the best answer to the question.
                        8. Format code blocks and technical terms appropriately using markdown

                        Your goal is to help users understand the documentation quickly and accurately."                    
                    """,
                ),
                (
                    "human",
                    "Context:\n{context}\n\nChat History:\n{chat_history}\n\nQuestion: {question}",
                ),
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
            k=10,  # retrieve top 4 chunks
        )

        formatted_chunks = [
            f"From {chunk.title} ({chunk.url}):\n{chunk.content}\n" for chunk in chunks
        ]

        context = "\n---\n".join(formatted_chunks)
        logger.info(f"context for incoming message: {context}")
        return context

    async def chat(
        self,
        doc_set_id: UUID,
        message: str,
        conversation_id: UUID | None = None,
        chat_history: List[ChatMessage] = None,
    ) -> Tuple[str, UUID]:
        if chat_history is None:
            chat_history = []

        # Get or create conversation
        if not conversation_id:
            conversation_id = await self._create_conversation(doc_set_id, message)

        # Get relevant chunks from vector store
        _ = await self._get_context(doc_set_id, message)

        # Format chat history for the LLM
        formatted_history = []
        for msg in chat_history:
            formatted_history.append({"role": msg.role, "content": msg.content})

        # Construct prompt with history
        response = await self.chain.ainvoke(
            {
                "doc_set_id": doc_set_id,
                "question": message,
                "chat_history": formatted_history,
            }
        )

        # Store the new messages
        await self._store_messages(
            conversation_id,
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": response},
            ],
        )

        return response, conversation_id

    async def _create_conversation(self, doc_set_id: UUID, first_message: str) -> UUID:
        """Create a new conversation and return its ID"""
        async with AsyncSession(self.store.engine) as session:
            # Generate a title based on the first message
            title = (
                first_message[:50] + "..." if len(first_message) > 50 else first_message
            )

            conversation = Conversation(documentation_set_id=doc_set_id, title=title)
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)

            return conversation.id

    async def _store_messages(
        self, conversation_id: UUID, messages: List[Dict[str, str]]
    ):
        """Store messages in the database"""
        async with AsyncSession(self.store.engine) as session:
            for msg in messages:
                message = Message(
                    conversation_id=conversation_id,
                    role=msg["role"],
                    content=msg["content"],
                )
                session.add(message)
            await session.commit()

    async def get_conversation(self, conversation_id: UUID) -> ConversationRead:
        """Get a conversation with its messages"""
        async with AsyncSession(self.store.engine) as session:
            # Get conversation
            conversation = await session.get(Conversation, conversation_id)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")

            # Get messages
            stmt = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
            result = await session.execute(stmt)
            messages = result.scalars().all()

            # Convert to API model
            return ConversationRead(
                id=conversation.id,
                documentation_set_id=conversation.documentation_set_id,
                title=conversation.title,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                messages=[
                    ChatMessage(role=msg.role, content=msg.content) for msg in messages
                ],
            )
