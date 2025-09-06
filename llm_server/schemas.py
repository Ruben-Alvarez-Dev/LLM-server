from __future__ import annotations

from typing import Any, Dict, List


def memory_search_input_schema() -> Dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "memory.search.input",
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query or question"},
            "k": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
            "filters": {"type": "object", "additionalProperties": True, "description": "Optional filter map"},
        },
        "required": ["query"],
        "additionalProperties": False,
    }


def memory_search_output_schema() -> Dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "memory.search.output",
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "score": {"type": "number"},
                        "text": {"type": "string"},
                        "metadata": {"type": "object", "additionalProperties": True},
                    },
                    "required": ["id", "score", "text"],
                    "additionalProperties": True,
                },
            }
        },
        "required": ["results"],
        "additionalProperties": False,
    }


def tool_list() -> List[Dict[str, Any]]:
    return [
        {
            "name": "llm.chat",
            "description": "Chat completion via local models",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string"},
                    "messages": {"type": "array"},
                    "params": {"type": "object"},
                },
                "required": ["model", "messages"],
            },
        },
        {
            "name": "memory.search",
            "description": "Search semantic memory for relevant snippets",
            "inputSchema": memory_search_input_schema(),
            "outputSchema": memory_search_output_schema(),
        },
        {
            "name": "vision.analyze",
            "description": "Analyze screenshots or images with OCR and heuristic insights",
            "inputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "vision.analyze.input",
                "type": "object",
                "properties": {
                    "images": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"},
                                "base64": {"type": "string", "description": "data: URI or raw base64"},
                                "purpose": {"type": "string", "enum": ["screenshot","ui","code","error","document","other"]}
                            },
                            "oneOf": [{"required": ["url"]}, {"required": ["base64"]}]
                        }
                    },
                    "prompt": {"type": "string", "default": "Extract OCR and summarize issues"},
                    "tasks": {"type": "array", "items": {"type": "string", "enum": ["ocr","ui","code","errors"]}},
                    "ocr": {"type": "string", "enum": ["auto","off","fast"], "default": "auto"}
                },
                "required": ["images"],
                "additionalProperties": False
            },
            "outputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "vision.analyze.output",
                "type": "object",
                "properties": {
                    "ocr": {
                        "type": "array",
                        "items": {"type": "object", "properties": {"text": {"type": "string"}, "index": {"type": "integer"}}, "required": ["text","index"]}
                    },
                    "insights": {"type": "array", "items": {"type": "string"}},
                    "issues": {"type": "array", "items": {"type": "string"}},
                    "raw": {"type": "object"}
                },
                "required": ["ocr"],
                "additionalProperties": True
            }
        },
        {
            "name": "embeddings.generate",
            "description": "Generate embeddings for text inputs (OpenAI-style)",
            "inputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "embeddings.generate.input",
                "type": "object",
                "properties": {
                    "model": {"type": "string"},
                    "input": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]},
                    "encoding_format": {"type": "string", "enum": ["float","base64"], "default": "float"},
                    "dimensions": {"type": "integer", "minimum": 32, "maximum": 2048, "default": 256}
                },
                "required": ["input"],
                "additionalProperties": False
            },
            "outputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "embeddings.generate.output",
                "type": "object",
                "properties": {
                    "object": {"type": "string"},
                    "data": {"type": "array"},
                    "model": {"type": "string"},
                    "usage": {"type": "object"}
                },
                "required": ["object","data"],
                "additionalProperties": True
            }
        },
        {
            "name": "voice.transcribe",
            "description": "Transcribe audio to text (ASR)",
            "inputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "voice.transcribe.input",
                "type": "object",
                "properties": {
                    "audio": {"type": "object", "properties": {"base64": {"type": "string"}, "url": {"type": "string"}}},
                    "language": {"type": "string"}
                },
                "required": ["audio"],
                "additionalProperties": False
            },
            "outputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "voice.transcribe.output",
                "type": "object",
                "properties": {"text": {"type": "string"}, "segments": {"type": "array"}, "language": {"type": "string"}},
                "required": ["text"],
                "additionalProperties": True
            }
        },
        {
            "name": "voice.tts",
            "description": "Synthesize speech from text (TTS)",
            "inputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "voice.tts.input",
                "type": "object",
                "properties": {"text": {"type": "string"}, "voice": {"type": "string"}, "format": {"type": "string", "default": "mp3"}},
                "required": ["text"],
                "additionalProperties": False
            },
            "outputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "voice.tts.output",
                "type": "object",
                "properties": {"audio": {"type": "string"}, "format": {"type": "string"}, "voice": {"type": "string"}},
                "required": ["audio"],
                "additionalProperties": True
            }
        },
        {
            "name": "research.search",
            "description": "Search external sources and return snippets",
            "inputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "research.search.input",
                "type": "object",
                "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "default": 5}, "site": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False
            },
            "outputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "research.search.output",
                "type": "object",
                "properties": {"results": {"type": "array"}},
                "required": ["results"],
                "additionalProperties": True
            }
        },
        {
            "name": "agents.plan",
            "description": "Compile NL hints to agent-graph DSL and optionally persist",
            "inputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "agents.plan.input",
                "type": "object",
                "properties": {
                    "nl": {"type": "string"},
                    "hints": {"type": "object"},
                    "save": {"type": "boolean", "default": True}
                },
                "additionalProperties": False
            },
            "outputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "agents.plan.output",
                "type": "object",
                "properties": {
                    "dsl": {"type": "object"},
                    "validated": {"type": "boolean"},
                    "issues": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["dsl","validated"],
                "additionalProperties": True
            }
        },
        {
            "name": "agents.current",
            "description": "Return current agent-graph DSL if present",
            "inputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "agents.current.input",
                "type": "object",
                "additionalProperties": False
            },
            "outputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "agents.current.output",
                "type": "object"
            }
        },
    ]


