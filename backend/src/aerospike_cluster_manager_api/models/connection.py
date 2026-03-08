from __future__ import annotations

from pydantic import BaseModel, Field


class ConnectionStatus(BaseModel):
    connected: bool
    nodeCount: int
    namespaceCount: int
    build: str | None = None
    edition: str | None = None


class ConnectionProfile(BaseModel):
    id: str
    name: str
    hosts: list[str] = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    clusterName: str | None = None
    username: str | None = None
    password: str | None = None
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    createdAt: str
    updatedAt: str


class CreateConnectionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255, default="New Connection")
    hosts: list[str] = Field(min_length=1, default=["localhost"])
    port: int = Field(ge=1, le=65535, default=3000)
    clusterName: str | None = None
    username: str | None = None
    password: str | None = None
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$", default="#0097D3")


class UpdateConnectionRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    hosts: list[str] | None = Field(None, min_length=1)
    port: int | None = Field(None, ge=1, le=65535)
    clusterName: str | None = None
    username: str | None = None
    password: str | None = None
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")


class TestConnectionRequest(BaseModel):
    hosts: list[str] = Field(min_length=1)
    port: int = Field(ge=1, le=65535, default=3000)
    username: str | None = None
    password: str | None = None


class ConnectionProfileResponse(BaseModel):
    """Connection profile without password — used in API responses."""

    id: str
    name: str
    hosts: list[str] = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    clusterName: str | None = None
    username: str | None = None
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    createdAt: str
    updatedAt: str

    @classmethod
    def from_profile(cls, profile: ConnectionProfile) -> ConnectionProfileResponse:
        return cls(**profile.model_dump(exclude={"password"}))


class ConnectionWithStatus(ConnectionProfileResponse):
    status: ConnectionStatus
