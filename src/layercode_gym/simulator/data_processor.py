from __future__ import annotations

"""Default data processor implementations for response.data events."""

from typing import Any

from pydantic_ai.format_prompt import format_as_xml


def default_data_processor(data: dict[str, Any]) -> str:
    """Default processor that formats response.data as XML.

    Uses PydanticAI's format_as_xml which LLMs find easier to parse
    than JSON for semi-structured data.

    Args:
        data: The raw data dictionary from response.data event

    Returns:
        XML-formatted string representation of the data

    Example:
        >>> data = {"tool": "show_menu", "items": ["croissant", "baguette"]}
        >>> print(default_data_processor(data))
        <response_data>
          <tool>show_menu</tool>
          <items>
            <item>croissant</item>
            <item>baguette</item>
          </items>
        </response_data>
    """
    return format_as_xml(data, root_tag="response_data")


class XMLDataProcessor:
    """Configurable XML data processor with custom root tag.

    This is a class-based processor that allows customization of the
    XML output format.

    Attributes:
        root_tag: The XML root element tag (default: "response_data")
        include_field_info: Whether to include Pydantic field descriptions

    Example:
        processor = XMLDataProcessor(root_tag="tool_result")
        result = processor({"status": "success", "data": [1, 2, 3]})
    """

    def __init__(
        self,
        root_tag: str = "response_data",
        include_field_info: bool = False,
    ) -> None:
        self.root_tag = root_tag
        self.include_field_info = include_field_info

    def __call__(self, data: dict[str, Any]) -> str:
        """Convert response.data to XML format.

        Args:
            data: The raw data dictionary from response.data event

        Returns:
            XML-formatted string representation
        """
        return format_as_xml(
            data,
            root_tag=self.root_tag,
            include_field_info=self.include_field_info,
        )
