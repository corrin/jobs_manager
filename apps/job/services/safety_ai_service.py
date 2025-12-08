"""
SafetyAIService - AI prompting for JSA/SWP generation.

Handles all AI interactions for generating safety document content including:
- Full JSA/SWP generation
- Individual hazard identification
- Control measure generation
- Task description expansion

Uses the shared LLMService for provider-agnostic LLM access.
"""

import logging
from typing import Any

from apps.job.models import Job, SafetyDocument
from apps.workflow.models import CompanyDefaults
from apps.workflow.services.llm_service import LLMService

logger = logging.getLogger(__name__)


# Default PPE for metal fabrication work
DEFAULT_PPE = [
    "Hard hat",
    "Safety glasses",
    "Steel cap boots",
    "High visibility vest",
    "Gloves (appropriate for task)",
    "Hearing protection (as required)",
]


class SafetyAIService:
    """
    Service for AI-powered safety document content generation.

    Uses the shared LLMService for provider-agnostic access to Claude, Gemini, etc.
    Generates JSA/SWP content following NZ WorkSafe guidelines.
    """

    def __init__(self):
        """Initialize the AI service."""
        self.llm = LLMService()
        logger.info(f"SafetyAIService configured with model: {self.llm.model_name}")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for safety document generation."""
        company = CompanyDefaults.objects.first()
        company_name = company.company_name if company else "Morris Sheetmetal"

        return f"""You are a workplace safety expert specializing in New Zealand safety regulations,
WorkSafe NZ guidelines, and Job Safety Analysis (JSA) creation for metal fabrication and installation work.

You work for {company_name}, a custom metal fabrication business.

Your role is to create comprehensive safety documents that:
- Follow NZ Health and Safety at Work Act 2015 requirements
- Apply the hierarchy of controls (Elimination > Substitution > Engineering > Administrative > PPE)
- Focus on practical, implementable control measures
- Consider the metal fabrication and installation context

The primary use cases are:
- On-site installation work (installing fabricated metal items at customer premises)
- Working at heights, with heavy equipment, near traffic
- Hot work (welding, grinding) in variable environments
- Manual handling of heavy fabricated items

Risk ratings:
- Low: Minor injury unlikely, proceed with standard precautions
- Moderate: Injury possible, additional controls recommended
- High: Serious injury likely without controls, must implement controls
- Extreme: Life-threatening, do not proceed without comprehensive controls and approval

Always respond with valid JSON as specified in the prompt."""

    def _call_llm(self, prompt: str, expect_json: bool = True) -> dict | str:
        """
        Make a call to the LLM via the shared LLMService.

        Args:
            prompt: The user prompt to send
            expect_json: If True, parse response as JSON

        Returns:
            Parsed JSON dict or raw string response
        """
        messages = [{"role": "user", "content": prompt}]

        if expect_json:
            return self.llm.completion_with_json(
                messages=messages,
                system_prompt=self._get_system_prompt(),
            )
        else:
            return self.llm.get_text_response(
                messages=messages,
                system_prompt=self._get_system_prompt(),
            )

    def generate_full_jsa(
        self, job: Job, context_docs: list[SafetyDocument] | None = None
    ) -> dict[str, Any]:
        """
        Generate a complete JSA for a job using AI.

        Args:
            job: The job to generate a JSA for
            context_docs: Optional list of similar JSAs to use as context

        Returns:
            Dict with JSA structure: title, description, ppe_requirements, tasks, etc.
        """
        # Build context from similar JSAs
        context_section = ""
        if context_docs:
            context_section = "\n\nREFERENCE JSAs FROM SIMILAR WORK:\n"
            for i, doc in enumerate(context_docs, 1):
                task_summaries = []
                for task in doc.tasks[:3]:  # First 3 tasks
                    task_summaries.append(
                        f"  - {task.get('summary', task.get('description', '')[:50])}"
                    )
                hazards = []
                for task in doc.tasks:
                    hazards.extend(task.get("potential_hazards", [])[:2])

                context_section += f"""
JSA {i}: {doc.title}
Description: {doc.description[:200]}...
Key Tasks:
{chr(10).join(task_summaries)}
Key Hazards: {', '.join(hazards[:5])}
"""
            context_section += "\nUse these as reference for appropriate hazards and controls, but tailor specifically for the current job.\n"

        prompt = f"""Generate a Job Safety Analysis (JSA) for the following job:

Job Name: {job.name}
Job Number: {job.job_number}
Client: {job.client.name if job.client else 'Unknown'}
Description: {job.description or 'No description provided'}
{context_section}

Generate a comprehensive JSA with:
1. A clear title (job name)
2. Site location (use client address if known, otherwise "To be confirmed on site")
3. A detailed job description for safety purposes
4. 4-6 sequential tasks covering the work from setup to completion
5. For each task: 2-4 potential hazards and appropriate control measures
6. PPE requirements specific to this work
7. Any additional safety notes

For control measures, always link them to the specific hazard they address.
Apply the hierarchy of controls (Elimination > Substitution > Engineering > Administrative > PPE).

