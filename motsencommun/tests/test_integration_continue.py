"""L'intégration continue lance les tests et pip-audit, avec des actions épinglées à un commit."""

import re
import tomllib
from pathlib import Path

from django.conf import settings

GITHUB = Path(settings.BASE_DIR) / ".github"
WORKFLOW = GITHUB / "workflows" / "verifications.yml"


def test_chaque_action_est_epinglee_a_un_commit_complet():
    workflows = sorted((GITHUB / "workflows").glob("*.y*ml"))
    assert workflows
    for workflow in workflows:
        actions = re.findall(
            r"^\s*(?:-\s+)?uses:\s*(\S+)", workflow.read_text("utf-8"), re.MULTILINE
        )
        assert actions, f"{workflow.name} n'utilise aucune action"
        for action in actions:
            assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", action), (
                f"{workflow.name} : {action} n'est pas épinglée à un commit complet"
            )


def test_les_verifications_tournent_a_chaque_push_et_pull_request():
    texte = WORKFLOW.read_text("utf-8")
    declencheurs = re.search(r"^on:\n((?:[ \t]+.*\n|\n)+)", texte, re.MULTILINE).group(
        1
    )
    assert re.search(r"^  push:", declencheurs, re.MULTILINE)
    assert re.search(r"^  pull_request:", declencheurs, re.MULTILINE)


def test_les_verifications_lancent_les_tests_et_pip_audit():
    texte = WORKFLOW.read_text("utf-8")
    assert "uv run pytest" in texte
    assert "pip-audit" in texte
    assert "--strict" in texte


def test_dependabot_surveille_les_dependances_python_et_les_actions():
    texte = (GITHUB / "dependabot.yml").read_text("utf-8")
    ecosystemes = re.findall(r'package-ecosystem:\s*"?([\w-]+)"?', texte)
    assert sorted(ecosystemes) == ["github-actions", "uv"]


def test_dependabot_ne_propose_pas_la_version_majeure_suivante_de_django():
    """Django reste sur sa LTS, sous chacun des noms que Dependabot lui donne.

    Dependabot reprend le nom écrit dans pyproject.toml, extras compris : une
    règle pour « django » seul laissait passer « django[argon2] » vers Django 6.
    """
    texte = (GITHUB / "dependabot.yml").read_text("utf-8")
    majeures_ignorees = set(
        re.findall(
            r'dependency-name:\s*"([^"]+)"\s*\n\s*'
            r'update-types:\s*\["version-update:semver-major"\]',
            texte,
        )
    )
    projet = tomllib.loads(
        (Path(settings.BASE_DIR) / "pyproject.toml").read_text("utf-8")
    )
    noms_de_django = {
        re.match(r"[\w.-]+(?:\[[^\]]*\])?", exigence).group(0)
        for exigence in projet["project"]["dependencies"]
        if re.match(r"django(\[|[<>=!~ ]|$)", exigence, re.IGNORECASE)
    }
    assert noms_de_django, "pyproject.toml devrait dépendre de Django"
    assert noms_de_django <= majeures_ignorees
