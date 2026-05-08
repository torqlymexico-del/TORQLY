from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, get_current_user
from app.models import DirectMessage, User

router = APIRouter(prefix="/direct-chat", tags=["direct-chat"])


class DmIn(BaseModel):
    content: str = Field(default="", max_length=2000)
    attachment_url: str | None = None
    attachment_type: str | None = None
    attachment_name: str | None = None

    @model_validator(mode="after")
    def check_not_empty(self):
        if not self.content.strip() and not self.attachment_url:
            raise ValueError("Se requiere contenido o adjunto")
        return self


class DmOut(BaseModel):
    id: int
    sender_id: int
    sender_name: str
    sender_role: str
    content: str
    attachment_url: str | None
    attachment_type: str | None
    attachment_name: str | None
    read_at: str | None
    created_at: str


class ContactOut(BaseModel):
    id: int
    name: str
    role: str
    branch: str
    unread: int


def _dm_to_out(m: DirectMessage) -> DmOut:
    return DmOut(
        id=m.id,
        sender_id=m.sender_id,
        sender_name=m.sender.name if m.sender else "?",
        sender_role=m.sender.role if m.sender else "",
        content=m.content,
        attachment_url=m.attachment_url,
        attachment_type=m.attachment_type,
        attachment_name=m.attachment_name,
        read_at=m.read_at.isoformat() if m.read_at else None,
        created_at=m.created_at.isoformat(),
    )


@router.get("/contacts", response_model=list[ContactOut])
def get_contacts(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> list[ContactOut]:
    company_id = current_company_id(current_user)
    users = list(db.scalars(
        select(User)
        .where(User.company_id == company_id, User.id != current_user.id, User.is_active.is_(True))
        .order_by(User.name)
    ).all())

    result = []
    for u in users:
        unread = db.scalar(
            select(func.count(DirectMessage.id))
            .where(
                DirectMessage.sender_id == u.id,
                DirectMessage.recipient_id == current_user.id,
                DirectMessage.read_at.is_(None),
            )
        ) or 0
        result.append(ContactOut(id=u.id, name=u.name, role=u.role, branch=u.branch, unread=unread))
    return result


@router.get("/{contact_id}", response_model=list[DmOut])
def get_dm_messages(
    contact_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(get_current_user),
    since_id: int | None = Query(default=None),
    limit: int = Query(default=60, le=200),
) -> list[DmOut]:
    company_id = current_company_id(current_user)
    conversation = (
        DirectMessage.company_id == company_id
    ) & or_(
        (DirectMessage.sender_id == current_user.id) & (DirectMessage.recipient_id == contact_id),
        (DirectMessage.sender_id == contact_id) & (DirectMessage.recipient_id == current_user.id),
    )

    if since_id is not None:
        msgs = list(db.scalars(
            select(DirectMessage)
            .where(conversation, DirectMessage.id > since_id)
            .order_by(DirectMessage.id.asc())
            .limit(limit)
        ).all())
    else:
        rows = list(db.scalars(
            select(DirectMessage)
            .where(conversation)
            .order_by(DirectMessage.id.desc())
            .limit(limit)
        ).all())
        msgs = list(reversed(rows))

    # Mark received messages as read
    now = datetime.now(timezone.utc)
    for m in msgs:
        if m.recipient_id == current_user.id and m.read_at is None:
            m.read_at = now
    db.commit()

    return [_dm_to_out(m) for m in msgs]


@router.post("/{contact_id}", response_model=DmOut, status_code=201)
def send_dm(
    contact_id: int,
    payload: DmIn,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> DmOut:
    company_id = current_company_id(current_user)
    msg = DirectMessage(
        company_id=company_id,
        sender_id=current_user.id,
        recipient_id=contact_id,
        content=payload.content.strip(),
        attachment_url=payload.attachment_url,
        attachment_type=payload.attachment_type,
        attachment_name=payload.attachment_name,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return _dm_to_out(msg)