Respond with JSON in this exact format:
{{
    "title": "JSA title",
    "site_location": "Work site location",
    "description": "Detailed job description for safety purposes",
    "ppe_requirements": ["PPE item 1", "PPE item 2", ...],
    "tasks": [
        {{
            "step_number": 1,
            "description": "Detailed task description",
            "summary": "1-3 word summary",
            "potential_hazards": ["Hazard 1", "Hazard 2"],
            "initial_risk_rating": "Low|Moderate|High|Extreme",
            "control_measures": [
                {{"measure": "Control measure text", "associated_hazard": "Hazard it addresses"}}
            ],
            "revised_risk_rating": "Low|Moderate|High|Extreme"
        }}
    ],
    "additional_notes": "Any additional safety notes or site-specific requirements"
}}"""

        result = self._call_llm(prompt, expect_json=True)

        # Ensure all required fields exist with defaults
        result.setdefault("title", job.name)
        result.setdefault("site_location", "To be confirmed on site")
        result.setdefault("description", job.description or "")
        result.setdefault("ppe_requirements", DEFAULT_PPE.copy())
        result.setdefault("tasks", [])
        result.setdefault("additional_notes", "")

        return result

    def generate_full_swp(
        self,
        title: str,
        description: str,
        site_location: str = "",
        context_docs: list[SafetyDocument] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a complete SWP (Safe Work Procedure) using AI.

        Args:
            title: Name of the procedure
            description: Scope and description of the procedure
            site_location: Optional site location
            context_docs: Optional list of similar documents for context

        Returns:
            Dict with SWP structure
        """
        # Build context from similar documents
        context_section = ""
        if context_docs:
            context_section = "\n\nREFERENCE DOCUMENTS FROM SIMILAR PROCEDURES:\n"
            for i, doc in enumerate(context_docs, 1):
                task_summaries = []
                for task in doc.tasks[:3]:
                    task_summaries.append(
                        f"  - {task.get('summary', task.get('description', '')[:50])}"
                    )
                hazards = []
                for task in doc.tasks:
                    hazards.extend(task.get("potential_hazards", [])[:2])

                context_section += f"""
Document {i}: {doc.title}
Description: {doc.description[:200]}...
Key Tasks:
{chr(10).join(task_summaries)}
Key Hazards: {', '.join(hazards[:5])}
"""
            context_section += (
                "\nUse these as reference but tailor for this specific procedure.\n"
            )

        prompt = f"""Generate a Safe Work Procedure (SWP) for:

Procedure Name: {title}
Description/Scope: {description}
Location: {site_location or 'General workshop/site'}
{context_section}

Generate a comprehensive SWP with:
1. A clear title
2. Site/work location
3. A detailed procedure description
4. 4-8 sequential steps covering the procedure
5. For each step: 2-4 potential hazards and appropriate control measures
6. PPE requirements
7. Additional safety notes

This is a generic procedure (not job-specific), so focus on standard practices that can be applied consistently.

Respond with JSON in this exact format:
{{
    "title": "SWP title",
    "site_location": "Work location",
    "description": "Detailed procedure description",
    "ppe_requirements": ["PPE item 1", "PPE item 2", ...],
    "tasks": [
        {{
            "step_number": 1,
            "description": "Detailed step description",
            "summary": "1-3 word summary",
            "potential_hazards": ["Hazard 1", "Hazard 2"],
            "initial_risk_rating": "Low|Moderate|High|Extreme",
            "control_measures": [
                {{"measure": "Control measure text", "associated_hazard": "Hazard it addresses"}}
            ],
            "revised_risk_rating": "Low|Moderate|High|Extreme"
        }}
    ],
    "additional_notes": "Additional safety notes"
}}"""

        result = self._call_llm(prompt, expect_json=True)

        # Ensure all required fields exist with defaults
        result.setdefault("title", title)
        result.setdefault("site_location", site_location or "General")
        result.setdefault("description", description)
        result.setdefault("ppe_requirements", DEFAULT_PPE.copy())
        result.setdefault("tasks", [])
        result.setdefault("additional_notes", "")

        return result

    def generate_hazards(self, task_description: str) -> list[str]:
        """
        Generate potential hazards for a specific task.

        Args:
            task_description: Description of the task

        Returns:
            List of 3-5 potential hazards
        """
        prompt = f"""Identify potential hazards for this task in a metal fabrication/installation context:

Task: {task_description}

Generate 3-5 specific, relevant hazards. Consider:
- Physical hazards (machinery, manual handling, working at height)
- Environmental hazards (weather, traffic, confined spaces)
- Chemical hazards (fumes, dust, solvents)
- Ergonomic hazards (repetitive tasks, awkward positions)

Respond with JSON:
{{
    "hazards": ["Hazard 1", "Hazard 2", "Hazard 3"]
}}"""

        result = self._call_llm(prompt, expect_json=True)
        return result.get("hazards", [])

    def generate_controls(self, hazards: list[str]) -> list[dict[str, str]]:
        """
        Generate control measures for a list of hazards.

        Args:
            hazards: List of hazards to generate controls for

        Returns:
            List of control measure dicts with 'measure' and 'associated_hazard'
        """
        hazards_text = "\n".join(f"- {h}" for h in hazards)

        prompt = f"""Generate control measures for these hazards using the hierarchy of controls:

Hazards:
{hazards_text}

For each hazard, suggest 1-2 practical control measures.
Apply the hierarchy: Elimination > Substitution > Engineering > Administrative > PPE

Respond with JSON:
{{
    "controls": [
        {{"measure": "Control measure description", "associated_hazard": "The hazard this controls"}}
    ]
}}"""

        result = self._call_llm(prompt, expect_json=True)
        return result.get("controls", [])

    def generate_task_description(self, brief: str) -> str:
        """
        Expand a brief task into a detailed description.

        Args:
            brief: Short task description or summary

        Returns:
            Expanded, detailed task description
        """
        prompt = f"""Expand this brief task description into a detailed, safety-focused description:

Brief: {brief}

The description should:
- Be clear and specific
- Include relevant safety considerations
- Be appropriate for a JSA/SWP document
- Be 1-2 sentences

Respond with JSON:
{{
    "description": "Detailed task description"
}}"""

        result = self._call_llm(prompt, expect_json=True)
        return result.get("description", brief)
