import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, get_current_user
from app.models import TeamMessage

router = APIRouter(prefix="/team-chat", tags=["team-chat"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent.parent / "uploads" / "chat"

ALLOWED_MIME_PREFIXES = ("image/", "video/", "audio/")
ALLOWED_MIME_EXACT = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip",
    "text/plain",
}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


VALID_BRANCHES = {"local", "domicilios", "arrendadoras"}


class MessageIn(BaseModel):
    content: str = Field(default="", max_length=2000)
    branch: str = Field(default="local", max_length=30)
    attachment_url: str | None = None
    attachment_type: str | None = None
    attachment_name: str | None = None

    @model_validator(mode="after")
    def check_not_empty(self):
        if not self.content.strip() and not self.attachment_url:
            raise ValueError("Se requiere contenido o adjunto")
        if self.branch not in VALID_BRANCHES:
            raise ValueError("Rama inválida")
        return self


class MessageOut(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_role: str
    content: str
    branch: str
    attachment_url: str | None
    attachment_type: str | None
    attachment_name: str | None
    created_at: str

    model_config = {"from_attributes": True}


class UploadOut(BaseModel):
    url: str
    type: str
    name: str


def _to_out(m: TeamMessage, name: str | None = None, role: str | None = None) -> MessageOut:
    return MessageOut(
        id=m.id,
        user_id=m.user_id,
        user_name=name or (m.user.name if m.user else "?"),
        user_role=role or (m.user.role if m.user else ""),
        content=m.content,
        branch=m.branch,
        attachment_url=m.attachment_url,
        attachment_type=m.attachment_type,
        attachment_name=m.attachment_name,
        created_at=m.created_at.isoformat(),
    )


@router.post("/upload", response_model=UploadOut)
async def upload_attachment(
    file: UploadFile,
    current_user=Depends(get_current_user),
) -> UploadOut:
    content_type = file.content_type or ""
    is_allowed = (
        any(content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES)
        or content_type in ALLOWED_MIME_EXACT
    )
    if not is_allowed:
        raise HTTPException(status_code=415, detail="Tipo de archivo no permitido")

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande (máx 20 MB)")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "file").suffix.lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / filename).write_bytes(data)

    if content_type.startswith("image/"):
        attach_type = "image"
    elif content_type.startswith("video/"):
        attach_type = "video"
    elif content_type.startswith("audio/"):
        attach_type = "audio"
    else:
        attach_type = "file"

    return UploadOut(
        url=f"/uploads/chat/{filename}",
        type=attach_type,
        name=file.filename or filename,
    )


@router.get("/", response_model=list[MessageOut])
def get_messages(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(get_current_user),
    branch: str = Query(default="local"),
    since_id: int | None = Query(default=None),
    limit: int = Query(default=60, le=200),
) -> list[MessageOut]:
    company_id = current_company_id(current_user)
    base = (TeamMessage.company_id == company_id) & (TeamMessage.branch == branch)

    if since_id is not None:
        msgs = list(db.scalars(
            select(TeamMessage)
            .where(base, TeamMessage.id > since_id)
            .order_by(TeamMessage.id.asc())
            .limit(limit)
        ).all())
    else:
        rows = list(db.scalars(
            select(TeamMessage)
            .where(base)
            .order_by(TeamMessage.id.desc())
            .limit(limit)
        ).all())
        msgs = list(reversed(rows))

    return [_to_out(m) for m in msgs]


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
        branch=payload.branch,
        content=payload.content.strip(),
        attachment_url=payload.attachment_url,
        attachment_type=payload.attachment_type,
        attachment_name=payload.attachment_name,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return _to_out(msg, name=current_user.name, role=current_user.role)
