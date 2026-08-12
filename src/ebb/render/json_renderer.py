import json

from ebb.finding import Finding


def render_json(findings: list[Finding]) -> str:
    return json.dumps([f.model_dump(mode="json") for f in findings], indent=2, sort_keys=True)
