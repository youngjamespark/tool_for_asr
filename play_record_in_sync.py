from pathlib import PurePath
from pydub import AudioSegment
import pyaudio
import wave
import time
import queue
import wave
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure
import tkinter as tk


def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text


def get_current_time():
    """Return Current Time in MS."""
    return int(round(time.time() * 1000))


def flac2wav(flac_file):
    flac_file_path = PurePath(flac_file)
    wav_file_path = flac_file_path.name.replace(flac_file_path.suffix, ".wav")
    flac_tmp_audio_data = AudioSegment.from_file(flac_file_path, "flac")
    flac_tmp_audio_data.export(wav_file_path, format="wav")


class MicrophoneStream:
    """ Opens a recording stream as a generator yielding the audio chunks. """

    def __init__(self, rate, chunk, channels, outQueue, in_idx, out_idx):
        self._rate = rate
        self._chunk = chunk
        self._channels = channels
        self._buff = queue.Queue()
        self.closed = True
        self._outQ = outQueue
        self.in_dev_id = in_idx
        self.out_dev_id = out_idx

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            channels=self._channels,
            rate=self._rate,
            input=True,
            output=True,
            input_device_index=self.in_dev_id,
            output_device_index=self.out_dev_id,
            frames_per_buffer=self._chunk,
            stream_callback=self._fill_buffer,
        )
        self.closed = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that client's
        # streaming_recognize method will not block the process termination
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status):
        self._buff.put(in_data)
        out_data = self._outQ.get()
        return out_data, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            chunk = self._buff.get()
            if chunk is None:
                return

            data = [chunk]

            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break
            yield b''.join(data)


def play_and_record(sample_rate, channels, in_idx, out_idx, src_file, rec_file):
    """ Start bidirectional streaming from microphone input to speech API """
    outQ = queue.Queue()
    chunk_size = int(sample_rate * 2 / 100)                 # 20msec

    with MicrophoneStream(sample_rate, chunk_size, channels, outQ, in_idx, out_idx) as stream:
        audio_generator = stream.generator()

        with wave.open(src_file, 'rb') as file:
            with wave.open(rec_file, "wb") as wf_near:
                wf_near.setnchannels(channels)
                wf_near.setsampwidth(2)
                wf_near.setframerate(sample_rate)

                data = file.readframes(-1)
                long_empty = bytes(chunk_size * 2 * 15)     # 300 msec
                speech = data + long_empty
                offset = chunk_size * 2

                out_data = speech[:offset]
                speech = speech[offset:]
                outQ.put(out_data)

                next(audio_generator)
                for content in audio_generator:
                    out_data = speech[:offset]
                    speech = speech[offset:]
                    outQ.put(out_data)

                    wf_near.writeframes(content)
                    if len(out_data) < (chunk_size * 2):
                        break


if __name__ == '__main__':
    play_and_record(16000, 1, "wave\\far.wav", "wave\\after_near.wav")
