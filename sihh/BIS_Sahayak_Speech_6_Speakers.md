# BIS Sahayak — Presentation Speech Script (6 Speakers)
**Team Rockstar | SIH 2026 | SIH26107**

Total time target: ~7-9 minutes (about 70-90 seconds per speaker). Adjust pace based on your slot.

---

## SPEAKER 1 — Introduction & Team (Slide 1)

"Good morning/afternoon, respected judges. We are **Team Rockstar**, Team ID **TO95**, presenting our solution for Problem Statement **SIH26107**, under the theme **Smart Automation**, in the **Software** category.

Our problem statement title is: **'AI-Powered Intelligent Assistant for Indian Standards and BIS Services for Industries and Consumers.'**

Today, we're presenting our solution called **BIS Sahayak** — an explainable, source-cited AI assistant that helps industries and consumers navigate India's standards and certification system. I'll now hand over to my teammate to explain the real-world problem we are solving."

---

## SPEAKER 2 — Problem, Importance & Solution Overview (Slide 2)

"Thank you. Let me walk you through **why this problem matters**.

Today, MSMEs, startups, students, and everyday consumers struggle to find the applicable Indian Standard for their product, the certification requirements, BIS scheme details, licensing steps, and testing rules — because all this information is scattered across **thousands of PDFs and government portals**.

**Why is this important?** This manual searching wastes enormous time, delays certification for businesses, and — most critically — it lets **counterfeit ISI and hallmark products** slip into the market, putting consumer safety at risk and eroding public trust in genuine, certified goods.

**Our solution — BIS Sahayak** — is a multilingual, RAG-based conversational AI agent. RAG means Retrieval-Augmented Generation — so instead of guessing, our AI retrieves the exact clause from official BIS documents before answering. A user can simply ask in plain language, for example: *'Which IS standard applies to my LED bulb?'* — and BIS Sahayak responds: *'IS 16102 Part 2 applies, certification is mandatory under CRS, sourced from BIS Notification clause 4.2.'* Every answer is backed by a citation, so there's no hallucination or guesswork.

It also helps users find the **nearest BIS-recognised testing lab**, guides them step-by-step through certification, and works in multiple languages for rural and regional users. In short, it takes a user end-to-end — from their first product query, all the way to certification.

Now, my teammate will explain how we plan to build this technically."

---

## SPEAKER 3 — Technical Approach (Slide 3)

"Thank you. Let's look at **how BIS Sahayak works under the hood**.

Our implementation follows a **6-step methodology**:
1. **Query Understanding** — we interpret the user's plain-language question.
2. **Semantic Retrieval** — we search a vector database of BIS standards to find the most relevant clauses.
3. **Standard Mapping** — we match the query to the exact applicable Indian Standard.
4. **Explainable Response Generation** — we generate an answer that always cites its source.
5. **Multilingual Delivery** — the answer is delivered in the user's preferred Indian language, by text or voice.
6. **Feedback & Human Escalation** — if the AI isn't confident, the query is escalated to a human BIS officer.

On the technology side, we focus on the core tools driving our MVP: we use **Python** for development, **LangChain** for LLM orchestration, and **FAISS** for vector-based semantic search. For language understanding, we use **Whisper** for speech recognition, so users can speak their query in regional languages. Our backend runs on **FastAPI**, with a **React.js** frontend for web access.

The system is designed to be **API-ready for planned integration with the BIS CARE portal and UMANG (pending access)**.

Next, my teammate will cover how feasible and viable this solution is in the real world."

---

## SPEAKER 4 — Feasibility and Viability (Slide 4)

"Thank you. Now let's talk about **feasibility and viability** — because a good idea also needs to be practical and sustainable.

**On the technical side:** BIS Sahayak is built entirely on **proven, open-source RAG and LLM components**, so there's no dependency on unproven technology. It uses a **microservice architecture**, which means we can easily scale it to new schemes and new languages without rebuilding the system. It's also **cost-effective**, since open-source models keep our inference costs low. Importantly, **BIS standards and circulars are already public documents** — so the data we need is readily available for us to ingest. And the interface itself — a simple chat or voice UI — **requires no training** for users to adopt.

