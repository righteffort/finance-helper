## Publish
```bash
uv build
UV_PUBLISH_TOKEN=$(cat ~/.pypitoken) uv publish
uv run pdoc -o ../../docs/python/fidelity-helper fidelity_helper
```
