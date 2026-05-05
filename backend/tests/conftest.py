from pathlib import Path
import sys


# Ensure `import app` works when running `cd backend && pytest -q`.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

import pytest


def pytest_collection_modifyitems(config, items):
    """Classify existing tests into speed layers without rewriting every file.

    Fast development loop can run:
      PYTHONPATH=. pytest -m unit -q
      PYTHONPATH=. pytest -m service -q
      PYTHONPATH=. pytest -m contract -q
      PYTHONPATH=. pytest -m "not integration and not slow" -q
    """
    for item in items:
        path = Path(str(item.fspath)).as_posix()
        name = item.name.lower()

        if "/tests/unit/" in path:
            item.add_marker(pytest.mark.unit)
            continue
        if "/tests/service/" in path:
            item.add_marker(pytest.mark.service)
            continue
        if "/tests/contract/" in path:
            item.add_marker(pytest.mark.contract)
            continue
        if "/tests/integration/" in path:
            item.add_marker(pytest.mark.integration)
            continue

        if "api_contract" in path or "contract" in name:
            item.add_marker(pytest.mark.contract)
        elif any(token in path for token in ["provider", "persistence", "pgvector", "memory"]):
            item.add_marker(pytest.mark.integration)
        elif any(token in path for token in ["workflow", "promotion", "registry", "selection", "runner", "scanner"]):
            item.add_marker(pytest.mark.service)
        else:
            item.add_marker(pytest.mark.unit)
