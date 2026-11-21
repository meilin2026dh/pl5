from pathlib import Path
import tomllib
import pailie5


def test_package_metadata_matches_research_release():
    metadata = tomllib.loads((Path(__file__).resolve().parents[1] / 'pyproject.toml').read_text())
    assert metadata['project']['version'] == pailie5.__version__
    assert tuple(map(int, pailie5.__version__.split('.'))) >= (3, 7, 2)
