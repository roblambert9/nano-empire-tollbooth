"""Validate the local smithery.yaml shape used by this stdio MCP package.

Smithery's current publishing flow is CLI-driven for URL servers and MCPB
bundles. This script validates the legacy Docker/stdio metadata this repo keeps
for local registry review and older Smithery examples; it does not publish.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SMITHERY_YAML = ROOT / "smithery.yaml"

SCHEMA = {
    "type": "object",
    "required": ["startCommand", "build"],
    "additionalProperties": False,
    "properties": {
        "startCommand": {
            "type": "object",
            "required": ["type", "configSchema", "commandFunction"],
            "additionalProperties": False,
            "properties": {
                "type": {"const": "stdio"},
                "configSchema": {
                    "type": "object",
                    "required": ["type", "properties"],
                    "properties": {
                        "type": {"const": "object"},
                        "properties": {"type": "object"},
                    },
                    "additionalProperties": True,
                },
                "commandFunction": {"type": "string", "minLength": 1},
            },
        },
        "build": {
            "type": "object",
            "required": ["dockerfile", "dockerBuildPath"],
            "additionalProperties": False,
            "properties": {
                "dockerfile": {"type": "string", "minLength": 1},
                "dockerBuildPath": {"type": "string", "minLength": 1},
            },
        },
    },
}


def main() -> None:
    data = yaml.safe_load(SMITHERY_YAML.read_text(encoding="utf-8"))
    Draft202012Validator(SCHEMA).validate(data)
    dockerfile = ROOT / data["build"]["dockerfile"]
    build_path = ROOT / data["build"]["dockerBuildPath"]
    if not dockerfile.is_file():
        raise SystemExit(f"Dockerfile not found: {dockerfile}")
    if not build_path.is_dir():
        raise SystemExit(f"dockerBuildPath not found: {build_path}")
    print("smithery.yaml local validation: ok")


if __name__ == "__main__":
    main()
