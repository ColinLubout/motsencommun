"""L'intégration continue lance les tests et pip-audit, avec des actions épinglées à un commit."""

import re
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
