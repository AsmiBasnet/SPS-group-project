# PolicyGuard — Experiment Log

## MILESTONE — March 24, 2026

### Full Pipeline Working End to End
Hardware: Intel i5, 1.4GHz, 8GB RAM, no GPU
Model: Qwen3.5 4B (think:False)

### Results
✅ FAISS retrieval working — correct chunks returned
✅ ANSWER path working — correct answer + citation
✅ FLAG_CONFLICT path working — conflict detected
✅ GUARDRAIL working — weak evidence refused
✅ No hallucination — only uses policy context
✅ JSON output reliable with think:False fix

### Latency Results
| Question | Time |
|---|---|
| Notice period probationary | 46 sec |
| Sick days | 37 sec |
| Vague question | 33 sec |
| Out of scope (guardrail) | instant |
| Performance plan conflict | 31 sec |
| Average | 37 seconds |

### Key Discoveries
1. Qwen3.5 4B has thinking mode ON by default
2. think:False parameter fixes empty response bug
3. stop tokens must not include } character
4. num_ctx 2048 needed for reliable generation
5. Average latency 37 seconds — needs optimization in Week 6

### Problems Found
- Latency above 30 second target
- CLARIFY path not yet implemented
- No real PDF connected yet

### Next Steps
- Add CLARIFY path
- Connect real HR policy PDF
- Build Streamlit UI skeleton
