import asyncio
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "03-production"
FUNCTION_CALLING = ROOT / "01-function-calling"

sys.path.insert(0, str(PRODUCTION))
from registry_client import ToolRegistry  # noqa: E402


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RegistryTests(unittest.TestCase):
    def test_search_by_tag_returns_matching_tools(self):
        registry = ToolRegistry()

        results = registry.search(tag="forecast")

        self.assertEqual(["get_weather_v2"], [item["tool"] for item in results])

    def test_best_match_compares_numeric_versions(self):
        data = {
            "tools": {
                "legacy": {
                    "description": "Legacy tool",
                    "tags": ["demo"],
                    "server": "demo",
                    "version": "9.0.0",
                },
                "current": {
                    "description": "Current tool",
                    "tags": ["demo"],
                    "server": "demo",
                    "version": "10.0.0",
                },
            },
            "servers": {"demo": {"transport": "stdio", "args": []}},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            registry = ToolRegistry(path)

        self.assertEqual("current", registry.best_match(tag="demo")["tool"])


class FunctionCallingTests(unittest.TestCase):
    def test_mock_weather_tool_returns_json(self):
        module = load_module(
            "weather_function_calling",
            FUNCTION_CALLING / "weather_function_calling.py",
        )

        result = json.loads(module.get_weather("Hà Nội"))

        self.assertEqual("Hà Nội", result["city"])
        self.assertEqual("29°C", result["nhiệt_độ"])

    def test_missing_api_key_has_actionable_error(self):
        module = load_module(
            "weather_function_calling_no_key",
            FUNCTION_CALLING / "weather_function_calling.py",
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            with self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY"):
                module.create_client()


class VersionedServerTests(unittest.TestCase):
    def test_v2_rejects_unknown_units(self):
        server = load_module(
            "versioned_server", PRODUCTION / "versioned_server.py"
        )

        result = json.loads(
            server.get_weather_v2("Hanoi", units="kelvin")
        )

        self.assertEqual("2.0", result["api_version"])
        self.assertIn("units", result["error"])


class Lab04Tests(unittest.TestCase):
    def test_forecast_without_api_key_returns_actionable_error(self):
        server = load_module(
            "lab04_weather_server",
            ROOT / "04-lab" / "mcp-server" / "weather.py",
        )

        with patch.dict(os.environ, {"WEATHERAPI_KEY": ""}):
            result = asyncio.run(server.get_forecast("Hanoi", days=0))

        self.assertIn("WEATHERAPI_KEY", result)


if __name__ == "__main__":
    unittest.main()
