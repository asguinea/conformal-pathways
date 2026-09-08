from __future__ import annotations

DR_UNSAFE_PATTERNS_STRICT = [
    "DME-positive case with no OCT ordered anywhere in the pathway.",
    "DME-positive case managed with monitor.",
    "DME-positive case assigned 24-week follow-up.",
    "DME-negative case treated with anti_VEGF.",
]

GLAUCOMA_UNSAFE_PATTERNS_STRICT = [
    "High-risk glaucoma case with no extra tests + monitor + 24-week follow-up.",
    "High-risk glaucoma case that delays follow-up to 24 weeks after monitor without testing.",
    "High-risk glaucoma case where pathway stays low-intervention despite missing tests.",
]
