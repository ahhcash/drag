from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest
from app.services.chat import ChatService
from app.core.logging import logger
import uuid

router = APIRouter()
chat_service = ChatService()


@router.post("/")
async def chat(request: ChatRequest):
    try:
        # convert string id to UUID
        doc_set_id = uuid.UUID(request.documentation_id)

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
