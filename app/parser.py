import fitz
import re
import hashlib
class PDFParser:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.document = fitz.open(pdf_path)

    def get_page_count(self):
        return len(self.document)

    def extract_blocks(self):
        """
        Extract text blocks along with formatting information.
        """

        extracted_blocks = []

        for page_number, page in enumerate(self.document, start=1):

            blocks = page.get_text("dict")["blocks"]

            for block in blocks:

                if "lines" not in block:
                    continue

                for line in block["lines"]:

                    for span in line["spans"]:

                        text = span["text"].strip()

                        if not text:
                            continue

                        extracted_blocks.append({
                            "page": page_number,
                            "text": text,
                            "font": span["font"],
                            "font_size": round(span["size"], 2),
                            "bbox": span["bbox"]
                        })

        return extracted_blocks

    def classify_blocks(self):
        """
        Classify document blocks using
        heading numbering + font size + bold font.
        """

        blocks = self.extract_blocks()

        # Collect unique font sizes
        font_sizes = sorted(
            {block["font_size"] for block in blocks},
            reverse=True
        )

        title_size = font_sizes[0]

        classified = []

        for block in blocks:

            text = block["text"]

            heading_level = self.get_heading_level(text)

            is_bold = "bold" in block["font"].lower()

            # -------- Classification --------

            if block["font_size"] == title_size:
                block_type = "TITLE"

            elif heading_level == 1:
                block_type = "HEADING"

            elif heading_level is not None:
                block_type = "SUBHEADING"

            elif is_bold:
                block_type = "HEADING"

            else:
                block_type = "PARAGRAPH"

            classified.append({
                **block,
                "type": block_type,
                "level": heading_level
            })

        return classified
    def get_heading_level(self, text):
        """
        Returns heading level based on numbering.

        Examples:
        1 Introduction      -> 1
        2.1 Battery         -> 2
        2.1.1 Installation  -> 3
        Normal paragraph    -> None
        """

        match = re.match(r"^(\d+(?:\.\d+)*)", text)

        if not match:
            return None

        return len(match.group(1).split("."))
    def build_hierarchy(self):
        """
        Build a document hierarchy using heading levels.
        """

        blocks = self.classify_blocks()

        root = []
        stack = []

        for block in blocks:

            node = {
                "text": block["text"],
                "type": block["type"],
                "page": block["page"],
                "level": block["level"],
                "children": []
            }

            # Merge multiple title lines into one logical title
            if block["type"] == "TITLE":

                if root and root[0]["type"] == "TITLE":
                    root[0]["text"] += " " + block["text"]
                    stack = [root[0]]
                else:
                    root.append(node)
                    stack = [node]

                continue

            # Paragraph
            if block["type"] == "PARAGRAPH":

                if stack:
                    stack[-1]["children"].append(node)
                else:
                    root.append(node)

                continue

            # Heading/Subheading
            level = block["level"] or 1

            while len(stack) > level:
                stack.pop()

            if stack:
                stack[-1]["children"].append(node)
            else:
                root.append(node)

            if len(stack) == level:
                stack.append(node)
            else:
                stack = stack[:level]
                stack.append(node)

        return root
    def generate_hash(self, heading, body):
        """
        Generate SHA-256 hash for a node.
        """

        content = f"{heading}\n{body}"

        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    def flatten_hierarchy(self, hierarchy):
        """
        Convert the hierarchy tree into a flat list of nodes.
        """

        nodes = []

        def traverse(item):

            body = ""

            # Collect paragraph children as the node body
            for child in item["children"]:
                if child["type"] == "PARAGRAPH":
                    body += child["text"] + "\n"

            nodes.append({
                "heading": item["text"],
                "level": item["level"] if item["level"] is not None else 0,
                "body": body.strip(),
                "content_hash": self.generate_hash(item["text"], body),
                "children": item["children"]
            })

            for child in item["children"]:
                if child["type"] != "PARAGRAPH":
                    traverse(child)

        for root in hierarchy:
            traverse(root)

        return nodes