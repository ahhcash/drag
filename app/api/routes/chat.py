from fastapi import APIRouter, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.api import ChatRequest, IngestionStatus
from app.models.db import DocumentationSet, IngestionTask
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
            id_str = request.identifier.id_or_name
            uuid_value = uuid.UUID(id_str)

            async with AsyncSession(store.engine) as session:
                stmt = select(DocumentationSet).where(
                    DocumentationSet.name == request.identifier.id_or_name
                )
                result = await session.execute(stmt)
                doc_set = result.scalar_one_or_none()
                if doc_set:
                    doc_set_id = uuid_value
                else:
                    task_stmt = select(IngestionTask).where(
                        IngestionTask.id == uuid_value,
                        IngestionTask.status == IngestionStatus.COMPLETED.value,
                    )
                    task_result = await session.execute(task_stmt)
                    task = task_result.scalar_one_or_none()

                    if not task or not task.documentation_set_id:
                        raise ValueError(
                            f"No completed documentation task found with ID {uuid_value}"
                        )

                    logger.info(
                        f"Found task ID {uuid_value}, mapping to doc set ID {task.documentation_set_id}"
                    )

                    doc_set_id = task.documentation_set_id
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

        logger.info(f"Using documentation set ID: {doc_set_id} for chat")

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
