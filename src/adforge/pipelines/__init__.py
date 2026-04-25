"""Temporal workflows. Two atoms + one merged.

  playable_forge — gameplay video → interactive HTML playable + variants
  creative_forge — target game     → market-informed brief + Scenario prompt
  full_forge     — both, chained   → market-informed playable + brief + creative
"""

from adforge.pipelines.creative_forge import CreativeForge, CreativeForgeInput
from adforge.pipelines.full_forge import FullForge, FullForgeInput
from adforge.pipelines.playable_forge import PlayableForge, PlayableForgeInput

WORKFLOWS = [PlayableForge, CreativeForge, FullForge]
