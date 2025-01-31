from langchain_anthropic.chat_models import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from app.services.store import VectorStore
from app.core.config import get_settings
from langchain.schema import StrOutputParser
from app.models.schemas import ChatMessage
from typing import List
from uuid import UUID
from app.models.schemas import DocumentChunk

class ChatService:
    def __init__(self):
        self.settings = get_settings()
        self.store = VectorStore()
        self.llm = ChatAnthropic(
            model_name="claude-3-5-sonnet-20241022",
            temperature=0.1,
            timeout=None,
            stop=None
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant that answers questions about documentation.
            You will be given some context from the documentation and a question.
            Only answer based on the context provided. If you're unsure or the context doesn't
            contain the relevant information, say so.

            Keep responses concise but informative. If appropriate, include relevant code snippets
            from the documentation context.

            Always include links to the relevant documentation pages where you found the information."""),
            ("human", "Context:\n{context}\n\nQuestion: {question}"),
        ])

        self.chain = self.prompt | self.llm | StrOutputParser()

    async def _format_chat_context(self, chunks: List[DocumentChunk]) -> str:
            # format chunks into a string with clear section breaks and source links
            formatted_chunks = []
            for chunk in chunks:
                formatted_chunks.append(
                    f"From {chunk.title} ({chunk.url}):\n{chunk.content}\n"
                )
            return "\n---\n".join(formatted_chunks)

    async def chat(
        self,
        doc_set_id: UUID,
        message: str,
        chat_history: List[ChatMessage] = []
    ) -> str:
        # get relevant chunks from vector store
        context_chunks = await self.store.similarity_search(
            query=message,
            doc_set_id=doc_set_id,
            k=4  # retrieve top 4 chunks
        )

        # format context from chunks
        context = await self._format_chat_context(context_chunks)

        # invoke chain
        response = await self.chain.ainvoke({
            "context": context,
            "question": message
        })

        return response
