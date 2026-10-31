import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_frontmatter  # noqa: E402

VERSION = "0.2.0"


def skill_version(path: Path) -> str:
    match = re.search(r"^metadata:\s*\n(?:[ \t]+.*\n)*?[ \t]+version:\s*(\S+)", path.read_text(encoding="utf-8"), re.M)
    return match.group(1).strip("\"'") if match else "<none>"


class RepoStructureTest(unittest.TestCase):
    def test_every_version_is_0_2_0(self):
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["version"], VERSION)
        self.assertEqual(market["metadata"]["version"], VERSION)
        skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
        self.assertGreaterEqual(len(skills), 7)
        for path in skills:
            self.assertEqual(skill_version(path), VERSION, str(path.relative_to(ROOT)))

    def test_frontmatter_guard_passes(self):
        self.assertEqual(check_frontmatter.main(str(ROOT)), 0)


if __name__ == "__main__":
    unittest.main()
