from pathlib import Path


class DocumentParser:
    SUPPORTED = {".pdf", ".docx", ".md", ".markdown", ".txt"}

    def extract_text(self, path: Path) -> list[tuple[str, int | None]]:
        """Returns list of (text, page_number) segments."""
        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED:
            raise ValueError(f"Unsupported file type: {suffix}")

        if suffix == ".pdf":
            return self._parse_pdf(path)
        if suffix == ".docx":
            return [(self._parse_docx(path), None)]
        return [(path.read_text(encoding="utf-8", errors="ignore"), None)]

    def _parse_pdf(self, path: Path) -> list[tuple[str, int | None]]:
        import fitz

        doc: fitz.Document = fitz.open(path)
        pages: list[tuple[str, int | None]] = []
        try:
            for i in range(doc.page_count):
                text = str(doc[i].get_text()).strip()
                if text:
                    pages.append((text, i + 1))
        finally:
            doc.close()
        if not pages:
            return [("", None)]
        return pages

    def _parse_docx(self, path: Path) -> str:
        from docx import Document as DocxDocument

        doc = DocxDocument(str(path))
        return "\n\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
