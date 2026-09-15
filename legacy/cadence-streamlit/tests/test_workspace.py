from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from modules.workspace import create_analysis_workspace


class AnalysisWorkspaceTests(unittest.TestCase):
    def test_analysis_workspaces_are_unique_and_isolated(self):
        with TemporaryDirectory() as temp_dir:
            first = create_analysis_workspace(Path(temp_dir))
            second = create_analysis_workspace(Path(temp_dir))

            self.assertNotEqual(first.run_id, second.run_id)
            self.assertTrue(first.root.is_dir())
            self.assertTrue(second.root.is_dir())
            self.assertNotEqual(first.root, second.root)
            self.assertEqual(first.professional_upload.parent, first.root)
            self.assertEqual(second.user_keypoints.parent, second.root)