def get_schema_by_name(name: str) -> Dict[str, Any]:
    if name == "memory.search":
        return memory_search_input_schema()
    if name == "memory.search.output":
        return memory_search_output_schema()
    if name == "llm.chat":
        # expose chat input schema for consistency
        return [t for t in tool_list() if t["name"] == "llm.chat"][0]["inputSchema"]
    if name == "vision.analyze":
        return [t for t in tool_list() if t["name"] == "vision.analyze"][0]["inputSchema"]
    if name == "vision.analyze.output":
        return [t for t in tool_list() if t["name"] == "vision.analyze"][0]["outputSchema"]
    if name == "embeddings.generate":
        return [t for t in tool_list() if t["name"] == "embeddings.generate"][0]["inputSchema"]
    if name == "embeddings.generate.output":
        return [t for t in tool_list() if t["name"] == "embeddings.generate"][0]["outputSchema"]
    if name == "voice.transcribe":
        return [t for t in tool_list() if t["name"] == "voice.transcribe"][0]["inputSchema"]
    if name == "voice.transcribe.output":
        return [t for t in tool_list() if t["name"] == "voice.transcribe"][0]["outputSchema"]
    if name == "voice.tts":
        return [t for t in tool_list() if t["name"] == "voice.tts"][0]["inputSchema"]
    if name == "voice.tts.output":
        return [t for t in tool_list() if t["name"] == "voice.tts"][0]["outputSchema"]
    if name == "research.search":
        return [t for t in tool_list() if t["name"] == "research.search"][0]["inputSchema"]
    if name == "research.search.output":
        return [t for t in tool_list() if t["name"] == "research.search"][0]["outputSchema"]
    if name == "agents.plan":
        return [t for t in tool_list() if t["name"] == "agents.plan"][0]["inputSchema"]
    if name == "agents.plan.output":
        return [t for t in tool_list() if t["name"] == "agents.plan"][0]["outputSchema"]
    if name == "agents.current.output":
        return [t for t in tool_list() if t["name"] == "agents.current"][0]["outputSchema"]
    raise KeyError(name)
