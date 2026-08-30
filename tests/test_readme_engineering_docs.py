from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReadmeEngineeringDocsTests(unittest.TestCase):
    def test_readme_contains_complete_portable_startup_flow(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        required = [
            "## 🚀 How to run it",
            "Data Out",
            "PORT = `1234`",
            "Open **DRIVE**",
            "Open **PLAN**",
            "%LOCALAPPDATA%\\FH6 Scenic Navigator\\logs",
        ]
        for text in required:
            self.assertIn(text, readme)

    def test_readme_links_engineering_story(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("## 🧠 Engineering challenges we solved", readme)
        self.assertIn("docs/ENGINEERING_NOTES.md", readme)
        self.assertIn("Directed WVAN", readme)
        self.assertIn("one-way", readme)

    def test_engineering_notes_explain_interchanges_and_directionality(self):
        notes_path = ROOT / "docs" / "ENGINEERING_NOTES.md"
        self.assertTrue(notes_path.exists(), "docs/ENGINEERING_NOTES.md must exist")
        notes = notes_path.read_text(encoding="utf-8")
        required = [
            "Complex interchanges",
            "oneway_forward",
            "no_right_turn",
            "NavPoint",
            "fail-closed",
            "45 m",
            "800 ms",
            "ForzaLabs",
            "Directed WVAN",
        ]
        for text in required:
            self.assertIn(text, notes)


if __name__ == "__main__":
    unittest.main()
