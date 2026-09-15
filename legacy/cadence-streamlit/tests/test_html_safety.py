import unittest

from modules.html_safety import escape_html


class HtmlSafetyTests(unittest.TestCase):
    def test_escapes_html_and_attribute_characters(self):
        unsafe_text = '<img src=x onerror="alert(1)">'

        self.assertEqual(
            escape_html(unsafe_text),
            "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;",
        )
