from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models import (
    Document,
    DocumentVersion,
    DocumentNode,
    Selection,
    SelectionNode,
    GeneratedTestCase,
)

import hashlib
def save_document(
    db: Session,
    document_name: str,
    version_number: int,
    nodes: list,
):
    """
    Save parsed document into database.
    """

    # -----------------------------
    # Create / Get Document
    # -----------------------------

    document = (
        db.query(Document)
        .filter(Document.name == document_name)
        .first()
    )

    if not document:
        document = Document(name=document_name)
        db.add(document)
        db.commit()
        db.refresh(document)

    # -----------------------------
    # Create Version
    # -----------------------------

    existing_version = (
    db.query(DocumentVersion)
    .filter(
        DocumentVersion.document_id == document.id,
        DocumentVersion.version_number == version_number,
    )
    .first()
)

    if existing_version:
        return {
            "message": f"Version {version_number} already exists."
        }

    version = DocumentVersion(
        document_id=document.id,
        version_number=version_number,
    )

    db.add(version)
    db.commit()
    db.refresh(version)

    # -----------------------------
    # Save Nodes
    # -----------------------------

    previous_node = {}

    for node in nodes:

        parent = None

        if node["level"] > 0:
            parent = previous_node.get(node["level"] - 1)

        db_node = DocumentNode(
            version_id=version.id,
            parent_id=parent,
            heading=node["heading"],
            level=node["level"],
            body=node["body"],
            content_hash=node["content_hash"],
        )

        db.add(db_node)
        db.commit()
        db.refresh(db_node)

        previous_node[node["level"]] = db_node.id

    return {
        "document_id": document.id,
        "version_id": version.id,
        "nodes_saved": len(nodes),
    }
def compare_versions(db: Session, document_name: str):
    """
    Compare Version 1 and Version 2 of a document.
    """

    document = (
        db.query(Document)
        .filter(Document.name == document_name)
        .first()
    )

    if not document:
        return {"error": "Document not found"}

    versions = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_number)
        .all()
    )

    if len(versions) < 2:
        return {"error": "At least two versions are required"}

    v1 = versions[0]
    v2 = versions[1]

    nodes_v1 = (
        db.query(DocumentNode)
        .filter(DocumentNode.version_id == v1.id)
        .all()
    )

    nodes_v2 = (
        db.query(DocumentNode)
        .filter(DocumentNode.version_id == v2.id)
        .all()
    )

    # Create lookup dictionaries
    hashes_v1 = {node.heading: node.content_hash for node in nodes_v1}
    hashes_v2 = {node.heading: node.content_hash for node in nodes_v2}

    added = []
    deleted = []
    modified = []

    # Added & Modified
    for heading, hash2 in hashes_v2.items():

        if heading not in hashes_v1:
            added.append({
            "heading": heading,
            "change": "Added"
        })

        elif hashes_v1[heading] != hash2:
            modified.append({
    "heading": heading,
    "change": "Modified"
})

    # Deleted
    for heading in hashes_v1:

        if heading not in hashes_v2:
            deleted.append({
    "heading": heading,
    "change": "Deleted"
})

    return {
        "version_1": v1.version_number,
        "version_2": v2.version_number,
        "added": added,
        "modified": modified,
        "deleted": deleted,
    }
from sqlalchemy import or_

def search_document(db: Session, query: str, version_number: int = None):
    """
    Search document nodes by heading or body.
    Optionally filter by document version.
    """

    search_query = (
        db.query(DocumentNode)
        .join(DocumentVersion)
        .filter(
            or_(
                DocumentNode.heading.ilike(f"%{query}%"),
                DocumentNode.body.ilike(f"%{query}%")
            )
        )
    )

    if version_number is not None:
        search_query = search_query.filter(
            DocumentVersion.version_number == version_number
        )

    results = search_query.all()

    return [
        {
            "id": node.id,
            "heading": node.heading,
            "level": node.level,
            "body": node.body,
            "version_id": node.version_id
        }
        for node in results
    ]
def browse_document(db: Session, version_number: int = 2):
    """
    Return the document hierarchy from the database.
    """

    version = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.version_number == version_number)
        .first()
    )

    if not version:
        return {"error": "Version not found"}

    nodes = (
        db.query(DocumentNode)
        .filter(DocumentNode.version_id == version.id)
        .order_by(DocumentNode.level)
        .all()
    )

    return [
        {
            "id": node.id,
            "heading": node.heading,
            "level": node.level,
            "parent_id": node.parent_id,
        }
        for node in nodes
    ]
def create_selection(db: Session, name: str):
    """
    Create a new selection.
    """

    selection = Selection(name=name)

    db.add(selection)
    db.commit()
    db.refresh(selection)

    return {
        "selection_id": selection.id,
        "name": selection.name
    }
def add_nodes_to_selection(
    db: Session,
    selection_id: int,
    node_ids: list[int]
):
    """
    Add document nodes to a saved selection.
    """

    selection = (
        db.query(Selection)
        .filter(Selection.id == selection_id)
        .first()
    )

    if not selection:
        return {"error": "Selection not found"}

    for node_id in node_ids:

        exists = (
            db.query(SelectionNode)
            .filter(
                SelectionNode.selection_id == selection_id,
                SelectionNode.node_id == node_id
            )
            .first()
        )

        if exists:
            continue

        db.add(
            SelectionNode(
                selection_id=selection_id,
                node_id=node_id
            )
        )

    db.commit()

    return {
        "message": "Nodes added successfully."
    }
def get_selection_context(db: Session, selection_id: int):
    """
    Retrieve the combined context for a saved selection.
    """

    selection = (
        db.query(Selection)
        .filter(Selection.id == selection_id)
        .first()
    )

    if not selection:
        return {"error": "Selection not found"}

    context = []

    for selection_node in selection.nodes:

        node = selection_node.node

        context.append(
            {
                "heading": node.heading,
                "body": node.body
            }
        )

    return {
        "selection": selection.name,
        "sections": context
    }
def save_generated_testcase(
    db: Session,
    selection_id: int,
    llm_provider: str,
    prompt: str,
    generated_output: str,
    source_hash: str
):
    testcase = GeneratedTestCase(
        selection_id=selection_id,
        llm_provider=llm_provider,
        prompt=prompt,
        generated_output=generated_output,
        source_hash=source_hash,
    )

    db.add(testcase)
    db.commit()
    db.refresh(testcase)

    return {
        "testcase_id": testcase.id
    }
def compute_selection_hash(selection):
    text = ""

    for node in selection.nodes:
        text += node.node.content_hash

    return hashlib.sha256(text.encode()).hexdigest()
def check_staleness(db: Session, testcase_id: int):

    testcase = (
        db.query(GeneratedTestCase)
        .filter(GeneratedTestCase.id == testcase_id)
        .first()
    )

    if not testcase:
        return {"error": "Test case not found"}

    selection = (
        db.query(Selection)
        .filter(Selection.id == testcase.selection_id)
        .first()
    )

    current_hash = compute_selection_hash(selection)

    stale = current_hash != testcase.source_hash

    testcase.is_stale = stale

    db.commit()

    return {
        "testcase_id": testcase.id,
        "is_stale": stale
    }
