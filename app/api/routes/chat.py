from fastapi import APIRouter, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.schemas import ChatRequest, DocumentationSet
from app.services.chat import ChatService
from app.core.logging import setup_logging
import uuid

from app.services.store import VectorStore

router = APIRouter()
chat_service = ChatService()
store = VectorStore()

logger = setup_logging(__name__)


@router.post("/")
async def chat(request: ChatRequest):
    logger.info(f"entered the ask endpoint with identifier {request.identifier}")
    doc_set_id: uuid.UUID
    try:
        if request.identifier.is_valid_uuid:
            doc_set_id = uuid.UUID(request.identifier.id_or_name)

        else:
            async with AsyncSession(store.engine) as session:
                stmt = select(DocumentationSet).where(
                    DocumentationSet.name == request.identifier.id_or_name
                )
                result = await session.execute(stmt)
                doc_set = result.scalar_one_or_none()
                if not doc_set:
                    raise ValueError(
                        f"no documentation found with name {request.identifier.id_or_name}"
                    )
            doc_set_id = doc_set.id

        response = await chat_service.chat(
            doc_set_id=doc_set_id,
            message=request.message,
            chat_history=request.chat_history,
        )
        return {"response": response}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"chat failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="failed to process chat request, check logs for details",
        )
