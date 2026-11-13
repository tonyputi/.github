#!/usr/bin/env python3
"""Exercise the real inline queue logic offline; PyYAML comes with existing yamllint."""

import copy
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
workflow = yaml.load(
    (ROOT / ".github/workflows/queue-dependabot.yml").read_text(), Loader=yaml.BaseLoader
)
assert set(workflow["on"]) == {"workflow_call"}
assert set(workflow["on"]["workflow_call"]["inputs"]) == {"validation_workflow"}
assert workflow["on"]["workflow_call"]["secrets"] == {
    "github_app_private_key": {
        "description": "Dedicated caller-repository queue App private key (PEM)",
        "required": "false",
    }
}
assert workflow["permissions"] == {"contents": "read", "pull-requests": "read"}
job = workflow["jobs"]["queue"]
assert "github.event_name == 'workflow_run'" in job["if"]
assert "vars.DEPENDABOT_AUTO_MERGE_ENABLED == 'true'" in job["if"]
steps = job["steps"]
assert len(steps) == 3
metadata, token, merge = steps
assert metadata["env"]["APP_PRIVATE_KEY"] == "${{ secrets.github_app_private_key }}"
assert metadata["env"]["APP_CLIENT_ID"] == "${{ vars.DEPENDABOT_QUEUE_APP_CLIENT_ID }}"
assert metadata["env"]["QUEUE_ENABLED"] == "${{ vars.DEPENDABOT_AUTO_MERGE_ENABLED }}"
assert metadata["env"]["VALIDATION_WORKFLOW"] == "${{ inputs.validation_workflow }}"
assert "${{" not in metadata["run"] + merge["run"]
assert re.fullmatch(r"actions/create-github-app-token@[a-f0-9]{40}", token["uses"])
assert token["if"] == merge["if"] == "steps.metadata.outputs.number != ''"
assert token["with"] == {
    "client-id": "${{ vars.DEPENDABOT_QUEUE_APP_CLIENT_ID }}",
    "private-key": "${{ secrets.github_app_private_key }}",
    "owner": "${{ github.repository_owner }}",
    "repositories": "${{ github.event.repository.name }}",
    "permission-contents": "write",
    "permission-pull-requests": "write",
}
assert merge["env"] == {
    "GH_TOKEN": "${{ steps.app-token.outputs.token }}",
    "PR_NUMBER": "${{ steps.metadata.outputs.number }}",
    "HEAD_SHA": "${{ github.event.workflow_run.head_sha }}",
    "REPOSITORY": "${{ github.repository }}",
}

SHA = "a" * 40
BRANCH = "dependabot/composer/example"
event = {
    "action": "completed",
    "repository": {
        "full_name": "example/widget", "name": "widget",
        "owner": {"login": "example"}, "default_branch": "master",
    },
    "workflow": {"id": 123, "path": ".github/workflows/quality.yml"},
    "workflow_run": {
        "workflow_id": 123, "event": "pull_request", "status": "completed",
        "conclusion": "success", "head_repository": {"full_name": "example/widget"},
        "head_sha": SHA, "head_branch": BRANCH,
    },
}
pr = {
    "number": 42, "state": "open", "draft": False,
    "user": {"login": "dependabot[bot]", "id": 49699333, "type": "Bot"},
    "base": {"ref": "master", "repo": {"full_name": "example/widget"}},
    "head": {"sha": SHA, "ref": BRANCH, "repo": {"full_name": "example/widget"}},
}
count = 0


