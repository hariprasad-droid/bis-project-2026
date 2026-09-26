# BIS SAHAYAK — COMPLETE PROJECT MASTER SUMMARY

## 1. Project Overview
### Project Name
**BIS Sahayak**

### Problem Statement
**PS ID: 26107 — Smart Automation**

### Team
**Team Rockstar — Team ID 095**

### Core Idea
BIS Sahayak is an **evidence-grounded conversational interface for discovering, navigating, and understanding Indian Standards and BIS services**.

The project's central objective is simple:
> **A user should be able to ask a question in natural language and receive an understandable answer that is backed by actual BIS documentation, clauses, standards, and official links.**

The system is specifically designed around a critical safety principle:
> **The AI must not guess.**

Instead of allowing an LLM to answer using general knowledge, BIS Sahayak first retrieves relevant evidence from the BIS knowledge base, verifies that evidence, and only then generates the explanation.

The project's own material summarizes the interaction as:
**Ask → Retrieve → Verify → Understand.** 

---

## 2. The Problem BIS Sahayak Is Solving
Indian Standards and BIS services contain a large amount of information. There can be:
* standards
* IS codes
* certification procedures
* testing requirements
* licensing information
* hallmarking information
* CRS information
* ISI-related information
* laboratory information
* manuals
* gazettes
* technical documentation
* revisions
* withdrawn/superseded standards

The problem is not necessarily that information does not exist. The problem is:
> **Finding the correct information and understanding it can be difficult.**

The uploaded project identifies this as:
**“Information exists. Discovery is the bottleneck.”** 

---

## 3. Existing Discovery Problem
The current information-discovery process can involve multiple portals and different categories of information. A person may have to understand which BIS service they need, which standard applies, which IS code is relevant, which document contains the requirement, which clause contains the answer, whether a document is current, whether a standard has been superseded, which testing procedure applies, and which laboratory information is relevant.

### 3.1 Fragmented Portal Traversal
Users may need to navigate different services and information sources.
For example: **Standards → Certification → Testing → Hallmarking → Consumer information**
Instead of one conversational entry point, the user may need to know where to search. The project specifically describes this as **multi-silo navigation**. 

---

## 4. Taxonomy Barrier
A traditional search process may require users to know technical terminology before searching effectively.
For example, a user may not know the exact IS code, committee number, standard title, technical terminology, or relevant BIS service. A normal user might simply ask:
> “What certification do I need for this product?”

BIS Sahayak is designed to accept this kind of natural-language intent rather than requiring the user to already understand BIS's internal taxonomy. The project calls this the **taxonomy hurdle**. 

---

## 5. Manual Information Synthesis
Another problem is that information may be distributed across documents. A user might have to:
1. find a document
2. download it
3. search inside it
4. find a clause
5. find another document
6. compare requirements
7. understand technical language
8. determine whether the document is current
9. combine the information

This creates a manual research burden. BIS Sahayak is intended to automate much of this discovery and synthesis while keeping the underlying evidence visible.

---

## 6. Proposed Solution
BIS Sahayak introduces a:
### **Grounded Conversational Layer**
The user interacts with the system using natural language. For example:
> “What BIS requirements apply to this product?”
> “Which standard covers this product?”
> “Explain this BIS requirement in simple language.”

The system then follows this flow:
**User Question → Understand Query → Retrieve Relevant BIS Evidence → Verify Evidence → Generate Grounded Explanation → Show Citation / Document / Clause / Official Link**

This is fundamentally different from simply connecting a chatbot to an LLM.

---

## 7. Why the Project Uses RAG
The core technology is a **Retrieval-Augmented Generation architecture**.
A general LLM can generate fluent answers, but fluency does not guarantee that the answer is supported by the correct BIS document. For a regulatory or standards-related application, an incorrect answer could cause serious misunderstanding.
Therefore, BIS Sahayak does not want:
**Question → LLM → Answer**
Instead, it wants:
**Question → Retrieval → Verification → Grounded LLM → Answer**

The uploaded project explicitly describes a **strict dual-stage pipeline that decouples evidence retrieval from explanation generation**. 

---

## 8. Complete System Workflow
The complete BIS Sahayak workflow can be understood in four major stages.

### Stage 1 — ASK
The user asks a question naturally. They do not necessarily need to know IS numbers, committees, or document titles.

### Stage 2 — RETRIEVE
The system identifies the relevant information from the BIS knowledge base using document embeddings, chunked documents, vector search, keyword overlap, and similarity ranking. The architecture uses **Qdrant / ChromaDB with hybrid retrieval**.

### Stage 3 — VERIFY
The system checks relevance, publication information, active status, document metadata, version information, and whether enough evidence exists. The project describes this as the **Gatekeeper** stage. If evidence is insufficient, it responds:
> **“I don't have sufficient evidence to answer this accurately.”**

