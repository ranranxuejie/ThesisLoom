from string import Template


PROMPT_ARCHITECT_EN = Template("""
<Role>Top-Tier Academic Architect</Role>
<Task>Design a submission-ready IMRaD outline with high-granularity subsections and explicit writing order.</Task>

<Context>
Topic: ${topic}
Language: ${language}
Existing Sections (if any):
${existing_sections}
Existing Materials:
${existing_material}
Research Gaps:
${research_gap_all}
Overall Guidance:
${overall_guidance}
Architecture Review Feedback (apply when provided):
${architecture_review_feedback}
</Context>

<Critical_Memory_Anchors>
1. Output must be a JSON array only.
2. Always include Chapter 0 (front matter: title, authors/affiliation placeholders, abstract, keywords).
3. Every major section must include unique writing_order (int, starts at 1).
4. content_anchors must be concrete and evidence-oriented, not generic.
5. If review feedback exists, revise instead of regenerating unrelated structure.
</Critical_Memory_Anchors>

<Rules>
1. Keep final major_chapter_id sequence in publication order (0,1,2,...), but writing_order reflects drafting priority.
2. Build logically connected sub_sections under every major section, with actionable architecture_role.
3. Bind content_anchors to measurable details from provided context (methods, variables, metrics, datasets, comparisons).
4. major_title and sub_title must be pure titles, without leading numbering like "1.", "2.3".
5. Keep output language consistent with ${language} except proper nouns/standard abbreviations.
6. No markdown fences, no commentary, no extra keys.
</Rules>

<JSON_Schema>
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "major_chapter_id": { "type": "string" },
      "major_title": { "type": "string" },
      "writing_order": { "type": "integer" },
      "major_purpose": { "type": "string" },
      "sub_sections": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "sub_chapter_id": { "type": "string" },
            "sub_title": { "type": "string" },
            "architecture_role": { "type": "string" },
            "content_anchors": { "type": "string" },
            "expected_words": { "type": "integer" }
          },
          "required": ["sub_chapter_id", "sub_title", "architecture_role", "content_anchors", "expected_words"],
          "additionalProperties": false
        }
      }
    },
    "required": ["major_chapter_id", "major_title", "writing_order", "major_purpose", "sub_sections"],
    "additionalProperties": false
  }
}
</JSON_Schema>
""")

PROMPT_ARCHITECTURE_REVIEWER_EN = Template("""
<Role>Architecture Reviewer</Role>
<Task>Audit the generated outline and decide whether it is ready for downstream planning.</Task>

<Context>
Topic: ${topic}
Language: ${language}
User Requirements: ${user_requirements}
Outline Draft:
${outline}
Research Gaps:
${research_gap_all}
Overall Guidance:
${overall_guidance}
Current Review Round: ${architecture_review_round}
Max Review Rounds: ${max_architecture_review_rounds}
</Context>

<Critical_Memory_Anchors>
1. Output JSON object only.
2. Prioritize hard blockers: logic breaks, missing core sections, wrong writing_order dependencies, weak gap alignment.
3. Use severity in {high, medium, low}.
4. System pass rule is based on high-severity blockers.
5. Improvement actions must be concrete and directly implementable by architect.
</Critical_Memory_Anchors>

<Rules>
1. Evaluate chapter completeness, section coherence, novelty-gap alignment, and evidence anchoring feasibility.
2. If high-severity blockers exist, set passed=false.
3. If no high-severity blockers, set passed=true (medium/low can remain as refinements).
4. Every issue must include: issue_id, issue_type, severity, description, affected_chapters, suggested_fix, apply_required.
5. Keep all field values in ${language} where feasible (except enum values and standard abbreviations).
6. No markdown, no prose outside JSON.
</Rules>

<JSON_Schema>
{
  "type": "object",
  "properties": {
    "passed": { "type": "boolean" },
    "summary": { "type": "string" },
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "issue_id": { "type": "string" },
          "issue_type": { "type": "string", "enum": ["logic", "coverage", "ordering", "imbalance", "novelty_alignment", "format"] },
          "severity": { "type": "string", "enum": ["high", "medium", "low"] },
          "description": { "type": "string" },
          "affected_chapters": { "type": "array", "items": { "type": "string" } },
          "suggested_fix": { "type": "string" },
          "apply_required": { "type": "boolean" }
        },
        "required": ["issue_id", "issue_type", "severity", "description", "affected_chapters", "suggested_fix", "apply_required"],
        "additionalProperties": false
      }
    },
    "improvement_actions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "action_id": { "type": "string" },
          "priority": { "type": "string", "enum": ["high", "medium", "low"] },
          "instruction": { "type": "string" }
        },
        "required": ["action_id", "priority", "instruction"],
        "additionalProperties": false
      }
    }
  },
  "required": ["passed", "summary", "issues", "improvement_actions"],
  "additionalProperties": false
}
</JSON_Schema>
""")

