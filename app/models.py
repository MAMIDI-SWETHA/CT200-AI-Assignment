from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    Boolean,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    versions = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    version_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="versions")
    nodes = relationship(
        "DocumentNode",
        back_populates="version",
        cascade="all, delete-orphan",
    )


class DocumentNode(Base):
    __tablename__ = "document_nodes"

    id = Column(Integer, primary_key=True, index=True)

    version_id = Column(Integer, ForeignKey("document_versions.id"))

    parent_id = Column(
        Integer,
        ForeignKey("document_nodes.id"),
        nullable=True,
    )

    heading = Column(String, nullable=False)
    level = Column(Integer, nullable=False)

    body = Column(Text)

    content_hash = Column(String, nullable=False)

    version = relationship("DocumentVersion", back_populates="nodes")

    parent = relationship(
        "DocumentNode",
        remote_side=[id],
        backref="children",
    )


class Selection(Base):
    __tablename__ = "selections"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    nodes = relationship(
        "SelectionNode",
        back_populates="selection",
        cascade="all, delete-orphan",
    )


class SelectionNode(Base):
    __tablename__ = "selection_nodes"

    id = Column(Integer, primary_key=True)

    selection_id = Column(
        Integer,
        ForeignKey("selections.id"),
    )

    node_id = Column(
        Integer,
        ForeignKey("document_nodes.id"),
    )

    selection = relationship(
        "Selection",
        back_populates="nodes",
    )

    node = relationship("DocumentNode")


class GeneratedTestCase(Base):
    __tablename__ = "generated_testcases"

    id = Column(Integer, primary_key=True)

    selection_id = Column(
        Integer,
        ForeignKey("selections.id"),
    )

    llm_provider = Column(String)

    prompt = Column(Text)

    generated_output = Column(Text)

    source_hash = Column(String)

    is_stale = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)