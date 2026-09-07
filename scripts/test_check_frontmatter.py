import unittest

from check_frontmatter import ALLOWED_KEYS, check_frontmatter


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


if __name__ == "__main__":
    unittest.main()
