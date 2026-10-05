import unittest

from mailbox_address_parser import Mailbox, parse_mailbox


class TestParseMailbox(unittest.TestCase):
    def test_bare_simple(self):
        m = parse_mailbox("alice@example.org")
        self.assertIsNone(m.display_name)
        self.assertEqual(m.local_part, "alice")
        self.assertEqual(m.domain, "example.org")

    def test_bare_with_dots(self):
        m = parse_mailbox("first.last@example.org")
        self.assertEqual(m.local_part, "first.last")
        self.assertEqual(m.domain, "example.org")

    def test_bare_quoted_local_part(self):
        m = parse_mailbox('"a.b"@example.org')
        self.assertEqual(m.local_part, "a.b")
        self.assertEqual(m.domain, "example.org")

    def test_bare_quoted_local_part_with_specials(self):
        m = parse_mailbox('"a b"@example.org')
        self.assertEqual(m.local_part, "a b")

    def test_quoted_pair_in_local_part(self):
        m = parse_mailbox('"a\\"b"@example.org')
        self.assertEqual(m.local_part, 'a"b')

    def test_angle_bracket_simple(self):
        m = parse_mailbox("Alice <alice@example.org>")
        self.assertEqual(m.display_name, "Alice")
        self.assertEqual(m.local_part, "alice")
        self.assertEqual(m.domain, "example.org")

    def test_angle_bracket_quoted_display(self):
        m = parse_mailbox('"Alice Q" <alice@example.org>')
        self.assertEqual(m.display_name, "Alice Q")

    def test_angle_bracket_quoted_pair_display(self):
        m = parse_mailbox('"Alice \\"Bob" <alice@example.org>')
        self.assertEqual(m.display_name, 'Alice "Bob')

    def test_display_name_multi_word(self):
        m = parse_mailbox("Alice Carol <alice@example.org>")
        self.assertEqual(m.display_name, "Alice Carol")

    def test_display_name_mixed_quoted_and_atom(self):
        m = parse_mailbox('"Alice" Bob <alice@example.org>')
        self.assertEqual(m.display_name, "Alice Bob")

    def test_comment_in_display_name(self):
        m = parse_mailbox("Alice (the admin) <alice@example.org>")
        self.assertEqual(m.display_name, "Alice")
        self.assertEqual(m.local_part, "alice")

    def test_comment_around_at_sign(self):
        m = parse_mailbox("alice(comment)@example.org")
        self.assertEqual(m.local_part, "alice")
        self.assertEqual(m.domain, "example.org")

    def test_comment_around_angle_brackets(self):
        m = parse_mailbox("(intro) Alice <alice@example.org> (trailer)")
        self.assertEqual(m.display_name, "Alice")
        self.assertEqual(m.local_part, "alice")

    def test_nested_comment(self):
        m = parse_mailbox("alice(a (b) c)@example.org")
        self.assertEqual(m.local_part, "alice")
        self.assertEqual(m.domain, "example.org")

    def test_comment_with_quoted_pair(self):
        m = parse_mailbox(r"alice(a\)b)@example.org")
        self.assertEqual(m.local_part, "alice")
        self.assertEqual(m.domain, "example.org")

    def test_domain_with_dot_atom(self):
        m = parse_mailbox("alice@sub.example.org")
        self.assertEqual(m.domain, "sub.example.org")

    def test_empty_input(self):
        with self.assertRaises(ValueError):
            parse_mailbox("")

    def test_missing_domain(self):
        with self.assertRaises(ValueError):
            parse_mailbox("alice@")

    def test_missing_local_part(self):
        with self.assertRaises(ValueError):
            parse_mailbox("@example.org")

    def test_missing_at_sign(self):
        with self.assertRaises(ValueError):
            parse_mailbox("alice example.org")

    def test_missing_closing_bracket(self):
        with self.assertRaises(ValueError):
            parse_mailbox("Alice <alice@example.org")

    def test_trailing_garbage(self):
        with self.assertRaises(ValueError):
            parse_mailbox("alice@example.org junk")

    def test_unterminated_quoted_string(self):
        with self.assertRaises(ValueError):
            parse_mailbox('"unterminated@example.org')

    def test_unterminated_comment(self):
        with self.assertRaises(ValueError):
            parse_mailbox("alice (oops@example.org")

    def test_dot_atom_leading_dot(self):
        with self.assertRaises(ValueError):
            parse_mailbox(".alice@example.org")

    def test_dot_atom_trailing_dot_local(self):
        with self.assertRaises(ValueError):
            parse_mailbox("alice.@example.org")

    def test_dot_atom_trailing_dot_domain(self):
        with self.assertRaises(ValueError):
            parse_mailbox("alice@example.org.")

    def test_return_type(self):
        m = parse_mailbox("alice@example.org")
        self.assertIsInstance(m, Mailbox)

    def test_mailbox_fields(self):
        m = parse_mailbox("Alice <alice@example.org>")
        self.assertEqual(m.display_name, "Alice")
        self.assertEqual(m.local_part, "alice")
        self.assertEqual(m.domain, "example.org")


if __name__ == "__main__":
    unittest.main()
