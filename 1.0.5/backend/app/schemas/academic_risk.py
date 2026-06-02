from __future__ import annotations

from pydantic import BaseModel


class AcademicRiskAnalyzeRequest(BaseModel):
    include_recommendations: bool = True
