import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("export_skills", ROOT / "tools/codex/export_skills.py")
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class CodexExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "repo"
        shutil.copytree(ROOT / "skills/pr-sweep", self.source / "skills/pr-sweep")
        self.destination = self.base / "exported"

    def test_self_contained_export_preserves_sources_and_resources(self):
        source_file = self.source / "skills/pr-sweep/SKILL.md"
        original = source_file.read_bytes()
        target = exporter.export_skill(self.source, self.destination, "pr-sweep")
        self.assertEqual(source_file.read_bytes(), original)
        content = (target / "SKILL.md").read_text()
        header, body = content[4:].split("\n---\n", 1)
        self.assertEqual({line.split(":", 1)[0] for line in header.splitlines()}, {"name", "description"})
        self.assertIn("adapters/codex.md", body)
        self.assertNotIn("$ARGUMENTS", body)
        for relative in ["adapters/codex.md", "EVIDENCE.md", "agents/openai.yaml"]:
            self.assertEqual((target / relative).read_bytes(), (self.source / "skills/pr-sweep" / relative).read_bytes())
        # The exported copy can be moved away from the clone without losing references.
        moved = self.base / "moved"
        target.rename(moved)
        self.assertTrue((moved / "adapters/codex.md").is_file())

    def test_existing_customized_destination_is_not_replaced(self):
        target = self.destination / "pr-sweep"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("custom skill")
        with self.assertRaises(FileExistsError):
            exporter.export_skill(self.source, self.destination, "pr-sweep")
        self.assertEqual((target / "SKILL.md").read_text(), "custom skill")

    def test_unsupported_skill_does_not_create_output(self):
        with self.assertRaises(ValueError):
            exporter.export_skill(self.source, self.destination, "error-sweep")
        self.assertFalse(self.destination.exists())

    def test_missing_adapter_does_not_create_partial_install(self):
        (self.source / "skills/pr-sweep/adapters/codex.md").unlink()
        with self.assertRaises(ValueError):
            exporter.export_skill(self.source, self.destination, "pr-sweep")
        self.assertFalse(self.destination.exists())

    def test_external_symlink_is_rejected(self):
        (self.source / "skills/pr-sweep/external").symlink_to(ROOT / "README.md")
        with self.assertRaises(ValueError):
            exporter.export_skill(self.source, self.destination, "pr-sweep")
        self.assertFalse(self.destination.exists())

    def test_changed_frontmatter_fails_instead_of_truncating_description(self):
        p = self.source / "skills/pr-sweep/SKILL.md"
        p.write_text("---\nname: pr-sweep\ndescription: |\n  Multi-line description\n---\nBody\n")
        with self.assertRaises(ValueError):
            exporter.export_skill(self.source, self.destination, "pr-sweep")
        self.assertFalse(self.destination.exists())


if __name__ == "__main__":
    unittest.main()
