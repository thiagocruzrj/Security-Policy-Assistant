# Query Pseudocode: Question to Grounded Answer with Citations

This document provides pseudocode for the query flow that takes a user question and returns a grounded answer with policy citations, enforcing security trimming and answer guardrails.

## Pseudocode
```python
def answer_question(user, question):
    # 1) Build security filter (security trimming)
    user_groups = get_user_groups(user)  # Entra groups
    filter_expr = build_filter(user_groups=user_groups)

    # 2) Retrieve (hybrid)
    q_vec = embed(question)
    results = ai_search_hybrid(
        text=question,
        vector=q_vec,
        top_k=5,
        filter=filter_expr,
        use_semantic_ranker=True
    )

    if not results:
        return "I couldn't find this in the approved security policies."

    # 3) Prompt (grounded + citations)
    context = "\n\n".join([f"[{r.id}] {r.content}" for r in results])
    system = (
      "You are the Security Policy Assistant. "
      "Answer ONLY using the provided policy excerpts. "
      "If the answer isn't in the excerpts, say you don't know. "
      "Always include citations like [chunk-id]."
    )

    prompt = f"{context}\n\nUser question: {question}"

    # 4) Generate
    completion = azure_openai_chat(system=system, user=prompt)

    # 5) Post-check: ensure citations exist
    if not has_citations(completion):
        return "I can’t answer from policy sources. Please ask Security for clarification."

    return completion
```

## Steps Explained
1. **Build security filter**: Restrict retrieval to chunks the user is allowed to access (security trimming)
2. **Hybrid retrieval**: Use both keyword and vector search, with semantic ranker for relevance
3. **Grounded prompt**: Construct prompt with retrieved chunks and enforce citation requirements
4. **LLM generation**: Use Azure OpenAI to generate the answer
5. **Post-check**: Ensure answer includes citations; otherwise, refuse to answer

---
This query flow ensures answers are grounded in approved policy content, security-trimmed, and always include citations for auditability.