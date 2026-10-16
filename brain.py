# -*- coding: utf-8 -*-
"""Vicky Talk brain — hybrid LLM layer.

Modes:
  * "local" — free, on-device via Ollama (http://localhost:11434). Default.
  * "api"   — user-supplied key against an OpenAI-compatible endpoint.

All heavy third-party imports (ollama, requests) are lazy, inside methods, so
importing this module never touches the network and never fails on a machine
without those packages installed. chat() never raises — it always returns a
helpful string the UI can display.
"""

import json
import urllib.request

DEFAULT_LOCAL_MODEL = "llama3.1:8b"
OLLAMA_HOST = "http://localhost:11434"


class Brain:
    """Unified chat interface over local Ollama or an OpenAI-compatible API."""

    def __init__(self, mode="local", model=None, api_key=None, base_url=None):
        if mode not in ("local", "api"):
            raise ValueError("mode must be 'local' or 'api'")
        self.mode = mode
        self.model = model
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    # ------------------------------------------------------------------ utils
    def is_local_available(self):
        """True if Ollama answers on localhost with HTTP 200.

        Uses only stdlib urllib with a short timeout. No network at import.
        """
        try:
            req = urllib.request.Request(OLLAMA_HOST + "/api/tags")
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    # ------------------------------------------------------------------ chat
    def chat(self, messages):
        """Return the assistant's reply text for a list of chat messages.

        messages: [{"role": "system"|"user"|"assistant", "content": str}]
        Never raises — on failure returns a helpful guidance string.
        """
        try:
            if self.mode == "local":
                return self._chat_local(messages)
            return self._chat_api(messages)
        except Exception as exc:  # final safety net
            return (
                "Vicky Talk ran into a problem: %s. Please check the Setup wizard "
                "for brain settings." % exc
            )

    def chat_stream(self, messages):
        """Yield the assistant's reply in chunks as they arrive.

        Local mode streams token-by-token via Ollama; API mode yields the
        complete reply as a single chunk. Never raises — failures yield a
        human-readable message chunk instead.
        """
        if self.mode == "api":
            yield self._chat_api(messages)
            return
        try:
            import ollama
        except ImportError:
            yield (
                "The local brain needs the 'ollama' Python package. "
                "Open the Setup wizard to install it and pull a model with "
                "`ollama pull %s`." % DEFAULT_LOCAL_MODEL
            )
            return
        try:
            client = ollama.Client(host=OLLAMA_HOST)
            stream = client.chat(
                model=self.model or DEFAULT_LOCAL_MODEL,
                messages=messages,
                stream=True,
            )
            got_any = False
            for chunk in stream:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    got_any = True
                    yield content
            if not got_any:
                yield (
                    "The local model returned an empty reply. Try restarting "
                    "Ollama or pulling the model again: `ollama pull %s`."
                    % (self.model or DEFAULT_LOCAL_MODEL)
                )
        except Exception as exc:
            yield (
                "Couldn't reach the local brain: %s. "
                "Make sure Ollama is installed and running, and that the model "
                "is pulled: `ollama pull %s`. You can walk through this in the "
                "Setup wizard." % (exc, self.model or DEFAULT_LOCAL_MODEL)
            )

    def _chat_local(self, messages):
        try:
            import ollama
        except ImportError:
            return (
                "The local brain needs the 'ollama' Python package. "
                "Open the Setup wizard to install it and pull a model with "
                "`ollama pull %s`." % DEFAULT_LOCAL_MODEL
            )
        try:
            client = ollama.Client(host=OLLAMA_HOST)
            resp = client.chat(
                model=self.model or DEFAULT_LOCAL_MODEL, messages=messages
            )
            content = resp.get("message", {}).get("content", "")
            if not content:
                return (
                    "The local model returned an empty reply. Try restarting "
                    "Ollama or pulling the model again: `ollama pull %s`."
                    % (self.model or DEFAULT_LOCAL_MODEL)
                )
            return content
        except Exception as exc:
            return (
                "Couldn't reach the local brain: %s. "
                "Make sure Ollama is installed and running, and that the model "
                "is pulled: `ollama pull %s`. You can walk through this in the "
                "Setup wizard." % (exc, self.model or DEFAULT_LOCAL_MODEL)
            )

    def _chat_api(self, messages):
        try:
            import requests
        except ImportError:
            return (
                "API mode needs the 'requests' package, which isn't installed. "
                "Switch to local mode or install it, then set your API key in "
                "the Setup wizard."
            )
        try:
            resp = requests.post(
                "%s/chat/completions" % self.base_url,
                json={"model": self.model or "gpt-4o-mini", "messages": messages},
                headers={"Authorization": "Bearer %s" % self.api_key},
                timeout=60,
            )
            if resp.status_code != 200:
                return "API error: HTTP %s — %s" % (
                    resp.status_code,
                    resp.text[:300],
                )
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            return "API error: %s" % exc

    # ----------------------------------------------------------- tool routing
    def decide_tool(self, user_text):
        """Pick a tool for the user's text.

        Returns (tool_name | None, args_dict). The model is asked to reply
        with ONLY a JSON object {"tool": "<name>"|"null", "args": {...}}.
        Parsing is defensive — any failure yields (None, {}).
        """
        # Imported here to avoid a circular import (tools.py imports Brain's
        # sibling modules only at call time, but we keep it lazy anyway).
        try:
            from tools import TOOLS_SCHEMA
        except Exception:
            return None, {}

        lines = ["%s: %s" % (t["name"], t["description"]) for t in TOOLS_SCHEMA]
        system = (
            "You are a tool router. Available tools:\n"
            + "\n".join("- " + l for l in lines)
            + "\n\nReply with ONLY a single JSON object, no other text: "
              '{"tool": "<tool name>"|"null", "args": {"arg": value}}. '
              'Use "null" when no tool fits.'
        )
        try:
            raw = self.chat(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_text},
                ]
            )
        except Exception:
            return None, {}

        try:
            # Strip markdown fences the model might add.
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else ""
                text = text.rsplit("```", 1)[0]
            obj = json.loads(text)
            name = obj.get("tool")
            if not name or name == "null":
                return None, {}
            args = obj.get("args") or {}
            if not isinstance(args, dict):
                args = {}
            return name, args
        except Exception:
            return None, {}
