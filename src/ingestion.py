import fitz
import os
import re


def read_pdf(file_path):
    """
    Open a PDF, extract text chunks, close the document, then return.
    Returns a tuple: (chunks, total_pages)
    total_pages is captured BEFORE the loop so doc.close() is safe.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF not found: {file_path}")

    doc = fitz.open(file_path)
    chunks = []
    chunk_size = 400
    overlap = 50

    # Capture page count BEFORE anything else — never call len(doc) after close
    total_pages = len(doc)

    for page_num, page in enumerate(doc):
        text = page.get_text().strip()

        if not text or len(text) < 50:
            continue

        text = re.sub(r'\s+', ' ', text).strip()
        words = text.split()

        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)

            if len(chunk_text) < 100:
                continue

            chunks.append({
                "text": chunk_text,
                "page": page_num + 1,
                "source": os.path.basename(file_path),
                "source_path": file_path,
                "chunk_id": f"{os.path.basename(file_path)}_p{page_num+1}_c{i}"
            })

    # Close AFTER the loop is done — total_pages is already saved above
    doc.close()

    print(f"✅ Loaded: {os.path.basename(file_path)}")
    print(f"   Pages: {total_pages}")
    print(f"   Chunks: {len(chunks)}")

    # Return both so callers never need to re-open the file
    return chunks, total_pages


def read_multiple_pdfs(file_paths):
    all_chunks = []
    for file_path in file_paths:
        try:
            chunks, _ = read_pdf(file_path)   # unpack tuple; ignore page count here
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"❌ Error loading {file_path}: {e}")
    print(f"\n✅ Total chunks: {len(all_chunks)}")
    return all_chunks
