import unittest

from nt.io import load_json
from nt.testing import db_test
from nt.database.keys import *

NoiseX_92_json = db_test.ROOT / "NoiseX_92.json"
#NoiseX_92_json = "NoiseX_92.json"

class TestNoiseX92Database(db_test.DatabaseTest):

        def setUp(self):
            self.json = load_json(NoiseX_92_json)

        def test_examples(self):
            self.assert_in_example([AUDIO_PATH])

        def test_dataset(self):
            self.assert_in_datasets(['standard', '16kHz'])

        def test_len(self):
            self.assertEqual(len(self.json[DATASETS]['standard']), 15)
            self.assertEqual(len(self.json[DATASETS]['16kHz']), 15)
            #self.assertEqual(len(self.json[DATASETS]['metro']), 0)


if __name__ == '__main__':
    unittest.main()
