import faiss
import numpy as np
import requests
import json
import time

OLLAMA_URL = "http://localhost:11434/api/generate"

# ============================================
# STEP 1 — Policy chunks
# ============================================

chunks = [
    "Section 4.1: All employees are classified as Probationary or Regular. Probationary period is 90 days.",
    "Section 4.2: Probationary employees require 2 weeks written notice before termination.",
    "Section 4.3: Regular employees require 4 weeks written notice before termination.",
    "Section 4.4: Employees on Performance Improvement Plan may be terminated with 2 weeks notice if targets not met in 60 days.",
    "Section 5.1: Annual leave entitlement is 15 days per year for all employees.",
    "Section 5.2: Sick leave is capped at 10 days per calendar year.",
    "Section 6.1: Contractors are not entitled to notice period beyond their signed agreement.",
    "Section 7.1: All disputes must be escalated to HR Director within 5 working days.",
]

# ============================================
# STEP 2 — Embed each chunk
# ============================================

def get_embedding(text):
    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": text}
    )
    return response.json()["embedding"]

print("Building knowledge base...")
print("Embedding chunks...")

embeddings = []
for i, chunk in enumerate(chunks):
    emb = get_embedding(chunk)
    embeddings.append(emb)
    print(f"  ✅ Chunk {i+1}/{len(chunks)} embedded")

# ============================================
# STEP 3 — Build FAISS index
# ============================================

matrix = np.array(embeddings).astype("float32")
faiss.normalize_L2(matrix)
index = faiss.IndexFlatIP(matrix.shape[1])
index.add(matrix)

print(f"\n✅ Knowledge base ready — {len(chunks)} chunks indexed")

# ============================================
# STEP 4 — Ask function
# ============================================

def ask(question):
    print(f"\n{'='*50}")
    print(f"Question: {question}")

    # Search FAISS
    qemb = np.array([get_embedding(question)]).astype("float32")
    faiss.normalize_L2(qemb)
    scores, indices = index.search(qemb, 3)

    # Get top 3 chunks
    retrieved = []
    print("\nRetrieved chunks:")
    for score, idx in zip(scores[0], indices[0]):
        chunk = chunks[idx]
        retrieved.append(chunk)
        status = "✅" if score > 0.65 else "⚠️"
        print(f"  {status} Score {score:.3f}: {chunk[:60]}...")

    # Guardrail — weak evidence check
    if scores[0][0] < 0.65:
        print("\n🛑 GUARDRAIL: Evidence too weak — refusing to answer")
        return

    # Build context
    context = "\n".join(retrieved)

    # Prompt
    prompt = f"""You are an HR compliance agent.
STRICT RULES:
- Answer ONLY using the policy context below
- Do NOT use outside knowledge
- Respond in JSON only
- Keep answer and reasoning brief

Question: {question}

Policy context:
{context}

Respond in this exact JSON format:
{{
  "decision": "ANSWER or CLARIFY or FLAG_CONFLICT",
  "answer": "one sentence answer",
  "citation": "Section X.X",
  "reasoning": "under 15 words"
}}"""

    # Call LLM
    start = time.time()
    response = requests.post(OLLAMA_URL, json={
        "model": "qwen3.5:4b",
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0,
            "num_predict": 200,
            "num_ctx": 512,
            "stop": ["```", "\n\n\n"]
        }
    })
    latency = time.time() - start

    raw = response.json().get("response", "").strip()

    # Extract JSON cleanly
    start_idx = raw.find("{")
    end_idx = raw.rfind("}")
    if start_idx != -1 and end_idx != -1:
        raw = raw[start_idx:end_idx+1]
    elif start_idx != -1:
        raw = raw[start_idx:] + "}"

    print(f"\nResponse ({latency:.1f} sec):")

    try:
        parsed = json.loads(raw)
        decision = parsed.get('decision', 'N/A')
        answer   = parsed.get('answer',   'N/A')
        citation = parsed.get('citation', 'N/A')
        reasoning= parsed.get('reasoning','N/A')

        print(f"  Decision:  {decision}")
        print(f"  Answer:    {answer}")
        print(f"  Citation:  {citation}")
        print(f"  Reasoning: {reasoning}")

        # Flag result
        if decision == "ANSWER":
            print("  ✅ Direct answer provided")
        elif decision == "CLARIFY":
            print("  🔵 System needs more information")
        elif decision == "FLAG_CONFLICT":
            print("  🔴 Conflict detected — escalate to HR")

    except json.JSONDecodeError:
        print(f"  ❌ JSON parse failed")
        print(f"  Raw output: {raw}")

# ============================================
# STEP 5 — Run test questions
# ============================================

# Test 1 — Direct answer expected
ask("What is the notice period for a probationary employee?")

# Test 2 — Different topic
ask("How many sick days does an employee get?")

# Test 3 — Should trigger CLARIFY
ask("What notice period applies to this employee?")

# Test 4 — Should hit guardrail
ask("What is the salary increment policy?")

# Test 5 — Conflict test
ask("Can we terminate an employee on a performance plan without 4 weeks notice?")