import unittest

from dep_audit import version as v


class VersionTests(unittest.TestCase):
    def test_parse_and_str(self):
        self.assertEqual(str(v.parse_version("1.2.3")), "1.2.3")

    def test_parse_invalid(self):
        with self.assertRaises(ValueError):
            v.parse_version("1.2")

    def test_compare(self):
        self.assertEqual(v.compare_versions("1.0.0", "1.0.1"), -1)
        self.assertEqual(v.compare_versions("2.0.0", "1.9.9"), 1)
        self.assertEqual(v.compare_versions("1.2.3", "1.2.3"), 0)

    def test_bump_type(self):
        self.assertEqual(v.bump_type("1.0.0", "1.0.1"), "patch")
        self.assertEqual(v.bump_type("1.0.0", "1.1.0"), "minor")
        self.assertEqual(v.bump_type("1.0.0", "2.0.0"), "major")

    def test_version_in_range(self):
        self.assertTrue(v.version_in_range("4.17.0", "<4.17.19"))
        self.assertFalse(v.version_in_range("4.17.20", "<4.17.19"))
        self.assertTrue(v.version_in_range("1.0.0", ">=1.0.0,<2.0.0"))
        self.assertFalse(v.version_in_range("2.0.0", ">=1.0.0,<2.0.0"))
        self.assertTrue(v.version_in_range("4.17.21", ">=4.17.19"))


if __name__ == "__main__":
    unittest.main()
