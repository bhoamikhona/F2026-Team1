"""Regression checks for the editable manuscript review export."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


class WordExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory()
        cls.root = Path(cls.workspace.name)
        source = Path(__file__).resolve().parent
        for name in ('export_word.py', 'paper.tex', 'version-history.tex'):
            shutil.copy2(source / name, cls.root / name)
        (cls.root / 'figures').symlink_to(source / 'figures', target_is_directory=True)
        # A changed TeX paragraph must reach the next export, not a cached Word copy.
        paper = cls.root / 'paper.tex'
        paper.write_text(paper.read_text().replace(
            r'\section{Results}', 'Export freshness check.\n\n' + r'\section{Results}'))
        subprocess.run([sys.executable, str(cls.root / 'export_word.py')], check=True)
        cls.doc = Document(cls.root / 'paper.docx')

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def test_review_colors_and_no_latex_leaks(self):
        fills = {e.get(qn('w:fill')) for e in self.doc._element.iter(qn('w:shd'))}
        self.assertTrue({'FFDAB9', 'FFDCDC', 'DCF5DC'} <= fills)
        text = '\n'.join(p.text for p in self.doc.paragraphs)
        self.assertIn('Export freshness check.', text)
        self.assertIn('[Suggested replacement:', text)
        self.assertNotIn('\\', text)
        self.assertNotIn('\x01', text)

    def test_both_external_tables_and_new_column_shading(self):
        original = next(t for t in self.doc.tables if len(t.columns) == 5)
        expanded = next(t for t in self.doc.tables if len(t.columns) == 9)
        self.assertEqual(len(original.rows), 6)
        self.assertEqual(len(expanded.rows), 7)
        self.assertEqual(expanded.cell(2, 8).text, '0.228')
        for row in expanded.rows:
            for index, cell in enumerate(row.cells):
                shades = list(cell._tc.tcPr.iter(qn('w:shd')))
                self.assertEqual(bool(shades), index >= 5)

    def test_formulas_remain_editable(self):
        equations = list(self.doc._element.iter(qn('m:oMath')))
        self.assertGreaterEqual(len(equations), 10)
        math_text = ''.join(e.text or '' for e in self.doc._element.iter(qn('m:t')))
        self.assertIn('0.90', math_text)
        self.assertIn('0.05', math_text)
        self.assertIn('Specificity', math_text)
        self.assertEqual(len(self.doc.inline_shapes), 3)  # Only original figures.


if __name__ == '__main__':
    unittest.main()
