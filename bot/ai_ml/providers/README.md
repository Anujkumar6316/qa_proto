# Provider adapters

Provider code is a transport boundary only. The provider interface should accept normalized messages and generation settings, then return raw text plus available model/usage/latency metadata or a normalized provider exception.

- `protocol.py`: the minimal provider interface.
- `factory.py`: maps configuration to a provider instance.
- `openai_compatible.py`: adapter for compatible HTTP APIs; do not put task prompts here.
- `mock.py`: deterministic provider for unit, parser, and contract tests.

Do not add one adapter per model if several models use the same compatible API. Add a new adapter only when the transport/protocol genuinely differs. Never log API keys or authorization headers.
