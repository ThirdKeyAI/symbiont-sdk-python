# Examples

Runnable examples for the Symbiont Python SDK.

```bash
pip install symbiont-sdk
```

| Example | Needs a runtime? | What it shows |
|---------|:---:|---------------|
| [`agent_memory.py`](agent_memory.py) | No | Persistent, file-based agent memory with `MarkdownMemoryStore` — fully self-contained. |
| [`hello_runtime.py`](hello_runtime.py) | Yes | Connect to a running runtime, health-check it, and list agents. |

For the runtime example, start a Symbiont runtime first (`symbi up` or the
Docker quick-start in the main [Symbiont README](https://github.com/thirdkeyai/symbiont)),
then set `SYMBIONT_BASE_URL` (and `SYMBIONT_API_KEY` if required).

```bash
python examples/agent_memory.py
python examples/hello_runtime.py
```
