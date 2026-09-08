"""Check the new public command boundary, including side effects and bad inputs."""

import json

import pytest

from conformal_pathways import __version__
from conformal_pathways.cli import main


@pytest.mark.parametrize("workflow", ["dr", "glaucoma"])
def test_demo_is_deterministic_and_writes_no_files(workflow, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    command = ["demo", "--workflow", workflow, "--n", "20", "--seed", "7"]
    assert main(command) == 0
    first = capsys.readouterr().out
    assert main(command) == 0
    assert capsys.readouterr().out == first
    payload = json.loads(first)
    assert payload["verification_scope"] == "installation_smoke_only"
    assert payload["scientific_validation"] == "see_claim_register"
    assert payload["project_version"] == __version__
    assert payload["config"]["workflow"] == workflow
    assert payload["experimental_metrics"]
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "arguments",
    [
        ["--n", "0"],
        ["--n", "19"],
        ["--n", "1.5"],
        ["--alpha", "0"],
        ["--alpha", "1"],
        ["--alpha", "nan"],
        ["--alpha", "inf"],
        ["--alpha", "invalid"],
        ["--workflow", "unknown"],
    ],
)
def test_demo_rejects_invalid_configuration(arguments):
    with pytest.raises(SystemExit) as exc:
        main(["demo", *arguments])
    assert exc.value.code == 2
