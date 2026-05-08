from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, get_current_user
from app.models import TeamMessage

router = APIRouter(prefix="/team-chat", tags=["team-chat"])


class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class MessageOut(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_role: str
    content: str
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[MessageOut])
def get_messages(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(get_current_user),
    since_id: int = Query(default=0),
    limit: int = Query(default=60, le=200),
) -> list[MessageOut]:
    company_id = current_company_id(current_user)
    q = (
        select(TeamMessage)
        .where(TeamMessage.company_id == company_id)
        .order_by(TeamMessage.id.desc())
        .limit(limit)
    )
    if since_id:
        q = select(TeamMessage).where(
            TeamMessage.company_id == company_id,
            TeamMessage.id > since_id,
        ).order_by(TeamMessage.id.asc()).limit(limit)
    msgs = list(db.scalars(q).all())
    if not since_id:
        msgs = list(reversed(msgs))
    return [
        MessageOut(
            id=m.id,
            user_id=m.user_id,
            user_name=m.user.name if m.user else "?",
            user_role=m.user.role if m.user else "",
            content=m.content,
            created_at=m.created_at.isoformat(),
        )
        for m in reversed(msgs)
    ]


@router.post("/", response_model=MessageOut, status_code=201)
def send_message(
    payload: MessageIn,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> MessageOut:
    company_id = current_company_id(current_user)
    msg = TeamMessage(
        company_id=company_id,
        user_id=current_user.id,
        content=payload.content.strip(),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return MessageOut(
        id=msg.id,
        user_id=msg.user_id,
        user_name=current_user.name,
        user_role=current_user.role,
        content=msg.content,
        created_at=msg.created_at.isoformat(),
    )
