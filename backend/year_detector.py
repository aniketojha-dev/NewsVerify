import re
from typing import Dict
from backend.config import SUPPORTED_YEARS

YEAR_PATTERN = re.compile(r'\b(20[2-9][0-9])\b')


def detect_year(query: str) -> Dict:
    years = set(int(y) for y in YEAR_PATTERN.findall(query))

    if not years:
        return {"has_explicit_year": False, "is_supported": True, "years": []}

    for y in years:
        if y not in SUPPORTED_YEARS:
            unsupported = [y for y in years if y not in SUPPORTED_YEARS]
            return {
                "has_explicit_year": True,
                "is_supported": False,
                "years": sorted(years),
                "unsupported_years": unsupported,
            }

    return {
        "has_explicit_year": True,
        "is_supported": True,
        "years": sorted(years),
        "unsupported_years": [],
    }
