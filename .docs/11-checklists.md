# Checklists for Security Policy Assistant

## Security & Compliance Checklist
- [ ] Entra authentication + group-based authorization
- [ ] Managed identity for Search, OpenAI, and Storage
- [ ] Private endpoints + restricted public network access
- [ ] AI Search security filters (security trimming)
- [ ] Prompt injection defenses (system rules, context isolation)
- [ ] “Answer only from sources” + citations required
- [ ] Minimal logging of sensitive content; audit metadata instead

## Production Readiness Checklist
- [ ] Infrastructure as Code (IaC) with dev/stage/prod separation
- [ ] APIM rate limiting + authentication enforcement
- [ ] Retries, timeouts, and circuit breaker patterns
- [ ] Token/cost controls + caching
- [ ] Application Insights tracing + alerts

## RAG Quality Checklist
- [ ] Chunking by headings + metadata
- [ ] Hybrid retrieval + semantic ranker
- [ ] Evaluation dataset + regression tracking in Foundry prompt flow

---
Use these checklists to validate that the Security Policy Assistant meets enterprise security, production, and RAG quality standards before launch.