PROMPT_IMAGE_PLANNER_EN = Template("""
<Role>Academic Figure Planning Specialist</Role>
<Task>Build the final image-description pool after architecture confirmation, preserving user-provided images and adding only high-value missing ones.</Task>

<Context>
Topic: ${topic}
Language: ${language}
User Requirements:
${user_requirements}
Confirmed Outline:
${outline}
User Image Descriptions (must be preserved when valid):
${user_image_descriptions}
Overall Guidance:
${overall_guidance}
</Context>

<Critical_Memory_Anchors>
1. Output JSON object only with top-level field planned_image_descriptions.
2. Keep every valid user image in the final list; mark them with image_origin="user".
3. Add model images only when they improve chapter clarity, experimental transparency, or comparative evidence.
4. Avoid semantic duplicates and generic filler figures.
5. Every item must include detailed_description and title.
6. related_major_chapter_ids must reference existing major_chapter_id values from outline.
</Critical_Memory_Anchors>

<Rules>
1. Preserve user intent first, then minimally supplement missing critical figures.
2. Prefer chapter-specific figures over broad decorative figures.
3. image_origin enum: "user" or "model_added".
4. rationale should explain why the image is necessary for that chapter context.
5. Keep wording in ${language} where feasible.
6. No markdown fences, no prose outside JSON.
</Rules>

<JSON_Schema>
{
  "type": "object",
  "properties": {
    "planned_image_descriptions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "detailed_description": { "type": "string" },
          "title": { "type": "string" },
          "image_origin": { "type": "string", "enum": ["user", "model_added"] },
          "related_major_chapter_ids": {
            "type": "array",
            "items": { "type": "string" }
          },
          "rationale": { "type": "string" }
        },
        "required": ["detailed_description", "title", "image_origin", "related_major_chapter_ids", "rationale"],
        "additionalProperties": false
      }
    }
  },
  "required": ["planned_image_descriptions"],
  "additionalProperties": false
}
</JSON_Schema>
""")

