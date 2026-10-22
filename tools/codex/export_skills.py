#!/usr/bin/env python3
"""Export self-contained Codex skills without changing the Claude plugin sources."""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile

SUPPORTED_SKILLS = ("pr-sweep",)


def export_skill(root: Path, destination: Path, name: str) -> Path:
    if name not in SUPPORTED_SKILLS:
        raise ValueError(f"Unsupported Codex skill: {name}")
    source = root / "skills" / name
    content = (source / "SKILL.md").read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        raise ValueError("Expected SKILL.md YAML frontmatter")
    header, body = content[4:].split("\n---\n", 1)
    # Fail on changed/multiline source fields instead of silently exporting an incomplete description.
    skill_name = re.search(r"^name: ([a-z0-9-]+)$", header, re.MULTILINE)
    description = re.search(r"^description: (.+)$", header, re.MULTILINE)
    if not skill_name or skill_name[1] != name or not description or description[1] in ("|", ">", "|-", ">-"):
        raise ValueError("Expected a matching name and single-line description")
    if not (source / "adapters" / "codex.md").is_file():
        raise ValueError("Codex adapter is missing")
    if any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("Skill resources must not be symbolic links")
    target = destination / name
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"Refusing to replace existing skill: {target}")
    body = body.replace("Options for this run: $ARGUMENTS", "Options for this run: use the options in the user's request.")
    preamble = ("## Codex host\n\nBefore starting, read [the Codex adapter](adapters/codex.md). "
                "Its host mappings take precedence over Claude-specific references below; "
                "the shared workflow and owner-decision rules remain in force.\n\n")
    exported = (f"---\nname: {name}\ndescription: {json.dumps(description[1])}\n---\n\n"
                + preamble + body.lstrip())
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".nightforge-export-", dir=destination) as staging:
        staged = Path(staging) / name
        shutil.copytree(source, staged)
        (staged / "SKILL.md").write_text(exported, encoding="utf-8")
        staged.rename(target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", choices=SUPPORTED_SKILLS, default="pr-sweep")
    parser.add_argument("--dest", type=Path, required=True, help="Destination skills directory")
    args = parser.parse_args()
    try:
        target = export_skill(Path(__file__).resolve().parents[2], args.dest.expanduser(), args.skill)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Export failed: {error}\n")
    print(f"Exported {args.skill} to {target}")


if __name__ == "__main__":
    main()