def check(label, *, event_change=None, pr_change=None, env_change=None,
          eligible=False, copies=1, api_status="0", api_response=None, fails=False,
          no_api=False):
    global count
    payload, pull = copy.deepcopy(event), copy.deepcopy(pr)
    for root, changes in ((payload, event_change), (pull, pr_change)):
        for path, value in (changes or {}).items():
            target = root
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
    with tempfile.TemporaryDirectory(prefix="queue-dependabot-") as directory:
        directory = Path(directory)
        event_path, output, calls = (directory / name for name in ("event.json", "output", "calls"))
        event_path.write_text(json.dumps(payload))
        output.touch()
        calls.touch()
        env = dict(os.environ, QUEUE_ENABLED="true", APP_CLIENT_ID="test-client",
                   APP_PRIVATE_KEY="test-key-not-a-credential", VALIDATION_WORKFLOW=".github/workflows/quality.yml",
                   GITHUB_EVENT_NAME="workflow_run", GITHUB_REPOSITORY="example/widget",
                   GITHUB_REPOSITORY_OWNER="example", GITHUB_EVENT_PATH=str(event_path),
                   GITHUB_OUTPUT=str(output), API_CALLS=str(calls), API_STATUS=api_status,
                   PR_RESPONSE=api_response if api_response is not None else json.dumps([pull] * copies))
        env.update(env_change or {})
        stub = 'gh() { echo "$*" >> "$API_CALLS"; printf "%s" "$PR_RESPONSE"; return "$API_STATUS"; }\n'
        result = subprocess.run(["bash", "-euo", "pipefail", "-c", stub + metadata["run"]],
                                env=env, capture_output=True, text=True, check=False)
        assert (result.returncode != 0) == fails, (label, result.stderr)
        assert output.read_text() == ("number=42\n" if eligible else ""), label
        expected_api = ("api --method GET repos/example/widget/pulls -f state=open "
                        f"-f base=master -f head=example:{payload['workflow_run']['head_branch']}\n")
        assert calls.read_text() == ("" if no_api else expected_api), label
    count += 1


check("caller repository and non-main default branch", eligible=True)
for value in ("", "false", "TRUE", "True", "1", "true "):
    check(f"inactive flag {value!r}", env_change={"QUEUE_ENABLED": value}, no_api=True)
for name in ("APP_CLIENT_ID", "APP_PRIVATE_KEY"):
    check(f"missing {name}", env_change={name: ""}, no_api=True)
check("other trigger", env_change={"GITHUB_EVENT_NAME": "pull_request_target"}, no_api=True)
for path, value in [
    (("action",), "requested"),
    (("repository", "full_name"), "tonyputi/.github"),
    (("repository", "name"), ".github"),
    (("repository", "owner", "login"), "attacker"),
    (("repository", "default_branch"), ""),
    (("workflow", "path"), ".github/workflows/untrusted.yml"),
    (("workflow", "id"), 456),
    (("workflow", "id"), None),
    (("workflow_run", "event"), "push"),
    (("workflow_run", "status"), "in_progress"),
    (("workflow_run", "conclusion"), "failure"),
    (("workflow_run", "head_repository", "full_name"), "attacker/widget"),
    (("workflow_run", "head_sha"), "not-a-sha"),
    (("workflow_run", "head_branch"), "feature/human"),
]:
    check(str(path), event_change={path: value}, no_api=True)
for path, value in [
    (("user", "login"), "tonyputi"), (("user", "id"), 1), (("user", "type"), "User"),
    (("base", "ref"), "main"), (("base", "repo", "full_name"), "attacker/widget"),
    (("head", "repo", "full_name"), "attacker/widget"), (("head", "repo"), None),
    (("head", "sha"), "b" * 40), (("head", "ref"), "dependabot/other"),
    (("state",), "closed"), (("draft",), True), (("number",), "42\ninjected=true"),
]:
    check(str(path), pr_change={path: value})
check("no PR", copies=0)
check("ambiguous PR", copies=2)
check("read API error", api_status="1", fails=True)
check("invalid API JSON", api_response="not-json", fails=True)
check("branch is data, not shell", eligible=True,
      event_change={("workflow_run", "head_branch"): "dependabot/$(exit 99)"},
      pr_change={("head", "ref"): "dependabot/$(exit 99)"})
with tempfile.TemporaryDirectory(prefix="queue-merge-") as directory:
    args_path = Path(directory) / "args"
    env = dict(os.environ, PR_NUMBER="42", REPOSITORY="example/widget", HEAD_SHA=SHA,
               MERGE_ARGS=str(args_path))
    subprocess.run(["bash", "-euo", "pipefail", "-c",
                    'gh() { printf "%s\\0" "$@" > "$MERGE_ARGS"; }\n' + merge["run"]],
                   env=env, check=True)
    assert args_path.read_bytes().split(b"\0")[:-1] == [
        value.encode() for value in ("pr", "merge", "42", "--repo", "example/widget",
                                    "--auto", "--squash", "--match-head-commit", SHA)
    ]
print(f"Queue interface, {count} metadata/activation cases and merge argv: passed")