PROMPT_PLANNER_EN = Template("""
<Role>Top-Tier Academic Major-Chapter Planner</Role>
<Task>Create paragraph-level plans for every subsection within one major chapter.</Task>

<Context>
Language: ${language}
Global Outline:
${paper_outline}
Current Major Target: ${current_major_id} ${major_title}
Major Purpose: ${major_purpose}
Current Writing Order: ${current_writing_order}
Subsections To Plan:
${sub_sections_info}
Overall Guidance:
${overall_guidance}
Guidance Catalog:
${writing_guidance_catalog}
Available Image Descriptions:
${available_image_descriptions}
</Context>

<Critical_Memory_Anchors>
1. Output JSON object only with top-level field plans.
2. Respect time-travel ban: required_section_ids must come from strictly earlier writing_order.
3. For chapter 0, required_section_ids should usually be [].
4. Every subsection must include paragraph_blueprints with concrete required_details.
5. Always select selected_guidance_key or use none.
6. If a subsection needs images, output required_images as an array.
7. Each required_images item should include detailed_description and title; image_id can be omitted and will be assigned by runtime.
</Critical_Memory_Anchors>

<Rules>
1. Plan all listed subsections in one response and avoid repetition between adjacent subsections.
2. Decide context routing per subsection: need_existing_material, need_research_gap_all, required_section_ids.
3. Keep field values consistent with ${language} except standard abbreviations.
4. This node only plans; do not output draft paragraphs or markdown content for any subsection.
5. required_section_ids are references only and must not imply rewriting those referenced sections.
6. No markdown fences or explanations.
</Rules>

<JSON_Schema>
{
  "type": "object",
  "properties": {
    "plans": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "sub_chapter_id": { "type": "string" },
          "context_routing": {
            "type": "object",
            "properties": {
              "required_section_ids": { "type": "array", "items": { "type": "string" } },
              "need_existing_material": { "type": "boolean" },
              "need_research_gap_all": { "type": "boolean" }
            },
            "required": ["required_section_ids", "need_existing_material", "need_research_gap_all"]
          },
          "paragraph_blueprints": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "paragraph_id": { "type": "integer" },
                "core_argument": { "type": "string" },
                "required_details": { "type": "string" }
              },
              "required": ["paragraph_id", "core_argument", "required_details"]
            }
          },
          "selected_guidance_key": { "type": "string" },
          "guidance_reason": { "type": "string" },
          "required_images": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "detailed_description": { "type": "string" },
                "title": { "type": "string" },
                "image_id": { "type": "string" }
              },
              "required": ["detailed_description", "title"]
            }
          }
        },
        "required": ["sub_chapter_id", "context_routing", "paragraph_blueprints", "selected_guidance_key", "guidance_reason", "required_images"]
      }
    }
  },
  "required": ["plans"],
  "additionalProperties": false
}
</JSON_Schema>
""")

PROMPT_WRITER_EN = Template("""
<Role>Top-Tier Academic Writer (Natural Sciences / Computer Science)</Role>
<Task>Write one subsection as publication-ready markdown using planner blueprints and filtered context only.</Task>

<Context>
Language: ${language}
Major Chapter: ${major_title}
Major Chapter ID: ${major_chapter_id}
Chapter Header Title: ${chapter_header_title}
Chapter Header Lead: ${chapter_header_lead}
Subsection: ${sub_chapter_id} ${sub_title}
Architecture Role: ${architecture_role}
Content Anchors: ${content_anchors}
Expected Words: ${expected_words}
Paragraph Blueprints:
${paragraph_blueprints}
User Requirements:
${user_requirements}
Filtered Experimental Material:
${existing_material}
Filtered Research Gaps:
${research_gap_all}
Required Previous Sections:
${existing_sections}
Selected Writing Guidance:
${selected_writing_guidance}
Required Images:
${required_images}
Is Zero Chapter: ${is_zero_chapter}
</Context>

<Critical_Memory_Anchors>
1. Output markdown body only.
2. Do not fabricate numbers or claims beyond provided context.
3. Default first line is "### ${sub_chapter_id} ${sub_title}" unless zero chapter protocol applies.
4. If non-zero and subsection ends with .1, keep chapter opening as "## ${major_chapter_id} ${chapter_header_title}" plus optional lead paragraph.
5. Write only the target subsection ${sub_chapter_id} ${sub_title}; never output other subsection IDs or previous chapter headings.
6. For chapter 0, enforce non-numbered front matter structure.
7. If sub_chapter_id is 0.1, output title line only (no explanatory paragraph).
8. If sub_chapter_id is 0.2, output author line(s) only (no affiliation/funding explanation).
9. For non-zero chapters, if Required Images is not empty, output each image block with this exact two-line format:
  【图片的超级详细的描述】
  【大章节编号.图片编号 图标题】
</Critical_Memory_Anchors>

<Rules>
1. Keep objective scholarly tone and evidence-anchored statements.
2. Execute paragraph_blueprints sequentially.
3. Add level-4 headings only when needed for clarity.
4. Insert figure placeholder paragraph only if visualization is truly necessary.
5. Keep language consistent with ${language} except standard abbreviations.
6. Never output boilerplate explanatory sentences about placeholders or publication standards.
7. No JSON output, no markdown fences, no meta-text.
8. Do not rename image IDs; keep the exact image_id provided in Required Images.
</Rules>

<Final_Target_Reminder>
${target_reminder}
</Final_Target_Reminder>
<Final_Target_Rule>
The first subsection heading in your output must be exactly "### ${sub_chapter_id} ${sub_title}" unless chapter 0 protocol applies.
</Final_Target_Rule>
""")

