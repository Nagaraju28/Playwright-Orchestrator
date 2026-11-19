import secrets
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from .database import get_db
from .models.agent import Agent

def generate_secure_token(prefix: str = "agt_") -> str:
    """Generate a high-entropy cryptographically secure token."""
    return f"{prefix}{secrets.token_urlsafe(32)}"

def verify_agent_token(
    x_agent_token: str = Header(..., alias="X-Agent-Token"),
    db: Session = Depends(get_db),
) -> Agent:
    """Validate that the incoming request originates from an authorized Agent Daemon."""
    if not x_agent_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required X-Agent-Token header",
        )
    
    agent = db.query(Agent).filter(Agent.auth_token == x_agent_token).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or revoked agent authentication token",
        )
    return agent
