import unittest

from mcp_client import (
    build_ollama_chat_payload,
    build_tool_call_arguments,
    build_tool_catalog,
    deterministic_route,
    extract_ollama_message,
    format_tool_result,
    parse_routing_decision,
)


class ClientHelperTests(unittest.TestCase):
    def test_build_tool_call_arguments_wraps_input_for_fastmcp(self):
        result = build_tool_call_arguments({"city": "Istanbul"})

        self.assertEqual(result, {"input": {"city": "Istanbul"}})

    def test_build_tool_call_arguments_does_not_double_wrap_input(self):
        result = build_tool_call_arguments({"input": {"text": "MCP MCP LangGraph"}})

        self.assertEqual(result, {"input": {"text": "MCP MCP LangGraph"}})

    def test_build_tool_catalog_renders_discovered_tools(self):
        tools = [
            {
                "name": "calculate",
                "description": "Evaluate a safe math expression",
                "inputSchema": {"properties": {"expression": {"type": "string"}}},
            }
        ]

        result = build_tool_catalog(tools)

        self.assertIn("calculate", result)
        self.assertIn("Evaluate a safe math expression", result)
        self.assertIn("expression", result)

    def test_build_tool_catalog_renders_nested_fastmcp_input_fields(self):
        tools = [
            {
                "name": "get_weather",
                "description": "Get current weather for a city",
                "inputSchema": {
                    "properties": {
                        "input": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                        }
                    }
                },
            }
        ]

        result = build_tool_catalog(tools)

        self.assertIn("city", result)
        self.assertNotIn("Fields: input", result)

    def test_parse_routing_decision_accepts_valid_json(self):
        result = parse_routing_decision('{"tool": "calculate", "parameters": {"expression": "2+2"}, "reasoning": "math"}')

        self.assertEqual(result["tool"], "calculate")
        self.assertEqual(result["parameters"], {"expression": "2+2"})

    def test_parse_routing_decision_falls_back_on_invalid_json(self):
        result = parse_routing_decision("not json")

        self.assertEqual(result["tool"], "none")
        self.assertIsNone(result["parameters"])

    def test_build_ollama_chat_payload_disables_streaming(self):
        result = build_ollama_chat_payload(
            model="llama3:latest",
            messages=[{"role": "user", "content": "Merhaba"}],
            temperature=0.2,
            json_mode=True,
        )

        self.assertEqual(result["model"], "llama3:latest")
        self.assertFalse(result["stream"])
        self.assertEqual(result["format"], "json")
        self.assertEqual(result["options"]["temperature"], 0.2)

    def test_extract_ollama_message_reads_chat_response_content(self):
        result = extract_ollama_message({"message": {"content": "cevap"}})

        self.assertEqual(result, "cevap")

    def test_deterministic_route_detects_turkish_weather_question(self):
        result = deterministic_route("Bursa hava durumu")

        self.assertEqual(result, {"tool": "get_weather", "parameters": {"city": "Bursa"}, "reasoning": "deterministic weather route"})

    def test_deterministic_route_detects_arithmetic_question(self):
        result = deterministic_route("8+5 kaç yapar")

        self.assertEqual(result, {"tool": "calculate", "parameters": {"expression": "8+5"}, "reasoning": "deterministic math route"})

    def test_deterministic_route_detects_square_root_question(self):
        result = deterministic_route("12 + 78 rakamının karekökü kaçtır")

        self.assertEqual(
            result,
            {"tool": "calculate", "parameters": {"expression": "sqrt(12 + 78)"}, "reasoning": "deterministic math route"},
        )

    def test_format_tool_result_returns_exact_calculation_answer(self):
        result = format_tool_result("calculate", {"expression": "sqrt(12 + 78)", "result": 9.4868329805})

        self.assertEqual(result, "sqrt(12 + 78) = 9.4868")

    def test_format_tool_result_reads_json_text_mcp_content(self):
        result = format_tool_result(
            "calculate",
            {"content": [{"type": "text", "text": '{"expression": "8+5", "result": 13.0}'}]},
        )

        self.assertEqual(result, "8+5 = 13")

    def test_format_tool_result_returns_turkish_weather_summary(self):
        result = format_tool_result(
            "get_weather",
            {
                "location": "Bursa, Turkey",
                "temperature": "29 C / 85 F",
                "condition": "Sunny",
                "humidity": "37%",
                "wind": "14 km/h",
                "feels_like": "29 C",
            },
        )

        self.assertEqual(
            result,
            "Bursa, Turkey için hava durumu: Güneşli. Sıcaklık 29 C / 85 F, hissedilen 29 C. Nem %37, rüzgar 14 km/h.",
        )

    def test_format_tool_result_returns_turkish_weather_error(self):
        result = format_tool_result("get_weather", {"city": "Erzurum'un kuzey ilçeleri", "error": "Weather API returned HTTP 500"})

        self.assertEqual(
            result,
            "Erzurum'un kuzey ilçeleri için hava durumu alınamadı. Servis geçici hata döndürdü veya konum çok belirsiz olabilir.",
        )


if __name__ == "__main__":
    unittest.main()
