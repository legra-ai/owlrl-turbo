"""The shared provider cohort supplies original YAML and exact facade authorities."""

import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROVIDER = "d2692efc768554473a65eece7d0fce6836b47f57"


def test_runtime_floor_requires_the_published_scoped_capture_provider():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert project["dependencies"] == ["rdflib-turbo>=0.2.0a20"]


def steps(filename, job):
    workflow = yaml.safe_load((ROOT / ".github/workflows" / filename).read_text())
    return workflow["jobs"][job]["steps"]


def require_cohort(sequence):
    prepare = [
        i for i, step in enumerate(sequence) if "ci_facade.py prepare " in step.get("run", "")
    ]
    consume = [
        i for i, step in enumerate(sequence) if "ci_facade.py consume " in step.get("run", "")
    ]
    assert len(prepare) == len(consume) == 1
    assert prepare[0] < consume[0]
    assert '--output "$RUNNER_TEMP/candidate-facade-evidence"' in sequence[prepare[0]]["run"]
    assert '--input "$RUNNER_TEMP/candidate-facade-evidence"' in sequence[consume[0]]["run"]
    for index in (*prepare, *consume):
        assert "--python 3.13.16 python -B" in sequence[index]["run"]
    assert '--environment-file "$GITHUB_ENV"' in sequence[consume[0]]["run"]
    return consume[0]


def test_coverage_uses_one_verified_current_provider_cohort():
    sequence = steps("native-coverage.yml", "coverage")
    providers = [
        step
        for step in sequence
        if step.get("with", {}).get("repository") == "legra-ai/rdflib-turbo"
    ]
    assert len(providers) == 1
    assert providers[0]["with"]["ref"] == PROVIDER
    assert providers[0]["with"]["path"] == "rdflib-turbo"
    consumed = require_cohort(sequence)
    executions = [
        (i, step["run"])
        for i, step in enumerate(sequence)
        if "scripts/native_coverage.py" in step.get("run", "")
    ]
    assert len(executions) == 1
    index, command = executions[0]
    assert consumed < index
    for argument in (
        '--shacl-source "$SHACL_SOURCE"',
        '--shacl-wheel "$SHACL_WHEEL"',
        '--shacl-candidate-receipt "$SHACL_CANDIDATE_RECEIPT"',
        '--shacl-base-revision "$SHACL_BASE_REVISION"',
        '--yaml-authority "$YAML_AUTHORITY"',
        "--owlrl-source ../coverage-companion-owlrl",
    ):
        assert argument in command


def test_wheel_jobs_consume_one_linux_built_original_cohort():
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    build = workflow["jobs"]["build"]
    assert build["runs-on"] == "ubuntu-latest"
    producers = [step for step in build["steps"] if "ci_facade.py prepare " in step.get("run", "")]
    assert len(producers) == 1
    assert producers[0]["working-directory"] == "rdflib-turbo"
    assert '--output "$RUNNER_TEMP/candidate-facade-evidence"' in producers[0]["run"]
    assert "--python 3.13.16 python -B" in producers[0]["run"]
    provider = [
        step
        for step in build["steps"]
        if step.get("with", {}).get("repository") == "legra-ai/rdflib-turbo"
    ]
    assert len(provider) == 1
    assert provider[0]["with"]["ref"] == PROVIDER
    assert provider[0]["with"]["path"] == "rdflib-turbo"
    uploads = [
        step
        for step in build["steps"]
        if step.get("with", {}).get("name") == "provider-facade-cohort"
    ]
    assert len(uploads) == 1
    assert uploads[0]["uses"] == "actions/upload-artifact@v7"
    assert uploads[0]["with"]["path"] == "${{ runner.temp }}/candidate-facade-evidence"
    assert uploads[0]["with"]["include-hidden-files"] is True
    assert uploads[0]["with"]["if-no-files-found"] == "error"
    sequence = steps("ci.yml", "wheels")
    providers = [
        step
        for step in sequence
        if step.get("with", {}).get("repository") == "legra-ai/rdflib-turbo"
    ]
    assert len(providers) == 1
    assert providers[0]["with"] == {
        "repository": "legra-ai/rdflib-turbo",
        "ref": PROVIDER,
        "path": "rdflib-turbo",
    }
    assert not any("ci_facade.py prepare " in step.get("run", "") for step in sequence)
    downloads = [
        i
        for i, step in enumerate(sequence)
        if step.get("with", {}).get("name") == "provider-facade-cohort"
    ]
    consumes = [
        i for i, step in enumerate(sequence) if "ci_facade.py consume " in step.get("run", "")
    ]
    executions = [
        i for i, step in enumerate(sequence) if "scripts/test_wheel.py" in step.get("run", "")
    ]
    assert len(downloads) == len(consumes) == len(executions) == 1
    assert downloads[0] < consumes[0] < executions[0]
    assert sequence[downloads[0]]["uses"] == "actions/download-artifact@v8"
    assert sequence[downloads[0]]["with"]["path"] == "${{ runner.temp }}/candidate-facade-evidence"
    consume = sequence[consumes[0]]
    assert consume["working-directory"] == "rdflib-turbo"
    assert '--input "$RUNNER_TEMP/candidate-facade-evidence"' in consume["run"]
    assert '--environment-file "$GITHUB_ENV"' in consume["run"]
    assert "--python 3.13.16 python -B" in consume["run"]


def test_coverage_builds_its_own_original_owl_companion_before_measurement():
    sequence = steps("native-coverage.yml", "coverage")
    builds = [
        (i, step) for i, step in enumerate(sequence) if "uv build --sdist" in step.get("run", "")
    ]
    assert len(builds) == 1
    build_index, build = builds[0]
    assert build["working-directory"] == "coverage-companion-owlrl"
    assert "uv build --wheel" in build["run"]
    assert "../rdflib-turbo/native-coverage/companion-originals/source/*.tar.gz" in build["run"]
    executions = [
        (i, step["run"])
        for i, step in enumerate(sequence)
        if "scripts/native_coverage.py" in step.get("run", "")
    ]
    assert len(executions) == 1
    execution_index, command = executions[0]
    assert build_index < execution_index
    assert "--owlrl-wheel native-coverage/companion-originals/wheel/owlrl_turbo-*.whl" in command
    assert "--python 3.13.16 --shacl-source" in command
