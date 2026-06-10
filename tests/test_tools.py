import unittest

from tools import (
    CalculatorInput,
    TextAnalysisInput,
    UnitConversionInput,
    calculate,
    analyze_text,
    convert_units,
    create_learning_roadmap,
    LearningRoadmapInput,
)


class ToolTests(unittest.TestCase):
    def test_calculate_allows_basic_arithmetic(self):
        result = calculate(CalculatorInput(expression="(25 * 4) + 10 / 2"))

        self.assertEqual(result["result"], 105.0)
        self.assertEqual(result["expression"], "(25 * 4) + 10 / 2")

    def test_calculate_rejects_unsafe_expression(self):
        result = calculate(CalculatorInput(expression="__import__('os').system('dir')"))

        self.assertIn("error", result)
        self.assertIn("unsafe", result["error"].lower())

    def test_calculate_supports_square_root(self):
        result = calculate(CalculatorInput(expression="sqrt(12 + 78)"))

        self.assertAlmostEqual(result["result"], 9.4868, places=4)

    def test_convert_units_converts_celsius_to_fahrenheit(self):
        result = convert_units(UnitConversionInput(value=20, from_unit="celsius", to_unit="fahrenheit"))

        self.assertEqual(result["converted_value"], 68.0)
        self.assertEqual(result["to_unit"], "fahrenheit")

    def test_convert_units_rejects_incompatible_units(self):
        result = convert_units(UnitConversionInput(value=10, from_unit="kilometer", to_unit="celsius"))

        self.assertIn("error", result)

    def test_analyze_text_returns_counts_and_keywords(self):
        result = analyze_text(TextAnalysisInput(text="MCP MCP LangGraph tool agent agent agent", top_n=2))

        self.assertEqual(result["word_count"], 7)
        self.assertEqual(result["top_keywords"][0], {"term": "agent", "count": 3})
        self.assertEqual(result["top_keywords"][1], {"term": "mcp", "count": 2})

    def test_create_learning_roadmap_returns_ordered_steps(self):
        result = create_learning_roadmap(
            LearningRoadmapInput(topic="MCP ve LangGraph", audience="Python geliştiricisi", duration_days=7)
        )

        self.assertEqual(result["topic"], "MCP ve LangGraph")
        self.assertEqual(len(result["steps"]), 5)
        self.assertIn("MCP", result["steps"][0]["title"])


if __name__ == "__main__":
    unittest.main()
