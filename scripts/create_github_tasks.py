#!/usr/bin/env python3
"""
Cria, no repositório rickdeu/fenixschool e no GitHub Project #11 ("FenixSchool"),
uma issue por cada tarefa definida em scripts/tasks_data.py.

Cada issue é:
  - criada no repositório com título, corpo rico (contexto, exemplo de implementação,
    critérios de aceitação, referências), label de módulo e milestone de fase;
  - adicionada ao Project #11;
  - colocada no Status "Backlog" (por instrução do dono do projeto);
  - marcada com a Prioridade (P0/P1/P2) e o Tamanho (XS..XL) definidos em tasks_data.py.

Idempotente: mantém um log em scripts/.github_tasks_log.json (título -> URL da issue)
e salta tarefas já criadas, para poder ser corrido em várias etapas sem duplicar.

Uso:
    python3 scripts/create_github_tasks.py [--start N] [--end N] [--dry-run]
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tasks_data import TASKS  # noqa: E402

REPO = "rickdeu/fenixschool"
PROJECT_OWNER = "rickdeu"
PROJECT_NUMBER = "11"
PROJECT_ID = "PVT_kwHOAQ6R384BjPzD"

STATUS_FIELD_ID = "PVTSSF_lAHOAQ6R384BjPzDzhiE31k"
STATUS_BACKLOG_OPTION_ID = "f75ad846"

PRIORITY_FIELD_ID = "PVTSSF_lAHOAQ6R384BjPzDzhiE368"
PRIORITY_OPTION_IDS = {
    "P0": "79628723",
    "P1": "0a877460",
    "P2": "da944a9c",
}

SIZE_FIELD_ID = "PVTSSF_lAHOAQ6R384BjPzDzhiE37A"
SIZE_OPTION_IDS = {
    "XS": "6c6483d2",
    "S": "f784b110",
    "M": "7515a9f1",
    "L": "817d0097",
    "XL": "db339eb2",
}

LOG_PATH = Path(__file__).parent / ".github_tasks_log.json"


def load_log() -> dict:
    if LOG_PATH.exists():
        return json.loads(LOG_PATH.read_text())
    return {}


def save_log(log: dict) -> None:
    LOG_PATH.write_text(json.dumps(log, indent=2, ensure_ascii=False, sort_keys=True))


def get_milestone_map() -> dict:
    out = subprocess.run(
        ["gh", "api", f"repos/{REPO}/milestones", "--jq", ".[] | \"\\(.title)|\\(.number)\""],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    m = {}
    for line in out.splitlines():
        title, number = line.split("|")
        m[title] = number
    return m


def render_body(t: dict) -> str:
    lines = []
    lines.append(
        f"**Prioridade:** {t['priority']}  ·  **Tamanho estimado:** {t['size']}  ·  **Fase:** {t['phase']}  ·  **Módulo:** `{t['module']}`"
    )
    lines.append("")
    if t.get("refs"):
        lines.append(f"**Requisitos/Referências:** {', '.join(t['refs'])}")
        lines.append("")
    lines.append("## Contexto")
    lines.append(t["context"])
    lines.append("")
    lines.append("## Exemplo de implementação")
    lines.append(t["example"])
    lines.append("")
    lines.append("## Critérios de aceitação")
    for a in t["acceptance"]:
        lines.append(f"- [ ] {a}")
    lines.append("")
    lines.append("---")
    if t.get("doc_links"):
        lines.append("_Gerado a partir da documentação técnica em `docs/`. Ver também: " + ", ".join(t["doc_links"]) + "_")
    else:
        lines.append("_Gerado a partir da documentação técnica em `docs/`._")
    return "\n".join(lines)


def create_issue(t: dict, milestone_title: str) -> str:
    body = render_body(t)
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(body)
        body_path = f.name

    cmd = [
        "gh", "issue", "create",
        "--repo", REPO,
        "--title", t["title"],
        "--body-file", body_path,
        "--label", f"module:{t['module']}",
    ]
    if milestone_title:
        cmd += ["--milestone", milestone_title]

    result = subprocess.run(cmd, capture_output=True, text=True)
    Path(body_path).unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh issue create failed: {result.stderr}")
    return result.stdout.strip().splitlines()[-1]  # issue URL


def add_to_project(issue_url: str) -> str:
    result = subprocess.run(
        ["gh", "project", "item-add", PROJECT_NUMBER, "--owner", PROJECT_OWNER,
         "--url", issue_url, "--format", "json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh project item-add failed: {result.stderr}")
    return json.loads(result.stdout)["id"]


def set_field(item_id: str, field_id: str, option_id: str) -> None:
    result = subprocess.run(
        ["gh", "project", "item-edit",
         "--id", item_id,
         "--project-id", PROJECT_ID,
         "--field-id", field_id,
         "--single-select-option-id", option_id],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh project item-edit failed: {result.stderr}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=len(TASKS))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    log = load_log()
    milestone_map = get_milestone_map()

    batch = TASKS[args.start:args.end]
    print(f"Processing tasks [{args.start}:{args.end}] of {len(TASKS)} total "
          f"({len(batch)} in this batch)")

    created, skipped, failed = 0, 0, 0

    for i, t in enumerate(batch, start=args.start):
        key = t["title"]
        if key in log:
            skipped += 1
            continue

        if args.dry_run:
            print(f"[{i}] DRY-RUN would create: {t['title']}")
            continue

        try:
            milestone_title = t["phase"] if t["phase"] in milestone_map else None
            issue_url = create_issue(t, milestone_title)
            item_id = add_to_project(issue_url)
            set_field(item_id, STATUS_FIELD_ID, STATUS_BACKLOG_OPTION_ID)
            set_field(item_id, PRIORITY_FIELD_ID, PRIORITY_OPTION_IDS[t["priority"]])
            set_field(item_id, SIZE_FIELD_ID, SIZE_OPTION_IDS[t["size"]])

            log[key] = issue_url
            save_log(log)
            created += 1
            print(f"[{i}] OK  {issue_url}  {t['title']}")
        except Exception as e:
            failed += 1
            print(f"[{i}] FAIL {t['title']}: {e}")

    print(f"\nDone. created={created} skipped(existing)={skipped} failed={failed}")


if __name__ == "__main__":
    main()
