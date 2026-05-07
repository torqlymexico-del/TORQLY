from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.enums import UserRole
from app.schemas.bot import BotCommandRequest, BotMessageRead
from app.services.internal_bot import execute_command, list_history


router = APIRouter(prefix="/bot", tags=["internal-bot"])


@router.post("/command", response_model=BotMessageRead)
def run_bot_command(
    payload: BotCommandRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
):
    result = execute_command(db, command=payload.command, actor=current_user)
    return BotMessageRead(**result)


@router.get("/history", response_model=list[BotMessageRead])
def bot_history(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
    limit: int = Query(default=50, ge=1, le=200),
):
    return [BotMessageRead.model_validate(item) for item in list_history(db, user=current_user, limit=limit)]
