from __future__ import annotations

from backend.app.models import LegalEvidence, LegalOperatingMode


def resolve_legal_mode(
    requested_mode: LegalOperatingMode,
    evidence: LegalEvidence,
) -> tuple[LegalOperatingMode, list[str]]:
    if requested_mode == LegalOperatingMode.BLOCKED:
        return LegalOperatingMode.BLOCKED, ["MODE_EXPLICITLY_BLOCKED"]
    if requested_mode == LegalOperatingMode.LICENSED_ADVISORY:
        if evidence.advisory_complete:
            return LegalOperatingMode.LICENSED_ADVISORY, ["ADVISORY_EVIDENCE_VERIFIED"]
        return LegalOperatingMode.BLOCKED, ["INCOMPLETE_LICENSE_CONTRACT_OR_ADVISOR_EVIDENCE"]
    return LegalOperatingMode.RESEARCH_EDUCATION, ["DEFAULT_RESEARCH_EDUCATION_PERIMETER"]
