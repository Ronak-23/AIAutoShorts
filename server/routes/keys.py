"""
server/routes/keys.py
=====================
REST API endpoints for managing multi-tenant Bring Your Own Key (BYOK) credentials.
Enforces AES-256-GCM encryption and masked preview outputs (zero-plaintext leakage).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from server.routes.auth import get_current_user
from server.auth.crypto import encrypt_api_key, validate_provider_key
from core.db.repository import (
    save_user_api_key,
    list_user_api_keys,
    get_user_api_key,
    delete_user_api_key
)

router = APIRouter(prefix="/api/keys", tags=["BYOK API Keys"])


class AddKeyRequest(BaseModel):
    provider: str = Field(..., description="Provider: groq, gemini, openrouter, pexels, elevenlabs")
    api_key: Optional[str] = Field(None, description="Plaintext API key to be encrypted and stored")
    key: Optional[str] = Field(None, description="Alternative field for api_key")
    key_alias: Optional[str] = Field("Default", description="User-assigned alias for the key")
    skip_validation: Optional[bool] = Field(False, description="Whether to bypass preflight validation")

    @property
    def raw_key(self) -> str:
        return (self.api_key or self.key or "").strip()


class ValidateKeyRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    key: Optional[str] = None

    @property
    def raw_key(self) -> str:
        return (self.api_key or self.key or "").strip()


@router.get("", response_model=List[Dict[str, Any]])
async def get_my_keys(current_user: dict = Depends(get_current_user)):
    """Lists all configured API keys for the authenticated user with masked previews."""
    return list_user_api_keys(user_id=current_user["id"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_key(payload: AddKeyRequest, current_user: dict = Depends(get_current_user)):
    """
    Validates, encrypts with AES-256-GCM, and stores a provider API key.
    Raw keys are never persisted in plaintext or returned in the response.
    """
    prov = payload.provider.lower().strip()
    valid_providers = {"groq", "gemini", "openrouter", "pexels", "elevenlabs"}
    if prov not in valid_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider '{payload.provider}'. Must be one of: {', '.join(sorted(valid_providers))}"
        )

    raw_k = payload.raw_key
    if len(raw_k) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key is too short (must be at least 5 characters)."
        )

    # 1. Preflight validation
    if not payload.skip_validation:
        is_valid, reason = validate_provider_key(prov, raw_k)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Key verification failed: {reason}"
            )

    # 2. Encrypt with AES-256-GCM
    try:
        enc_data = encrypt_api_key(raw_k)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Encryption error: {str(e)}"
        )

    # 3. Store encrypted blobs in SQLite
    created = save_user_api_key(
        user_id=current_user["id"],
        provider=prov,
        encrypted_key=enc_data["encrypted_key"],
        nonce=enc_data["nonce"],
        tag=enc_data["tag"],
        key_preview=enc_data["key_preview"],
        key_alias=payload.key_alias or "Default"
    )

    return created


@router.post("/validate")
async def test_key(payload: ValidateKeyRequest, current_user: dict = Depends(get_current_user)):
    """Tests a provider API key without storing it."""
    raw_k = payload.raw_key
    is_valid, msg = validate_provider_key(payload.provider, raw_k)
    return {
        "valid": is_valid,
        "provider": payload.provider,
        "message": msg
    }


@router.delete("/{key_id}")
async def remove_key(key_id: str, current_user: dict = Depends(get_current_user)):
    """Revokes and deletes an API key."""
    found = get_user_api_key(key_id=key_id, user_id=current_user["id"])
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found or not owned by authenticated user."
        )

    deleted = delete_user_api_key(key_id=key_id, user_id=current_user["id"])
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete key record.")

    return {
        "status": "success",
        "message": f"API key {found.get('key_preview')} deleted successfully."
    }
