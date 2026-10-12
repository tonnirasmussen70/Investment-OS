"""Publish an externally researched JSON without changing its scores."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.compounder_updates import publish_agent, validate_agent_payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--target", type=Path, default=Path("data/compounder_agent.json"))
    parser.add_argument("--expected-sha256", help="SHA256 of currently published file (empty bytes if absent)")
    parser.add_argument("--check-only", action="store_true", help="Validate without publishing")
    args = parser.parse_args()
    if args.check_only:
        payload = validate_agent_payload(json.loads(args.source.read_bytes()))
        print(json.dumps({"candidate_count": len(payload["candidates"]), "generated_at": payload["generated_at"], "source": str(args.source)}))
        return
    if not args.expected_sha256:
        parser.error("--expected-sha256 is required for publication")
    print(json.dumps(publish_agent(args.source, args.target, args.expected_sha256), indent=2))


if __name__ == "__main__":
    main()
