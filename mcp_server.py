from dotenv import load_dotenv
from fastmcp import FastMCP

from tools import (
    CalculatorInput,
    LearningRoadmapInput,
    TextAnalysisInput,
    UnitConversionInput,
    WeatherInput,
    WebSearchInput,
    analyze_text as analyze_text_impl,
    calculate as calculate_impl,
    convert_units as convert_units_impl,
    create_learning_roadmap as create_learning_roadmap_impl,
    get_weather as get_weather_impl,
    web_search as web_search_impl,
)


load_dotenv()

mcp = FastMCP("turkce-mcp-langgraph-demo")


@mcp.tool()
def get_weather(input: WeatherInput):
    """Get current weather for a city."""
    return get_weather_impl(input)


@mcp.tool()
def web_search(input: WebSearchInput):
    """Search the web with Serper."""
    return web_search_impl(input)


@mcp.tool()
def calculate(input: CalculatorInput):
    """Evaluate a safe arithmetic expression."""
    return calculate_impl(input)


@mcp.tool()
def convert_units(input: UnitConversionInput):
    """Convert common distance, temperature, and weight units."""
    return convert_units_impl(input)


@mcp.tool()
def analyze_text(input: TextAnalysisInput):
    """Analyze text length, word count, and frequent keywords."""
    return analyze_text_impl(input)


@mcp.tool()
def create_learning_roadmap(input: LearningRoadmapInput):
    """Create a compact learning roadmap for a topic."""
    return create_learning_roadmap_impl(input)


if __name__ == "__main__":
    mcp.run()