**On viability**, the market opportunity is massive — India has over **6.3 crore MSMEs** who face this exact problem daily. Socially, it improves consumer safety and trust in certified products. Economically, it cuts certification delays and reduces consulting costs for businesses. Operationally, it reduces the workload on BIS staff by handling repetitive queries automatically. And regulatorily, it's fully aligned with the **BIS Act, 2016** and data protection norms.

Our **target customers** include MSMEs and startups seeking certification, manufacturers and exporters, students and researchers, general consumers, and BIS's own regional offices.

For sustainability, we propose a **hybrid revenue model** — a government-funded public assistant combined with a premium enterprise API, subscription alerts for standard revisions, and white-labelled licensing to trade bodies and exporters — making it a reusable SaaS model for other regulators too.

Now, let's look at the real impact this creates."

---

## SPEAKER 5 — Impact and Benefits (Slide 5)

"Thank you. Let me show you the **measurable impact** of BIS Sahayak.

Look at this comparison chart — **before and after** BIS Sahayak, on a scale of 1 to 5 for effort and time required:
- Finding the applicable standard drops from a score of **5 down to 1**.
- Getting certification guidance drops from **5 to 2**.
- Query resolution time drops from **4 to 1**.
- Verifying product authenticity drops from **4 to 1**.
- And language access — which used to be a major barrier — also drops from **5 to 1**.

This translates into real benefits across the board:
- **Social benefit** — building public trust in certified, standard-compliant products.
- **Safety benefit** — reducing the circulation of counterfeit and non-conforming products.
- **Economic benefit** — saving MSMEs time and consulting costs, and boosting export readiness.
- **Operational benefit** — freeing up BIS staff from repetitive queries so they can focus on higher-value work.
- **Environmental benefit** — cutting down paper-based documentation and the need for physical office visits.
- **Technological benefit** — combining NLP, RAG, and multilingual AI to advance e-governance in India.

In short, every stakeholder — from a small MSME owner to a BIS official to an everyday consumer — benefits directly.

Finally, my teammate will close with the research backing our approach and the real-world urgency behind this problem."

---

## SPEAKER 6 — Research, Real-World Evidence & Closing (Slide 6)

"Thank you. To close, I want to emphasize that this isn't a hypothetical problem — it's happening right now, across India.

Just in the recent past: **fake ISI-marked electrical cables worth over ₹5 lakh were seized in Hyderabad**; **BIS raided Amazon and Flipkart warehouses**, seizing fake ISI-marked appliances and footwear worth **₹76 lakh**; **579 plywood sheets with fake ISI and BIS marks were seized in Chennai**; and **6 tonnes of fake ISI-marked polypropylene sacks were seized in Assam**. These incidents show exactly why an accessible, trustworthy standards assistant is urgently needed — to help genuine businesses certify correctly and to help consumers verify authenticity instantly.

Our approach is grounded in primary sources — starting directly with Indian Standards documents, such as **IS 16102 (Part 2): Self-Ballasted LED Lamps**, to ground our RAG pipeline. We also studied RAG-based regulatory systems, including work on **pharmaceutical regulatory compliance and a legal-accessibility RAG system called LawPal** — and we've adapted these proven techniques specifically for India's BIS ecosystem.

**In summary:** BIS Sahayak is a multilingual, explainable, source-cited AI assistant that takes a user from confusion to certification — reducing counterfeit products, saving time and cost for MSMEs, and reducing the burden on BIS officials — built on a feasible, scalable, and sustainable technology stack.

Thank you. Team Rockstar is happy to take any questions from the panel."

---

## Quick Delivery Tips
- Practice transitions between speakers ("Now my teammate will explain...") so it flows smoothly.
- Speaker 2 and 3 are the longest — trim if you're short on time; Speaker 1 and 6 (intro/closing) should stay crisp.
- Make eye contact with judges, not the slide, during the "why it matters" and "impact" lines — those carry the most weight.
- Keep a printed or phone copy of just your own section for reference during the live pitch.
