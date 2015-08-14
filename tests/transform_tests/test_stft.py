import unittest
from nt.io.audioread import audioread
import numpy as np
from scipy import signal

import nt.testing as tc

from nt.transform.module_stft import _samples_to_stft_frames
from nt.transform.module_stft import _stft_frames_to_samples
from nt.transform.module_stft import stft
from nt.transform.module_stft import istft
from nt.transform.module_stft import _biorthogonal_window_loopy
from nt.transform.module_stft import _biorthogonal_window
from nt.transform.module_stft import stft_to_spectrogram
from nt.transform.module_stft import spectrogram_to_energy_per_frame
from pymatbridge import Matlab

matlab = unittest.skip("matlab")

class TestSTFTMethods(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        path = '/net/speechdb/timit/pcm/train/dr1/fcjf0/sa1.wav'
        self.x = audioread(path)

    def test_samples_to_stft_frames(self):
        size = 1024
        shift = 256

        tc.assert_equal(_samples_to_stft_frames(1023, size, shift), 1)
        tc.assert_equal(_samples_to_stft_frames(1024, size, shift), 1)
        tc.assert_equal(_samples_to_stft_frames(1025, size, shift), 2)
        tc.assert_equal(_samples_to_stft_frames(1024 + 256, size, shift), 2)
        tc.assert_equal(_samples_to_stft_frames(1024 + 257, size, shift), 3)

    def test_stft_frames_to_samples(self):
        size = 1024
        shift = 256

        tc.assert_equal(_stft_frames_to_samples(1, size, shift), 1024)
        tc.assert_equal(_stft_frames_to_samples(2, size, shift), 1024 + 256)

    def test_restore_time_signal_from_stft_and_istft(self):
        x = self.x
        X = stft(x)
        spectrogram = stft_to_spectrogram(X)
        energy = spectrogram_to_energy_per_frame(spectrogram)

        tc.assert_almost_equal(x, istft(X, 1024, 256)[:len(x)])
        tc.assert_equal(X.shape, (186, 513))

        tc.assert_equal(spectrogram.shape, (186, 513))
        tc.assert_isreal(spectrogram)
        tc.assert_array_greater_equal(spectrogram, 0)

        tc.assert_equal(energy.shape, (186,))
        tc.assert_isreal(energy)
        tc.assert_array_greater_equal(energy, 0)

    def test_compare_both_biorthogonal_window_variants(self):
        window = signal.blackman(1024)
        shift = 256

        for_result = _biorthogonal_window_loopy(window, shift)
        vec_result = _biorthogonal_window(window, shift)

        tc.assert_equal(for_result, vec_result)
        tc.assert_equal(for_result.shape, (1024,))

    @matlab
    def test_compare_with_matlab(self):
        y = self.x
        Y_python = stft(y)

        mlab = Matlab('nice -n 3 matlab -nodisplay -nosplash')
        mlab.start()
        _ = mlab.run_code('run /net/home/ldrude/Projects/2015_python_matlab/matlab/startup.m')
        mlab.set_variable('y', y)
        mlab.run_code('Y = transform.stft(y(:), 1024, 256, @blackman);')
        # mlab.run_code('Y(1:10) = 1;')
        Y_matlab = mlab.get_variable('Y').T

        tc.assert_equal(Y_matlab, Y_python)
