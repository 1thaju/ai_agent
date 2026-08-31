import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from routers.converse import merge_wav_files


class MergeWavFilesTests(unittest.TestCase):
    def test_merge_wav_files_empty_list_returns_empty_bytes(self):
        self.assertEqual(merge_wav_files([]), b"")


if __name__ == "__main__":
    unittest.main()
