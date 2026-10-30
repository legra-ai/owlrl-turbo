"""The shared provider cohort supplies original YAML and exact facade authorities."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROVIDER = "2e7b4048a792f496b86cbc9ecde00d921d9d03f4"


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


def test_wheel_build_arranges_the_same_original_declaration_before_uv():
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
    consumed = require_cohort(sequence)
    executed = [
        i for i, step in enumerate(sequence) if "scripts/test_wheel.py" in step.get("run", "")
    ]
    assert len(executed) == 1 and consumed < executed[0]
    for step in sequence:
        if "ci_facade.py " in step.get("run", ""):
            assert step["working-directory"] == "rdflib-turbo"


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