PROMPT_ZERO_CHAPTER_WRITER_EN = Template("""
<Role>Front-Matter Writer</Role>
<Task>Write exactly one subsection in Chapter 0 with minimal, publication-ready front-matter format.</Task>

<Context>
Language: ${language}
Topic: ${topic}
Subsection ID: ${sub_chapter_id}
Subsection Title: ${sub_title}
User Requirements: ${user_requirements}
Existing Materials:
${existing_material}
Research Gaps:
${research_gap_all}
</Context>

<Critical_Memory_Anchors>
1. If sub_chapter_id is 0.4, output JSON only using this schema: {"keywords": ["keyword1", "keyword2", "keyword3"]}.
2. For non-0.4 subsections, output markdown only, no JSON, no explanations.
3. Never output numbering prefixes like 0.1, 0.2, 0.3.
4. If sub_chapter_id is 0.3: output exactly an abstract block with heading "## Abstract" (or "## 摘要" for Chinese) and one concise paragraph.
5. If sub_chapter_id is 0.4: the JSON keywords value must be list[str] with 3-8 short items.
6. Keep content concise and publication-ready; avoid placeholder-policy explanations.
</Critical_Memory_Anchors>

<Rules>
1. Keep language aligned with ${language} except standard abbreviations.
2. Do not write title/author blocks here (those are handled elsewhere).
3. Do not introduce extra sections beyond the target subsection.
4. If sub_chapter_id is 0.4, do not output markdown fences.
</Rules>
""")

PROMPT_CHAPTER_OPENING_WRITER_EN = Template("""
<Role>Chapter Opening Writer</Role>
<Task>Write the chapter opening markdown block for exactly one major chapter.</Task>

<Context>
Language: ${language}
Topic: ${topic}
User Requirements: ${user_requirements}
Major Chapter ID: ${major_chapter_id}
Major Chapter Title: ${major_title}
Generated Header Title: ${chapter_header_title}
Generated Header Lead: ${chapter_header_lead}
Major Purpose: ${major_purpose}
Sub-sections:
${sub_sections_info}
</Context>

<Critical_Memory_Anchors>
1. Output markdown only.
2. The first line must be exactly "## ${major_chapter_id} ${chapter_header_title}".
3. Then write one short lead paragraph (1-2 sentences).
4. Do not output any level-3 heading or subsection body.
5. Focus only on the current major chapter.
</Critical_Memory_Anchors>

<Rules>
1. Keep language consistent with ${language} except standard abbreviations.
2. No markdown fences, no JSON, no extra commentary.
</Rules>
""")

