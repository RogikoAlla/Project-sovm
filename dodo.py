"""doit task file: lint, test, docs, locale, dist automation."""

import glob

DOIT_CONFIG = {"default_tasks": ["lint", "test"]}

SRC_FILES = glob.glob("common/*.py") + glob.glob("server/*.py") + glob.glob("client/*.py")
TEST_FILES = glob.glob("tests/*.py")
PO_FILES = glob.glob("common/locale/*/LC_MESSAGES/messages.po")
MO_FILES = [f.replace(".po", ".mo") for f in PO_FILES]


def task_lint():
    """Run flake8 and pydocstyle on all source directories."""
    return {
        "actions": [
            "flake8 common server client",
            "pydocstyle common server client",
        ],
        "file_dep": SRC_FILES,
        "verbosity": 1,
    }


def task_test():
    """Run pytest with coverage."""
    return {
        "actions": ["pytest"],
        "file_dep": SRC_FILES + TEST_FILES,
        "verbosity": 1,
    }


def task_locale():
    """Compile .po translation files to .mo."""
    return {
        "actions": [
            "pybabel compile -d common/locale",
        ],
        "file_dep": PO_FILES,
        "targets": MO_FILES,
        "verbosity": 1,
    }


def task_docs():
    """Build Sphinx HTML documentation from hand-maintained rst sources."""
    RST_FILES = glob.glob("docs/source/*.rst") + ["docs/source/conf.py"]
    return {
        "actions": [
            "sphinx-build -b html docs/source docs/build/html -q",
        ],
        "file_dep": SRC_FILES + RST_FILES,
        "targets": ["docs/build/html/index.html"],
        "verbosity": 1,
    }


def task_dist():
    """Build a wheel distribution."""
    return {
        "actions": ["python -m build --wheel"],
        "file_dep": SRC_FILES + ["pyproject.toml"],
        "targets": ["dist/king_and_servant-0.1.0-py3-none-any.whl"],
        "verbosity": 1,
    }


def task_clean_artifacts():
    """Remove build artefacts."""
    return {
        "actions": [
            "rm -rf dist build docs/build htmlcov .coverage",
            "find . -name '*.pyc' -delete",
            "find . -name '__pycache__' -type d -exec rm -rf {} +",
        ],
        "verbosity": 0,
    }
