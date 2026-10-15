"""
Canonical Task Definitions for Behavioral Telemetry Dataset Collection.
Defines controlled, reproducible browsing tasks for both Human and Automated collection modes.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class TaskStep:
    step_id: int
    instruction: str
    expected_event_type: str
    route: str


@dataclass
class TaskDefinition:
    task_id: str
    name: str
    description: str
    steps: List[TaskStep]
    min_duration_ms: int = 2000
    target_routes: List[str] = field(default_factory=list)


# Standardized Research Tasks
TASKS: Dict[str, TaskDefinition] = {
    "TASK_01": TaskDefinition(
        task_id="TASK_01",
        name="Catalog Browsing & Product Inspection",
        description="Navigate to the catalog, inspect a product, scroll through specifications, and return home.",
        steps=[
            TaskStep(1, "Open landing page and inspect hero area", "mouse_move", "/demo/landing"),
            TaskStep(2, "Navigate to product catalog", "navigation", "/demo/catalog"),
            TaskStep(3, "Scroll down through product cards", "scroll", "/demo/catalog"),
            TaskStep(4, "Click to inspect a product detail item", "mouse_click", "/demo/catalog"),
            TaskStep(5, "Scroll product specifications", "scroll", "/demo/catalog"),
            TaskStep(6, "Navigate back to catalog", "navigation", "/demo/catalog"),
            TaskStep(7, "Return to home page", "navigation", "/demo/landing"),
        ],
        target_routes=["/demo/landing", "/demo/catalog"]
    ),
    "TASK_02": TaskDefinition(
        task_id="TASK_02",
        name="Search & Query Filtering",
        description="Focus the search input, type a non-sensitive query string, inspect results, and scroll through listings.",
        steps=[
            TaskStep(1, "Open search interface", "navigation", "/demo/search"),
            TaskStep(2, "Click search input box", "mouse_click", "/demo/search"),
            TaskStep(3, "Type non-sensitive search query (metadata timing captured)", "key_meta", "/demo/search"),
            TaskStep(4, "Click to inspect search result", "mouse_click", "/demo/search"),
            TaskStep(5, "Scroll down search result details", "scroll", "/demo/search"),
            TaskStep(6, "Return to search results", "navigation", "/demo/search"),
        ],
        target_routes=["/demo/search"]
    ),
    "TASK_03": TaskDefinition(
        task_id="TASK_03",
        name="Multi-Page Exploration & Form Interaction",
        description="Traverse multiple application routes, perform clicks, test keyboard cadences, and include natural pauses.",
        steps=[
            TaskStep(1, "Start on landing page", "mouse_move", "/demo/landing"),
            TaskStep(2, "Navigate to catalog", "navigation", "/demo/catalog"),
            TaskStep(3, "Click interactive filter options", "mouse_click", "/demo/catalog"),
            TaskStep(4, "Navigate to cart checkout step", "navigation", "/demo/cart"),
            TaskStep(5, "Enter input form data (timing metadata only)", "key_meta", "/demo/cart"),
            TaskStep(6, "Scroll through summary", "scroll", "/demo/cart"),
            TaskStep(7, "Navigate to checkout confirmation", "navigation", "/demo/checkout"),
        ],
        target_routes=["/demo/landing", "/demo/catalog", "/demo/cart", "/demo/checkout"]
    )
}


def get_task(task_id: str) -> TaskDefinition:
    """Retrieve task definition by ID, defaulting to TASK_01 if unknown."""
    return TASKS.get(task_id, TASKS["TASK_01"])


def get_all_task_ids() -> List[str]:
    """Returns list of valid task identifiers."""
    return list(TASKS.keys())