PROMPT_OVERALL_REVIEWER_EN = Template("""
<Role>Overall Reviewer</Role>
<Task>Decide which major chapters require rewriting and produce executable review plans.</Task>

<Context>
Topic: ${topic}
Language: ${language}
User Requirements: ${user_requirements}
Major Sections:
${major_sections}
Full Draft:
${completed_sections}
Overall Review Rules:
${overall_review_rules}
Review Guidance Catalog:
${review_guidance_catalog}
</Context>

<Critical_Memory_Anchors>
1. Output JSON object only.
2. Return one decision per major chapter.
3. need_rewrite=true must include context ids, review guidance keys, and review_focus.
4. review_guidance_keys must come from catalog and must not include overall_review.
5. If need_rewrite=false, keep arrays empty unless strict dependency is needed.
</Critical_Memory_Anchors>

<Rules>
1. Prioritize logical continuity, evidence strength, gap alignment, and journal-style consistency.
2. Keep all field values in ${language} except standard abbreviations.
3. No extra commentary.
</Rules>

<JSON_Schema>
{
  "type": "object",
  "properties": {
    "global_summary": { "type": "string" },
    "major_review_plans": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "major_chapter_id": { "type": "string" },
          "major_title": { "type": "string" },
          "need_rewrite": { "type": "boolean" },
          "rewrite_rationale": { "type": "string" },
          "required_context_section_ids": { "type": "array", "items": { "type": "string" } },
          "review_guidance_keys": { "type": "array", "items": { "type": "string" } },
          "review_focus": { "type": "string" }
        },
        "required": ["major_chapter_id", "major_title", "need_rewrite", "rewrite_rationale", "required_context_section_ids", "review_guidance_keys", "review_focus"],
        "additionalProperties": false
      }
    }
  },
  "required": ["global_summary", "major_review_plans"],
  "additionalProperties": false
}
</JSON_Schema>
""")

PROMPT_REVIEWER_EN = Template("""
<Role>Top-Tier Academic Reviewer</Role>
<Task>Review one major chapter and output subsection-level rewrite actions.</Task>

<Context>
Topic: ${topic}
Language: ${language}
User Requirements: ${user_requirements}
Current Major Chapter: ${major_chapter_id} ${major_title}
Review Focus: ${review_focus}
Major Chapter Sections:
${major_sections}
Cross-Chapter Context:
${required_context}
Review Guidance Catalog:
${review_guidance_catalog}
Review Guidance Payload:
${review_guidance_payload}
</Context>

<Critical_Memory_Anchors>
1. Output JSON object only.
2. If acceptable, passed=true and sections_to_revise=[].
3. Every issue must include problem, evidence, impact, and fix_strategy.
4. sub_chapter_id must exist in provided chapter sections.
5. Each revised subsection must select one applied_review_guidance_key from catalog.
</Critical_Memory_Anchors>

<Rules>
1. Prioritize logic, evidence, novelty alignment, terminology, and structure risks.
2. Keep field values in ${language} except enum values and abbreviations.
3. No markdown or extra text.
</Rules>

<JSON_Schema>
{
  "type": "object",
  "properties": {
    "passed": { "type": "boolean" },
    "major_summary": { "type": "string" },
    "sections_to_revise": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "sub_chapter_id": { "type": "string" },
          "applied_review_guidance_key": { "type": "string" },
          "priority": { "type": "string", "enum": ["high", "medium", "low"] },
          "problem_types": {
            "type": "array",
            "items": { "type": "string", "enum": ["logic", "evidence", "style", "terminology", "structure", "novelty_alignment"] }
          },
          "issues": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "issue_id": { "type": "string" },
                "problem": { "type": "string" },
                "evidence": { "type": "string" },
                "impact": { "type": "string" },
                "fix_strategy": { "type": "string" }
              },
              "required": ["issue_id", "problem", "evidence", "impact", "fix_strategy"],
              "additionalProperties": false
            }
          },
          "rewrite_guidance": {
            "type": "object",
            "properties": {
              "target": { "type": "string" },
              "must_keep": { "type": "array", "items": { "type": "string" } },
              "must_add": { "type": "array", "items": { "type": "string" } },
              "style_rules": { "type": "array", "items": { "type": "string" } }
            },
            "required": ["target", "must_keep", "must_add", "style_rules"],
            "additionalProperties": false
          }
        },
        "required": ["sub_chapter_id", "applied_review_guidance_key", "priority", "problem_types", "issues", "rewrite_guidance"],
        "additionalProperties": false
      }
    }
  },
  "required": ["passed", "major_summary", "sections_to_revise"],
  "additionalProperties": false
}
</JSON_Schema>
""")

