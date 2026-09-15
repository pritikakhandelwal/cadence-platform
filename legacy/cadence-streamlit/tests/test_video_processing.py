"""Tests for video feature extraction and visualization error handling."""

import unittest
from modules.feature_extractor import extract_keypoints_from_video
from modules.visualisation import create_overlay_video


class VideoProcessingResourceTests(unittest.TestCase):

    def test_extract_keypoints_from_missing_file_raises_runtime_error(self):
        with self.assertRaises(RuntimeError):
            extract_keypoints_from_video("non_existent_video.mp4", "output.npy")

    def test_create_overlay_missing_files_raises_runtime_error(self):
        with self.assertRaises(RuntimeError):
            create_overlay_video("non_existent_1.mp4", "non_existent_2.mp4", "out.mp4")
