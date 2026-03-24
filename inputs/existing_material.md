# ThesisLoom - Codebase Architecture & Supporting Material

This repository contains the full architecture for ThesisLoom, an autonomous Python-based Multi-Agent system leveraging LLM models like gemini-3-pro. The system orchestrates the complete lifecycle of drafting, reviewing, and refining a research paper section-by-section. Below is an exhaustive structural breakdown and code abstraction to inform the Methodology section.

## 1. System State (core/state.py)
The core of ThesisLoom is built on a directed acyclic graph (using LangGraph). The state definitions hold critical information that flows across nodes: topic, research_gaps, journal_style, user_requirements, language, existing_material, generated_sections, current_section_name, current_section_content, review_feedback.

## 2. LLM Engine (core/llm.py)
A generalized module interfacing with LangChain. Specifically bound to the gemini-3-pro model for optimal logical coherence.

## 3. The Prompting Strategy (core/prompts.py)
This module codifies the system strict adherence to high-tier academic writing constraints. It contains Planner, Editor, Reviewer and Revise prompts.

## 4. Graph Nodes & Workflow (core/nodes.py & workflow.py)
Graph traversal logic: planner -> editor -> reviewer -> revise (loops back to reviewer) -> finalize.