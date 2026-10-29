"""Regression coverage for generating documentation through the public CLI."""

from pathlib import Path

import yaml
from click.testing import CliRunner

from docmaker.cli import main


def test_generate_preserves_literal_metadata_and_snippets_in_test_named_checkout(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    source_dir = Path("test_checkout/project")
    source_dir.mkdir(parents=True)
    source_dir.joinpath("on.py").write_text(
        'def example():\n    return """\n```\n# Literal source\n````\n"""\n',
        encoding="utf-8",
    )
    output_dir = Path("docs").resolve()

    result = runner.invoke(
        main, ["generate", str(source_dir), "--output", str(output_dir), "--no-llm"]
    )

    assert result.exit_code == 0, result.output
    content = (output_dir / "on.md").read_text(encoding="utf-8")
    metadata = yaml.safe_load(content.split("---\n", 2)[1])
    assert metadata["title"] == "on"
    assert metadata["package"] == "on"
    assert metadata["path"] == "on.py"
    assert '`````python\ndef example():\n    return """' in content
    assert '\n````\n"""\n`````\n</details>' in content

    moc = (output_dir / "MOC - on.md").read_text(encoding="utf-8")
    assert yaml.safe_load(moc.split("---\n", 2)[1])["package"] == "on"
