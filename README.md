# AgenticAI_LLMOrchestration_CVChatbot

# 🔬 LLM-Orchestrated Agentic AI Researcher 📚

An autonomous research assistant that turns any research query into a structured, downloadable PDF report — powered by an orchestration of specialised LLM agents, each handling a distinct step of the workflow.

🚀 **Live demo:** [Hugging Face Space](https://huggingface.co/spaces/yasinemirkutlu44/LLM-Orchestrated_Agentic_AI_Researcher)

---

## ✨ What It Does

Enter a research topic and the system will:

1. **Validate** your query to ensure it's meaningful and actionable.
2. **Plan** Plan a set of complementary web searches covering different aspects of the research query. For example, for "recent advancements in Large Language Models", the planner might produce one search on multimodal capabilities and another on agentic reasoning benchmarks.
3. **Search** the web in parallel across those angles.
4. **Synthesise** the findings into a structured markdown report.
5. **Export** the report as a downloadable PDF.

All progress is streamed to the UI in real time, with a progress bar tracking each stage.

---

## 🧠 Agent Architecture

The system orchestrates five specialised agents, each with a single responsibility and typed outputs (via Pydantic) for reliable data flow between them.

| Agent | Role | Output |
|-------|------|--------|
| 🛡️ **Query Validator** | Decides whether the user's query is a meaningful research question or gibberish. Blocks empty/nonsensical inputs before any expensive calls. | `QueryValidationInput` (`is_valid`, `reason`) |
| 🗺️ **Search Planner** | Breaks the query into targeted, complementary search terms covering different aspects of the research query. | `WebSearchPlan` (list of `WebSearchItem`) |
| 🌐 **Research Assistant** | Performs a web search for each planned term and returns a dense 2–3 paragraph summary. Runs in parallel across all search items. | Summary text per search |
| ✍️ **Senior Writer** | Synthesises all search summaries into a cohesive, multi-section markdown report (~1,500+ words). | `ReportOutline` (`summary`, `report`, `suggested_questions`) |
| 📄 **PDF Saver** | Renders the markdown report as a styled PDF and saves it to disk. | File path to the generated PDF |

All orchestration happens in the **`Orchestrator`** class (`LLM_Orchestrator.py`), which coordinates the agents and streams progress updates to the UI via an async generator.

---

## 🏗️ How It Works
┌─────────────────┐
│   User Query    │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Query Validator │ ◄── rejects gibberish early
└────────┬────────┘
         ▼
┌─────────────────┐
│ Search Planner  │ ◄── plans N targeted searches
└────────┬────────┘
         ▼
┌─────────────────┐
│ Research        │ ◄── parallel web searches
│ Assistants (N)  │     via asyncio.gather
└────────┬────────┘
         ▼
┌─────────────────┐
│ Senior Writer   │ ◄── synthesises findings
└────────┬────────┘
         ▼
┌─────────────────┐
│  PDF Saver      │ ◄── exports downloadable PDF
└─────────────────┘
