from typing import Callable, Dict, Optional

from prompts.tools.classification import get_classification_tool_description
from prompts.tools.resume_analyzer import get_resume_analyzer_tool_description
from prompts.tools.conversation_manager import get_conversation_manager_tool_description
from prompts.tools.vision_to_json import get_vision_to_json_tool_description
from prompts.tools.web_search import get_web_search_description

# Dictionary mapping tool names to their description functions
TOOL_DESCRIPTION_MAP: Dict[str, Callable] = {
    "classification": get_classification_tool_description,
    "resume_analyzer": get_resume_analyzer_tool_description,
    "conversation_manager": get_conversation_manager_tool_description,
    "vision_to_json": get_vision_to_json_tool_description,
    "web_search": get_web_search_description,
}

# Always available tools
ALWAYS_AVAILABLE_TOOLS = {"classification", "resume_analyzer", "conversation_manager", "vision_to_json", "web_search"}

# Tool groups (this can be loaded dynamically)
TOOL_GROUPS = {
    "default": {"tools": [""]},
}

def get_tool_descriptions_for_mode(
    mode: str,
    include_examples: bool = True
) -> str:
    """
    Generates tool descriptions based on the given mode.

    Args:
        mode: The mode to generate tool descriptions for.
        include_examples: Whether to include examples in the tool descriptions.

    Returns:
        str: The formatted tool descriptions.
    """
    tools = set()

    # Add tools from mode's group
    tool_group = TOOL_GROUPS.get(mode, {}).get("tools", [])
    tools.update(tool_group)

    # Add always available tools
    tools.update(ALWAYS_AVAILABLE_TOOLS)

    # Generate tool descriptions
    descriptions = [TOOL_DESCRIPTION_MAP[tool]()
                    for tool in tools if tool in TOOL_DESCRIPTION_MAP]

    return "# Tools\n\n{}".format("\n\n".join(descriptions))

# Example usage
if __name__ == "__main__":
    mode = "default"
    print(get_tool_descriptions_for_mode(mode))