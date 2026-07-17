from fastapi import FastAPI
from app.crud import browse_document
from app.database import Base, engine
from app import models
from app.database import get_db
from sqlalchemy.orm import Session
from fastapi import Depends
from app.crud import compare_versions
from app.crud import search_document
from app.crud import (
    create_selection,
    add_nodes_to_selection,
    get_selection_context,
    save_generated_testcase,
    check_staleness,
)
from app.crud import save_document
# Create all database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CT-200 Document Intelligence API",
    version="1.0.0",
    description="Backend API for AI Engineering Internship Assignment"
)


@app.get("/")
def home():
    return {
        "status": "Running",
        "message": "CT-200 Document Intelligence API is running successfully!"
    }
from app.parser import PDFParser


@app.get("/parse")
def parse_pdf():

    parser = PDFParser("data/ct200_manual.pdf")

    blocks = parser.extract_blocks()

    return {
        "pages": parser.get_page_count(),
        "total_blocks": len(blocks),
        "blocks": blocks
    }
@app.get("/font-analysis")
def font_analysis():

    parser = PDFParser("data/ct200_manual.pdf")

    blocks = parser.extract_blocks()

    font_sizes = {}

    for block in blocks:
        size = block["font_size"]

        if size not in font_sizes:
            font_sizes[size] = 0

        font_sizes[size] += 1

    return dict(sorted(font_sizes.items(), reverse=True))
@app.get("/classified")
def classified_pdf():

    parser = PDFParser("data/ct200_manual.pdf")

    blocks = parser.classify_blocks()

    return {
        "total_blocks": len(blocks),
        "blocks": blocks
    }
@app.get("/hierarchy")
def hierarchy():

    parser = PDFParser("data/ct200_manual.pdf")

    data = parser.build_hierarchy()

    print(type(data))
    print(data)

    return data
@app.get("/test-heading")
def test_heading():

    parser = PDFParser("data/ct200_manual.pdf")

    blocks = parser.extract_blocks()

    result = []

    for block in blocks:
        level = parser.get_heading_level(block["text"])

        if level is not None:
            result.append({
                "text": block["text"],
                "level": level
            })

    return result
@app.get("/flatten")
def flatten():

    parser = PDFParser("data/ct200_manual.pdf")

    hierarchy = parser.build_hierarchy()

    nodes = parser.flatten_hierarchy(hierarchy)

    return nodes
@app.post("/load")
def load_document(db: Session = Depends(get_db)):

    parser = PDFParser("data/ct200_manual.pdf")

    hierarchy = parser.build_hierarchy()

    nodes = parser.flatten_hierarchy(hierarchy)

    return save_document(
        db=db,
        document_name="CT200",
        version_number=1,
        nodes=nodes,
    )
@app.post("/load-v2")
def load_document_v2(db: Session = Depends(get_db)):

    parser = PDFParser("data/ct200_manual_v2.pdf")

    hierarchy = parser.build_hierarchy()

    nodes = parser.flatten_hierarchy(hierarchy)

    return save_document(
        db=db,
        document_name="CT200",
        version_number=2,
        nodes=nodes,
    )
@app.get("/compare")
def compare(db: Session = Depends(get_db)):

    return compare_versions(
        db=db,
        document_name="CT200"
    )
@app.get("/search")
def search(
    query: str,
    version: int = None,
    db: Session = Depends(get_db)
):
    return search_document(db, query, version)
@app.get("/browse")
def browse(
    version: int = 2,
    db: Session = Depends(get_db)
):
    return browse_document(db, version)

from pydantic import BaseModel

class SelectionCreate(BaseModel):
    name: str

class SelectionNodes(BaseModel):
    node_ids: list[int]

class TestCaseCreate(BaseModel):
    selection_id: int
    llm_provider: str
    prompt: str
    generated_output: str
    source_hash: str
@app.post("/selection")
def new_selection(
    request: SelectionCreate,
    db: Session = Depends(get_db)
):
    return create_selection(db, request.name)
@app.post("/selection/{selection_id}/nodes")
def add_nodes(
    selection_id: int,
    request: SelectionNodes,
    db: Session = Depends(get_db)
):
    return add_nodes_to_selection(
        db,
        selection_id,
        request.node_ids
    )
@app.get("/selection/{selection_id}")
def get_selection(
    selection_id: int,
    db: Session = Depends(get_db)
):
    return get_selection_context(
        db,
        selection_id
    )
@app.post("/testcase")
def create_testcase(
    request: TestCaseCreate,
    db: Session = Depends(get_db)
):
    return save_generated_testcase(
        db,
        request.selection_id,
        request.llm_provider,
        request.prompt,
        request.generated_output,
        request.source_hash,
    )
@app.get("/testcase/{testcase_id}/stale")
def stale(
    testcase_id: int,
    db: Session = Depends(get_db)
):
    return check_staleness(
        db,
        testcase_id
    )