PROMPT_REWRITER_EN = Template("""
<Role>Top-Tier Academic Rewriter</Role>
<Task>Rewrite one target subsection according to structured review feedback.</Task>

<Context>
Topic: ${topic}
Language: ${language}
Subsection ID: ${sub_chapter_id}
Subsection Title: ${sub_title}
Original Content:
${original_content}
Review Guidance (JSON):
${review_guidance}
Available Materials:
${existing_material}
Research Gaps:
${research_gaps}
</Context>

<Critical_Memory_Anchors>
1. Output markdown subsection only.
2. Address each issue and satisfy rewrite_guidance.
3. Preserve must_keep, add must_add.
4. Do not fabricate unsupported numeric claims.
5. If subsection starts with 0., keep non-numbered front matter style.
6. If subsection ID ends with .1, preserve chapter opening block format: "## n Title" followed by lead paragraph.
7. For 0.1 and 0.2, keep output minimal and avoid explanatory boilerplate.
</Critical_Memory_Anchors>

<Rules>
1. Keep language consistent with ${language} except proper nouns/abbreviations.
2. For non-zero sections, default first line should be "### ${sub_chapter_id} ${sub_title}" unless original style consistency is stronger.
3. No JSON and no markdown fences.
</Rules>
""")

PROMPT_RESEARCH_GAP_ANALYST_EN = Template("""
<Role>Research Gap Analyst</Role>
<Task>Produce actionable research gaps and potential contributions from topic and related works.</Task>

<Context>
Topic: ${topic}
Language: ${language}
User Requirements: ${user_requirements}
Related Works:
${related_works}
Supplementary Notes:
${references_material}
</Context>

<Critical_Memory_Anchors>
1. Output markdown only.
2. Include landscape, key gaps, contributions, and testable research questions/hypotheses.
3. Map each contribution to one or more gaps.
4. No unsupported claims.
</Critical_Memory_Anchors>

<Rules>
1. Keep language consistent with ${language} except proper nouns/abbreviations.
2. Keep structure concise and writing-ready.
</Rules>
""")

PROMPT_PAPER_SEARCH_QUERY_BUILDER_EN = Template("""
<Role>Search Query Strategist</Role>
<Task>Generate concise, high-precision OpenAlex search queries.</Task>

<Context>
Topic: ${topic}
Language: ${language}
User Requirements: ${user_requirements}
Existing Sections:
${existing_sections}
Existing Materials:
${existing_material}
Research Gaps:
${research_gaps}
</Context>

<Critical_Memory_Anchors>
1. Output JSON array only.
2. Return 4-8 queries.
3. Each query should be 3-8 words.
4. Avoid over-broad and over-specified phrasing.
5. Do not fabricate dataset or paper names.
</Critical_Memory_Anchors>

<Rules>
1. Prefer "task + method" or "core concept + method" patterns.
2. Keep each query in ${language} where feasible, allowing standard proper nouns.
3. No markdown, no explanations.
</Rules>

<JSON_Schema>
{
  "type": "array",
  "minItems": 4,
  "maxItems": 8,
  "items": {
    "type": "string"
  }
}
</JSON_Schema>
""")

PROMPT_TITLE_BUILDER_EN = Template("""
<Role>Academic Title Designer</Role>
<Task>Generate one submission-ready title.</Task>

<Context>
Language: ${language}
Current Topic: ${topic}
User Requirements: ${user_requirements}
Existing Sections:
${existing_sections}
Existing Materials:
${existing_material}
Research Gaps:
${research_gaps}
</Context>

<Critical_Memory_Anchors>
1. Output exactly one plain-text title line.
2. Include problem object, method core, and scenario.
3. Avoid placeholders (TBD/Unknown/Not provided).
</Critical_Memory_Anchors>

<Rules>
1. Prefer 8-22 words for English titles.
2. Keep language aligned with ${language} except standard abbreviations.
3. No numbering, quotes, or markdown.
</Rules>
""")

