"""Usage: triage path/to/pr.json [--model openai:gpt-5.2]"""

import argparse
import json
from pathlib import Path

from .models import PullRequest
from .triage import triage


def main() -> None:
    parser = argparse.ArgumentParser(description="Triage a pull request")
    parser.add_argument("pr_file", type=Path, help="JSON file with title, description, files")
    parser.add_argument("--model", default=None, help="e.g. openai:gpt-5.2 or anthropic:claude-sonnet-4-5")
    args = parser.parse_args()
    pr = PullRequest.model_validate(json.loads(args.pr_file.read_text()))
    print(json.dumps(triage(pr, model=args.model).model_dump(), indent=2))


if __name__ == "__main__":
    main()
