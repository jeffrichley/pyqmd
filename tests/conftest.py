import pathlib
import pytest


FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures" / "sample_markdown"


@pytest.fixture
def fixtures_dir() -> pathlib.Path:
    return FIXTURES_DIR


@pytest.fixture
def simple_md(fixtures_dir: pathlib.Path) -> pathlib.Path:
    return fixtures_dir / "simple.md"


@pytest.fixture
def with_code_md(fixtures_dir: pathlib.Path) -> pathlib.Path:
    return fixtures_dir / "with_code.md"


@pytest.fixture
def with_frontmatter_md(fixtures_dir: pathlib.Path) -> pathlib.Path:
    return fixtures_dir / "with_frontmatter.md"


@pytest.fixture
def large_md(fixtures_dir: pathlib.Path) -> pathlib.Path:
    return fixtures_dir / "large.md"


@pytest.fixture
def nested_headings_md(fixtures_dir: pathlib.Path) -> pathlib.Path:
    return fixtures_dir / "nested_headings.md"


@pytest.fixture
def tmp_collection(tmp_path: pathlib.Path, fixtures_dir: pathlib.Path) -> pathlib.Path:
    """Create a temporary directory with copies of fixture files for indexing tests."""
    import shutil
    collection_dir = tmp_path / "test_collection"
    shutil.copytree(fixtures_dir, collection_dir)
    return collection_dir
