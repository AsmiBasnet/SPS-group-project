import fitz
import os
import re


# Patterns that indicate a section heading in HR policy documents
HEADING_PATTERNS = [
    r'^(section|article|policy|chapter|part)\s+[\d\.]+',   # Section 3, Article 4.1
    r'^[\d]+[\.\d]*\s+[A-Z]',                              # 1. Leave Policy, 3.2 FMLA
    r'^[A-Z][A-Z\s]{5,}$',                                 # ALL CAPS HEADING
    r'^(purpose|scope|eligibility|procedure|overview|'
    r'definitions|responsibilities|policy statement|'
    r'background|introduction|applicability)',              # Common HR headings
]
HEADING_RE = re.compile(
    '|'.join(HEADING_PATTERNS), re.IGNORECASE
)


def _is_heading(line):
    """Return True if a text line looks like a section heading."""
    line = line.strip()
    if not line or len(line) > 80:   # headings are short
        return False
    return bool(HEADING_RE.match(line))


def _extract_sections(text):
    """
    Split page text into (heading, body) pairs.
    If no headings found, treat the whole page as one unnamed section.
    """
    lines = text.split('\n')
    sections = []
    current_heading = ""
    current_body = []

    for line in lines:
        stripped = line.strip()
        if _is_heading(stripped):
            # Save previous section
            if current_body:
                sections.append((current_heading, " ".join(current_body).strip()))
            current_heading = stripped
            current_body = []
        else:
            if stripped:
                current_body.append(stripped)

    # Save last section
    if current_body:
        sections.append((current_heading, " ".join(current_body).strip()))

    return sections if sections else [("", text.strip())]


def read_pdf(file_path):
    """
    Open a PDF, extract text chunks with section context, close document.

    Improvements over plain chunking:
    - Detects section headings and prepends them to each chunk
      so the LLM always knows which section it is reading
    - Splits by section first, then by word count within each section
    - Preserves source + page + section in metadata

    Returns: (chunks, total_pages)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF not found: {file_path}")

    doc = fitz.open(file_path)
    chunks = []
    chunk_size = 350   # words per chunk
    overlap    = 40    # word overlap between chunks

    total_pages = len(doc)   # capture BEFORE loop

    chunk_counter = 0   # simple global counter — guarantees unique IDs

    for page_num, page in enumerate(doc):
        raw_text = page.get_text().strip()

        if not raw_text or len(raw_text) < 50:
            continue

        # Clean excessive whitespace but keep newlines for heading detection
        raw_text = re.sub(r'\n{3,}', '\n\n', raw_text)
        raw_text = re.sub(r'[ \t]+', ' ', raw_text)

        sections = _extract_sections(raw_text)

        for heading, body in sections:
            if not body or len(body) < 80:
                continue

            words = body.split()

            # Prefix every chunk with its section heading for LLM context
            prefix = f"[{heading}] " if heading else ""

            for i in range(0, len(words), chunk_size - overlap):
                chunk_words = words[i:i + chunk_size]
                chunk_text  = prefix + " ".join(chunk_words)

                if len(chunk_text) < 100:
                    continue

                # Use counter as final discriminator — guaranteed unique per doc
                chunk_id = (
                    f"{os.path.basename(file_path)}"
                    f"_p{page_num+1}"
                    f"_{chunk_counter}"
                )
                chunk_counter += 1

                chunks.append({
                    "text":        chunk_text,
                    "page":        page_num + 1,
                    "section":     heading,
                    "source":      os.path.basename(file_path),
                    "source_path": file_path,
                    "chunk_id":    chunk_id
                })

    doc.close()   # AFTER loop — total_pages already saved

    print(f"✅ Loaded: {os.path.basename(file_path)}")
    print(f"   Pages: {total_pages}  |  Chunks: {len(chunks)}")

    return chunks, total_pages


def read_multiple_pdfs(file_paths):
    all_chunks = []
    for file_path in file_paths:
        try:
            chunks, _ = read_pdf(file_path)
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"❌ Error loading {file_path}: {e}")
    print(f"\n✅ Total chunks: {len(all_chunks)}")
    return all_chunks