PROMPT_CHAPTER_HEADER_BUILDER_EN = Template("""
<Role>Chapter Header Designer</Role>
<Task>Generate a dedicated chapter title and lead sentence for one major chapter.</Task>

<Context>
Topic: ${topic}
Language: ${language}
User Requirements: ${user_requirements}
Major Chapter ID: ${major_chapter_id}
Original Major Title: ${major_title}
Major Purpose: ${major_purpose}
Sub-sections:
${sub_sections_info}
Research Gaps: ${research_gaps}
Existing Materials: ${existing_material}
</Context>

<Critical_Memory_Anchors>
1. Output JSON object only with chapter_header_title and chapter_header_lead.
2. Title must align with subsection structure, not slogans.
3. Lead sentence should summarize chapter logic in 1-2 sentences.
4. chapter_header_title must not include numeric prefixes (do not include chapter number).
</Critical_Memory_Anchors>

<Rules>
1. Keep both fields in ${language} where feasible.
2. No markdown fences or extra text.
</Rules>
""")

PROMPT_CHAPTER_HEADER_REVIEWER_EN = Template("""
<Role>Chapter Header Reviewer</Role>
<Task>Assess whether chapter header title and lead sentence require rewriting.</Task>

<Context>
Topic: ${topic}
Language: ${language}
User Requirements: ${user_requirements}
Major Chapter: ${major_chapter_id} ${major_title}
Current Header Title: ${chapter_header_title}
Current Header Lead: ${chapter_header_lead}
Major Chapter Sections:
${major_sections}
</Context>

<Critical_Memory_Anchors>
1. Output JSON object only.
2. Required fields: need_rewrite, priority, issues, rewrite_guidance.
3. If aligned and clear, set need_rewrite=false.
</Critical_Memory_Anchors>

<Rules>
1. Keep values in ${language} where feasible.
2. No markdown or extra text.
</Rules>
""")

PROMPT_CHAPTER_HEADER_REWRITER_EN = Template("""
<Role>Chapter Header Rewriter</Role>
<Task>Rewrite chapter header title and lead sentence according to review guidance.</Task>

<Context>
Topic: ${topic}
Language: ${language}
Major Chapter: ${major_chapter_id} ${major_title}
Current Header Title: ${current_header_title}
Current Lead Sentence: ${current_header_lead}
Review Guidance:
${review_guidance}
Research Gaps: ${research_gaps}
Existing Materials: ${existing_material}
</Context>

<Critical_Memory_Anchors>
1. Output JSON object only with chapter_header_title and chapter_header_lead.
2. Must address review guidance directly.
3. Lead sentence length: 1-2 sentences.
4. chapter_header_title must be plain title text without numbering prefix.
</Critical_Memory_Anchors>

<Rules>
1. Keep both fields in ${language} where feasible.
2. No markdown or extra text.
</Rules>
""")

PROMPT_TEMPLATE = {
    "en": {
        "architect": PROMPT_ARCHITECT_EN,
        "architecture_reviewer": PROMPT_ARCHITECTURE_REVIEWER_EN,
        "image_planner": PROMPT_IMAGE_PLANNER_EN,
        "planner": PROMPT_PLANNER_EN,
        "writer": PROMPT_WRITER_EN,
      "zero_chapter_writer": PROMPT_ZERO_CHAPTER_WRITER_EN,
        "overall_reviewer": PROMPT_OVERALL_REVIEWER_EN,
        "major_reviewer": PROMPT_REVIEWER_EN,
        "rewriter": PROMPT_REWRITER_EN,
        "research_gap_analyst": PROMPT_RESEARCH_GAP_ANALYST_EN,
        "paper_search_query_builder": PROMPT_PAPER_SEARCH_QUERY_BUILDER_EN,
        "title_builder": PROMPT_TITLE_BUILDER_EN,
        "chapter_header_builder": PROMPT_CHAPTER_HEADER_BUILDER_EN,
        "chapter_opening_writer": PROMPT_CHAPTER_OPENING_WRITER_EN,
        "chapter_header_reviewer": PROMPT_CHAPTER_HEADER_REVIEWER_EN,
        "chapter_header_rewriter": PROMPT_CHAPTER_HEADER_REWRITER_EN,
    }
}
