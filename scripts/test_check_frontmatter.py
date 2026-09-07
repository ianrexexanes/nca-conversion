import os
import tempfile
import unittest

from check_frontmatter import ALLOWED_KEYS, check_frontmatter, main


class CheckFrontmatterTest(unittest.TestCase):
    def test_allowed_keys_match_the_spec_exactly(self):
        self.assertEqual(
            ALLOWED_KEYS,
            {"allowed-tools", "compatibility", "description", "license", "metadata", "name"},
        )

    def test_valid_frontmatter_returns_no_offenders(self):
        text = "---\nname: hook-lab\ndescription: Writes hooks.\n---\n\nBody.\n"
        self.assertEqual(check_frontmatter(text), [])

    def test_disallowed_key_is_reported(self):
        text = "---\nname: hook-lab\ndescription: Writes hooks.\nargument-hint: nope\n---\n"
        self.assertEqual(check_frontmatter(text), ["argument-hint"])

    def test_all_six_allowed_keys_together_are_valid(self):
        text = (
            "---\n"
            "name: hook-lab\n"
            "description: Writes hooks.\n"
            "license: MIT\n"
            "compatibility: '>=1.0'\n"
            "allowed-tools: Read\n"
            "metadata:\n"
            "  version: 0.1.0\n"
            "---\n"
        )
        self.assertEqual(check_frontmatter(text), [])

    def test_nested_metadata_keys_are_not_treated_as_top_level(self):
        text = "---\nname: x\ndescription: y\nmetadata:\n  version: 1\n  author: z\n---\n"
        self.assertEqual(check_frontmatter(text), [])

    def test_missing_frontmatter_is_reported_as_a_sentinel(self):
        self.assertEqual(check_frontmatter("No frontmatter here.\n"), ["<no frontmatter>"])

    def test_offenders_are_returned_in_file_order(self):
        text = "---\nname: x\nzebra: 1\ndescription: y\nalpha: 2\n---\n"
        self.assertEqual(check_frontmatter(text), ["zebra", "alpha"])

    def test_quoted_disallowed_key_does_not_slip_through(self):
        text = '---\nname: x\ndescription: y\n"argument-hint": nope\n---\n'
        offenders = check_frontmatter(text)
        self.assertEqual(len(offenders), 1)
        self.assertIn("argument-hint", offenders[0])

    def test_flow_mapping_frontmatter_fails_closed(self):
        text = "---\n{name: x, argument-hint: nope}\n---\n"
        self.assertTrue(
            check_frontmatter(text),
            "frontmatter the guard cannot read must be reported, never passed",
        )

    def test_comments_and_blank_lines_are_ignored(self):
        text = "---\n# a note\n\nname: x\ndescription: y\n---\n"
        self.assertEqual(check_frontmatter(text), [])

    def test_list_items_nested_under_a_key_are_not_top_level(self):
        text = "---\nname: x\ndescription: y\nallowed-tools:\n  - Read\n  - Bash\n---\n"
        self.assertEqual(check_frontmatter(text), [])

    def test_main_returns_1_when_a_skill_violates_the_spec(self):
        with tempfile.TemporaryDirectory() as root:
            skill_dir = os.path.join(root, "skills", "bad")
            os.makedirs(skill_dir)
            with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as handle:
                handle.write("---\nname: bad\ndescription: y\nargument-hint: nope\n---\n")
            self.assertEqual(main(root), 1)

    def test_main_returns_0_on_a_clean_tree(self):
        with tempfile.TemporaryDirectory() as root:
            skill_dir = os.path.join(root, "skills", "good")
            os.makedirs(skill_dir)
            with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as handle:
                handle.write("---\nname: good\ndescription: y\n---\n")
            self.assertEqual(main(root), 0)


if __name__ == "__main__":
    unittest.main()
