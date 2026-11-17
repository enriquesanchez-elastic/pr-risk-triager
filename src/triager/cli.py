"""Usage: triage path/to/pr.json [--model gemini-3.7-flash]"""

import argparse
import json
import sys
from pathlib import Path

from .models import PullRequest
from .triage import triage


def main() -> None:
    parser = argparse.ArgumentParser(description="Triage a pull request")
    parser.add_argument("pr_file", type=Path, help="JSON file with title, description, files")
    parser.add_argument("--model", default=None, help="LLM gateway model, e.g. gemini-3.7-flash or claude-sonnet-4-6, or stand-in to run offline")
    args = parser.parse_args()
    model = args.model
    if model == "stand-in":  # offline keyword model from the evals folder, no gateway needed
        sys.path.insert(0, str(Path.cwd()))  # run from the repo root so `evals` imports
        from evals.stand_in import stand_in_model

        model = stand_in_model
    pr = PullRequest.model_validate(json.loads(args.pr_file.read_text()))
    print(json.dumps(triage(pr, model=model).model_dump(), indent=2))


if __name__ == "__main__":
    main()
