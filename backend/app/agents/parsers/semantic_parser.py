"""
Semantic difference detection agent.

This agent uses LLM to extract structured semantic differences from protocol text.
The LLM is ONLY used for extraction, NOT for determining dependencies.
"""

import json
from typing import Optional

from app.domain.models.entities import ChangeType, SemanticDiff


class SemanticDiffAgent:
    """
    Agent for detecting semantic differences between old and new protocol text.

    Uses LLM for entity extraction and change classification.
    Output is always structured JSON - never free-form text.
    """

    def __init__(self, llm_enabled: bool = True):
        self.llm_enabled = llm_enabled

    async def detect_differences(
        self,
        old_text: str,
        new_text: str,
        suggested_change_type: Optional[ChangeType] = None,
    ) -> SemanticDiff:
        """
        Detect semantic differences between old and new text.

        Args:
            old_text: Original protocol/SAP text
            new_text: Amended protocol/SAP text
            suggested_change_type: Optional hint about the type of change

        Returns:
            Structured SemanticDiff object
        """
        if self.llm_enabled:
            try:
                return await self._detect_with_llm(
                    old_text, new_text, suggested_change_type
                )
            except Exception as e:
                print(f"LLM detection failed, falling back to rule-based: {e}")

        # Fallback to rule-based detection
        return self._detect_rule_based(old_text, new_text, suggested_change_type)

    async def _detect_with_llm(
        self,
        old_text: str,
        new_text: str,
        suggested_change_type: Optional[ChangeType],
    ) -> SemanticDiff:
        """Use LLM for semantic difference detection."""
        try:
            from openai import AsyncOpenAI
            from app.core.config import get_settings

            settings = get_settings()

            if not settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")

            client = AsyncOpenAI(api_key=settings.openai_api_key)

            prompt = self._build_extraction_prompt(
                old_text, new_text, suggested_change_type
            )

            response = await client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a clinical protocol analysis expert. "
                            "Extract structured semantic differences from protocol text. "
                            "Output ONLY valid JSON matching the schema. "
                            "Never output free-form text."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for deterministic output
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)

            # Determine change type if not provided
            change_type = suggested_change_type or self._infer_change_type(result)

            return SemanticDiff(
                endpoints_changed=result.get("endpoints_changed", []),
                visits_changed=result.get("visits_changed"),
                populations_changed=result.get("populations_changed", []),
                variables_changed=result.get("variables_changed", []),
                methods_changed=result.get("methods_changed", []),
                timing_changes=result.get("timing_changes"),
                change_type=change_type,
                change_description=result.get(
                    "change_description",
                    f"Detected {change_type.value} change"
                ),
                confidence=result.get("confidence", 0.8),
                raw_extraction=result,
            )

        except Exception as e:
            raise RuntimeError(f"LLM extraction failed: {e}")

    def _detect_rule_based(
        self,
        old_text: str,
        new_text: str,
        suggested_change_type: Optional[ChangeType],
    ) -> SemanticDiff:
        """
        Rule-based fallback for semantic difference detection.

        Uses simple string matching and patterns.
        """
        old_lower = old_text.lower()
        new_lower = new_text.lower()

        endpoints_changed = []
        visits_changed = {}
        populations_changed = []
        variables_changed = []

        # Detect endpoint mentions
        endpoint_keywords = ["primary endpoint", "secondary endpoint", "endpoint"]
        for keyword in endpoint_keywords:
            if keyword in old_lower or keyword in new_lower:
                # Extract potential endpoint names
                if "hba1c" in old_lower or "hba1c" in new_lower:
                    endpoints_changed.append("HbA1c")
                if "adalb" in old_lower or "adalb" in new_lower:
                    endpoints_changed.append("ADLB")

        # Detect visit timing changes
        week_patterns = ["week", "wk", "visit"]
        old_weeks = self._extract_weeks(old_text)
        new_weeks = self._extract_weeks(new_text)

        if old_weeks and new_weeks and old_weeks != new_weeks:
            visits_changed = {
                "old": f"Week {old_weeks[0]}",
                "new": f"Week {new_weeks[0]}",
            }

        # Detect population mentions
        pop_keywords = ["intent-to-treat", "per protocol", "safety", "itt", "pp"]
        for keyword in pop_keywords:
            if keyword in old_lower or keyword in new_lower:
                populations_changed.append(keyword.upper())

        # Determine change type
        change_type = suggested_change_type or ChangeType.ENDPOINT
        if visits_changed:
            change_type = ChangeType.TIMING
        elif populations_changed:
            change_type = ChangeType.POPULATION

        # Calculate confidence based on how clear the signals are
        confidence = 0.7
        if endpoints_changed:
            confidence += 0.1
        if visits_changed:
            confidence += 0.1
        confidence = min(confidence, 0.95)

        return SemanticDiff(
            endpoints_changed=endpoints_changed,
            visits_changed=visits_changed if visits_changed else None,
            populations_changed=populations_changed,
            variables_changed=variables_changed,
            methods_changed=[],
            change_type=change_type,
            change_description=f"Detected {change_type.value} change",
            confidence=confidence,
        )

    def _extract_weeks(self, text: str) -> list[int]:
        """Extract week numbers from text."""
        import re

        pattern = r"(?:week|wk)\s*(\d+)"
        matches = re.findall(pattern, text, re.IGNORECASE)
        return [int(m) for m in matches]

    def _infer_change_type(self, result: dict) -> ChangeType:
        """Infer change type from extraction results."""
        if result.get("visits_changed"):
            return ChangeType.TIMING
        elif result.get("endpoints_changed"):
            return ChangeType.ENDPOINT
        elif result.get("populations_changed"):
            return ChangeType.POPULATION
        elif result.get("variables_changed"):
            return ChangeType.VARIABLE
        elif result.get("methods_changed"):
            return ChangeType.METHOD
        return ChangeType.ENDPOINT

    def _build_extraction_prompt(
        self,
        old_text: str,
        new_text: str,
        suggested_change_type: Optional[ChangeType],
    ) -> str:
        """Build the prompt for LLM extraction."""
        return f"""
Analyze the following protocol amendment and extract semantic differences.

OLD TEXT:
{old_text}

NEW TEXT:
{new_text}

Extract the following information as JSON:
{{
    "endpoints_changed": ["list", "of", "endpoint", "names"],
    "visits_changed": {{"old": "Week X", "new": "Week Y"}},
    "populations_changed": ["list", "of", "population", "names"],
    "variables_changed": ["list", "of", "variable", "names"],
    "methods_changed": ["list", "of", "statistical", "methods"],
    "timing_changes": {{"description": "any timing changes"}},
    "change_description": "Brief description of the change",
    "confidence": 0.0-1.0
}}

Focus on clinically meaningful changes. Be precise with endpoint and variable names.
"""
