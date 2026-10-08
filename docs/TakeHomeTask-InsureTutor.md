# Take-Home Task: InsureTutor Demo

**Role:** AI Full Stack Engineering Intern, Asian Institute of Digital Finance (AIDF), National University of Singapore
**Due:** 3 days after you received this task
**Submission** Send your git link and anything you think is important

---

## Task

Build a working demo of InsureTutor, an AI tutor that answers questions about specific insurance plans. The demo must include the three capabilities below. How you design and implement them is up to you.

---

## Required Capabilities

| Capability | Description |
|---|---|
| **Chat and answer** | Users ask questions in a chat interface and receive answers within a conversation. |
| **Retrieval-augmented generation (RAG)** | Answers are grounded in a collection of insurance plan documents and cite the sources they draw on. |
| **Guardrails** | Controls that keep the tutor's answers safe, accurate and within scope. |

---

## Requirements

- [ ] The application can be complied by docker
- [ ] The system should be bilingual: English and Chinese, framework and data store may be used. Bonus: Both Simplified and Traditional Chinese are included.
- [ ] Store any API you used in `.env`, never commit it, and provide an `.env.example` with placeholder values
- [ ] Based on the material attached with this email
- [ ] Commit incrementally, with meaningful commit messages

---

## Deliverables

1. **GitHub repository** containing the source code, `Dockerfile` and `docker-compose.yml`
2. **`README.md`** covering how to run the demo, the architecture and your key design decisions

Shortlisted candidates will be invited to a follow-up session to present the demo and discuss their decisions.

---

## Submission

Share the repository with the reviewer account named in your invitation email, or email a zip of the repository, including the `.git` directory

---

## Evaluation Criteria

| Dimension | What we're looking for |
|---|---|
| **Chat and answer** | A working, coherent conversational experience |
| **RAG** | Answers grounded in the documents, with accurate citations |
| **Guardrails** | Safe, in-scope behaviour that holds up under misuse |
| **Engineering** | Runs through Docker; readable, well-structured code |
| **Documentation** | Clear documents for others to understand |

AI coding tools are encouraged. Review, understand and own everything you submit; you will be asked to explain it.