### Stage 4 — UNDERSTAND
Once verified, the LLM generates an explanation. Its job is to simplify, organize, explain, summarize, translate, and present the retrieved information. The final component is a **Grounded LLM** that synthesizes explanations strictly from retrieved context. 

---

## 9. The Most Important Principle: DO NOT GUESS
This is the heart of BIS Sahayak. A normal chatbot may try to answer every question. BIS Sahayak should behave differently:
- If evidence exists: **Answer + Evidence**
- If evidence is incomplete: **Request clarification / provide safe fallback**
- If evidence does not exist: **Do not fabricate an answer.**

The project explicitly says:
> **“CENTRAL RULE · PROPOSED CONVERSATIONAL LAYER CANNOT GUESS.”** 

---

## 10. Input & Parsing Layer
The first technical component is the input-processing layer which includes:
- **Language Detection:** The system identifies the language (e.g., using Bhashini/Indic capabilities) for Hindi, Tamil, English.
- **Query Expansion:** Identifying synonyms and related terminology.
- **Standards Terminology Extraction:** Identifying IS codes, product keywords, and terminology.

---

## 11. FastAPI Gateway
The project uses **Python FastAPI** as the API gateway acting as the bridge between the Frontend and the AI/RAG backend.

---

## 12. Vector Search (Hybrid Search)
The system uses dense embeddings + keyword overlap to search large quantities of BIS documents.
- **Semantic retrieval:** Understands conceptual similarity.
- **Keyword retrieval:** Helps preserve exact terminology like IS codes and product names.

---

## 13. BIS Knowledge Base Preparation
The structured knowledge base lifecycle:
**Collect → Parse → Clean → Chunk → Embed → Index & Sync**

- **Clause-level Chunking:** Documents are divided into smaller sections (clauses) instead of whole documents.
- **Version Control:** Distinguishes between Current/Active Standards and Withdrawn/Superseded Standards using metadata filtering.

---

## 14. Answer Generation
The final response contains:
- **Simple explanation**
- **Source Document**
- **Standard number (IS code)**
- **Exact Clause**
- **Official URL to BIS source**

---

## 15. Who Benefits?
- **MSMEs & Startups:** Discover applicable compliance requirements quickly.
- **Industrial Manufacturers:** Understand standards, testing, and revisions.
- **Students & Academics:** Explore standards naturally.
- **General Consumers:** Check ISI marks, CRS, and hallmarking.
- **BIS Helpdesk Staff:** Deflect repetitive navigation queries.

---

## 16. Development Roadmap
### Phase 1 — Core Ingestion
Collect top 100 IS manuals, clean, chunk, and create vector store.
### Phase 2 — RAG & Citations
Build FastAPI backend, Next.js interface, retrieval system, and citations.
### Phase 3 — Guardrails
Implement verification layer, hallucination boundaries, version checks.
### Phase 4 — Multilingual
Expand support using Indic-language technology (Bhashini) for Hindi and Tamil.

---

## 17. Evaluation
The project uses a benchmark evaluation framework:
- **Grounding & Faithfulness:** RAGAS faithfulness score > 0.90
- **Citation Correctness:** 100% exact match for clause and IS code.
- **Abstention Behavior:** Zero speculation on unsupported queries.
- **Multilingual Fluency:** Human evaluation for Indic languages.

---

## 18. Final Project Concept Architecture

```text
                  BIS SAHAYAK
                       │
                       ▼
              NATURAL LANGUAGE
                  USER QUERY
                       │
                       ▼
               QUERY UNDERSTANDING
                       │
                       ▼
              HYBRID BIS RETRIEVAL
             ┌─────────┴─────────┐
             │                   │
       Semantic Search      Keyword Search
             │                   │
             └─────────┬─────────┘
                       ▼
                RELEVANT CHUNKS
                       │
                       ▼
                 GATEKEEPER
                       │
             ┌─────────┴─────────┐
             │                   │
          Evidence             No Evidence
             │                   │
             ▼                   ▼
       Version Check       Clarification /
             │             Safe Fallback
             ▼
        GROUNDED LLM
             │
             ▼
      SIMPLE EXPLANATION
             │
             ├── IS Code
             ├── Clause
             ├── Document
             └── Official Link
```

---

## 19. How to Explain in One Minute
> **“BIS Sahayak is an evidence-grounded conversational AI system designed to make Indian Standards and BIS services easier to discover and understand. Instead of forcing users to know IS codes, technical terminology, or the correct BIS portal, users can ask questions naturally. The system understands the query, retrieves relevant information from a version-controlled BIS knowledge base using hybrid vector search, verifies whether the retrieved evidence is relevant and current, and then uses a grounded LLM to explain the information in simple language. Every important answer is connected to its source, clause, document, and official BIS link. If sufficient evidence is unavailable, the system does not guess; it asks for clarification or safely falls back to official support. The core principle is Ask, Retrieve, Verify, Understand.”**
