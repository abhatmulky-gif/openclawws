"""
Skill registry — discovers and loads all assessment skills.
Adding a new skill: create a module in skills/ that exports `skill = YourSkill()`.
"""

import importlib
import os
from typing import Optional

from skills.base import BaseSkill

# Explicit registration order (controls menu display order)
_SKILL_MODULES = [
    "skills.ran_autonomy",
    "skills.core_autonomy",
    "skills.transport_autonomy",
    "skills.fwa_autonomy",
    "skills.energy_efficiency",
    "skills.network_probe_skill",
]

_registry: dict[str, BaseSkill] = {}


def _load() -> None:
    if _registry:
        return
    for module_path in _SKILL_MODULES:
        try:
            mod = importlib.import_module(module_path)
            sk: BaseSkill = mod.skill
            _registry[sk.id] = sk
        except Exception as e:
            print(f"[skill_registry] Failed to load {module_path}: {e}")


def all_skills() -> list:
    _load()
    return list(_registry.values())


def get_skill(skill_id: str) -> Optional[BaseSkill]:
    _load()
    return _registry.get(skill_id)


def skill_menu() -> list:
    """Returns a list of dicts suitable for the chat UI skill selector."""
    return [
        {
            "id":          sk.id,
            "name":        sk.name,
            "description": sk.description,
            "icon":        sk.icon,
        }
        for sk in all_skills()
    ]
