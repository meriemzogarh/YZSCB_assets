"""
Shared DTOs / schema examples

Move or create typed schemas here (pydantic/dataclasses) so both frontend and backend
can import a single source of truth for request/response shapes.
"""
from typing import Optional
from dataclasses import dataclass


@dataclass
class UserInfo:
    full_name: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None
    project_name: Optional[str] = None


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: Optional[str] = None
