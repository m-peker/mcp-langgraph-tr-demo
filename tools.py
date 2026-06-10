import ast
import math
import operator
import os
import re
from collections import Counter
from typing import Any

import requests
from pydantic import BaseModel, Field


class WeatherInput(BaseModel):
    city: str = Field(..., description="City name, for example Istanbul")


class WebSearchInput(BaseModel):
    query: str = Field(..., description="Search query")


class CalculatorInput(BaseModel):
    expression: str = Field(..., description="A safe arithmetic expression")


class UnitConversionInput(BaseModel):
    value: float
    from_unit: str
    to_unit: str


class TextAnalysisInput(BaseModel):
    text: str
    top_n: int = 5


class LearningRoadmapInput(BaseModel):
    topic: str
    audience: str = "Python gelistiricisi"
    duration_days: int = 7


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}

_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_ALLOWED_FUNCTIONS = {
    "sqrt": math.sqrt,
}


def _eval_arithmetic(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_arithmetic(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _eval_arithmetic(node.left)
        right = _eval_arithmetic(node.right)
        return float(_BINARY_OPERATORS[type(node.op)](left, right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return float(_UNARY_OPERATORS[type(node.op)](_eval_arithmetic(node.operand)))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_FUNCTIONS:
        if len(node.args) != 1 or node.keywords:
            raise ValueError("Unsafe or unsupported expression")
        return float(_ALLOWED_FUNCTIONS[node.func.id](_eval_arithmetic(node.args[0])))
    raise ValueError("Unsafe or unsupported expression")


def calculate(input: CalculatorInput) -> dict[str, Any]:
    """Evaluate a safe arithmetic expression without eval."""
    try:
        parsed = ast.parse(input.expression, mode="eval")
        result = _eval_arithmetic(parsed)
        return {"expression": input.expression, "result": result}
    except Exception as exc:
        return {"expression": input.expression, "error": f"Unsafe calculation rejected: {exc}"}


def convert_units(input: UnitConversionInput) -> dict[str, Any]:
    """Convert common distance, temperature, and weight units."""
    from_unit = input.from_unit.strip().lower()
    to_unit = input.to_unit.strip().lower()
    value = float(input.value)

    if from_unit == to_unit:
        return {"value": value, "from_unit": from_unit, "to_unit": to_unit, "converted_value": value}

    conversions = {
        ("kilometer", "mile"): lambda x: x * 0.621371,
        ("mile", "kilometer"): lambda x: x / 0.621371,
        ("meter", "foot"): lambda x: x * 3.28084,
        ("foot", "meter"): lambda x: x / 3.28084,
        ("kilogram", "pound"): lambda x: x * 2.20462,
        ("pound", "kilogram"): lambda x: x / 2.20462,
        ("celsius", "fahrenheit"): lambda x: (x * 9 / 5) + 32,
        ("fahrenheit", "celsius"): lambda x: (x - 32) * 5 / 9,
    }

    converter = conversions.get((from_unit, to_unit))
    if converter is None:
        return {
            "value": value,
            "from_unit": from_unit,
            "to_unit": to_unit,
            "error": "Unsupported or incompatible unit conversion",
        }

    return {
        "value": value,
        "from_unit": from_unit,
        "to_unit": to_unit,
        "converted_value": round(converter(value), 4),
    }


def analyze_text(input: TextAnalysisInput) -> dict[str, Any]:
    """Return simple counts and top keywords for a text."""
    words = re.findall(r"[A-Za-z0-9_ğüşöçıİĞÜŞÖÇ]+", input.text.lower())
    counter = Counter(words)
    top_keywords = [{"term": term, "count": count} for term, count in counter.most_common(input.top_n)]

    return {
        "character_count": len(input.text),
        "word_count": len(words),
        "unique_word_count": len(counter),
        "top_keywords": top_keywords,
    }


def create_learning_roadmap(input: LearningRoadmapInput) -> dict[str, Any]:
    """Create a compact learning roadmap for an educational topic."""
    days = max(1, input.duration_days)
    steps = [
        {
            "day": 1,
            "title": f"{input.topic}: kavram haritasi",
            "goal": "MCP server, MCP client, tool ve transport kavramlarini ayir.",
        },
        {
            "day": max(1, round(days * 0.25)),
            "title": "Tool schema ve dogrulama",
            "goal": "Pydantic modellerinin tool sozlesmesine nasil donustugunu incele.",
        },
        {
            "day": max(1, round(days * 0.5)),
            "title": "LangGraph ile karar akisi",
            "goal": "Ajanin hangi tool'u ne zaman sececegini graph dugumleriyle modelle.",
        },
        {
            "day": max(1, round(days * 0.75)),
            "title": "Hata yonetimi ve gozlemlenebilirlik",
            "goal": "API hatalari, gecersiz argumanlar ve fallback cevaplarini test et.",
        },
        {
            "day": days,
            "title": "Mini proje ve dokumantasyon",
            "goal": f"{input.audience} icin calisan bir demo ve kisa teknik yazi hazirla.",
        },
    ]

    return {
        "topic": input.topic,
        "audience": input.audience,
        "duration_days": days,
        "steps": steps,
    }


def get_weather(input: WeatherInput) -> dict[str, Any]:
    """Get current weather for a city using wttr.in."""
    try:
        response = requests.get(f"https://wttr.in/{input.city}?format=j1", timeout=5)
        if response.status_code != 200:
            return {"city": input.city, "error": f"Weather API returned HTTP {response.status_code}"}

        data = response.json()
        current = data["current_condition"][0]
        location = data["nearest_area"][0]
        return {
            "location": f"{location['areaName'][0]['value']}, {location['country'][0]['value']}",
            "temperature": f"{current['temp_C']} C / {current['temp_F']} F",
            "condition": current["weatherDesc"][0]["value"],
            "humidity": f"{current['humidity']}%",
            "wind": f"{current['windspeedKmph']} km/h",
            "feels_like": f"{current['FeelsLikeC']} C",
        }
    except Exception as exc:
        return {"city": input.city, "error": f"Weather API error: {exc}"}


def web_search(input: WebSearchInput) -> dict[str, Any]:
    """Search the web using Serper API."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return {"query": input.query, "error": "SERPER_API_KEY is not configured"}

    try:
        response = requests.post(
            "https://google.serper.dev/search",
            json={"q": input.query, "num": 5},
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            timeout=10,
        )
        if response.status_code != 200:
            return {"query": input.query, "error": f"Serper API returned HTTP {response.status_code}"}

        data = response.json()
        results = [
            {
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet"),
            }
            for item in data.get("organic", [])[:5]
        ]
        knowledge = data.get("knowledgeGraph") or {}
        return {
            "query": input.query,
            "results": results,
            "knowledge_graph": knowledge.get("description"),
        }
    except Exception as exc:
        return {"query": input.query, "error": f"Web search error: {exc}"}
