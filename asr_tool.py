import tkinter as tk
from tkinter import PhotoImage, ttk
from tkinter.constants import HORIZONTAL
import tkinter.font as tkFont
from tkinter import messagebox
from tkinter import filedialog
import os
from pathlib import Path
import pyaudio
import numpy as np
from play_record_in_sync import play_and_record
import threading
import wave
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from pydub import AudioSegment
import pesq_assess

STOPPED = 0
PAUSED = 2
STARTED = 1


def flac2wav(flac_file, wav_file):
    flac_tmp_audio_data = AudioSegment.from_file(flac_file, "flac")
    flac_tmp_audio_data.export(wav_file, format="wav")


def mp3towav(mp3_file, wav_file):
    mp3_tmp_audio_data = AudioSegment.from_mp3(mp3_file)
    mp3_tmp_audio_data.export(wav_file, format="wav")


class Tool_GUI():

    def __init__(self, root):
        # Definition for audio devices
        self.input_devices_list = []
        self.output_devices_list = []
        self.input_device_index = None
        self.output_device_index = None
        self.find_device()

        # Main Dialog Definition
        main_dialog = root
        main_dialog.title("Tool for ASR")
        main_dialog.geometry("900x650")
        main_dialog.resizable(False, False)
        self.window = tk.Frame(master=main_dialog, relief="solid", bd=2, height=630, width=880)
        self.window.place(x=10, y=10)

        # Font definition
        bc10i = tkFont.Font(family="bitstream charter", size=10, slant="italic")
        bc10b = tkFont.Font(family="bitstream charter", size=10, weight="bold")
        bc12b = tkFont.Font(family="bitstream charter", size=12, weight="bold")
        bc12i = tkFont.Font(family="bitstream charter", size=12, slant="italic")

        # Definition for File info Frame
        file_info_frame = tk.Frame(master=self.window, relief="solid", bd=1, height=100, width=500)
        file_info_frame.place(x=10, y=10)

        # Definition for Source directory
        lbl_src = tk.Label(master=file_info_frame, text="Source", fg="coral4", font=bc12b, anchor="w")
        lbl_src.place(x=10, y=15)
        self.btn_src_path_var = tk.StringVar()
        self.btn_src_path_var.set("Source directory")
        self.btn_src_path = tk.Button(master=file_info_frame, textvariable=self.btn_src_path_var, font=bc12i, fg="gray",
                                      width=40, bg='white', anchor="w", command=lambda: self.select_src_folder())
        self.btn_src_path.place(x=115, y=10)

        # Definition for Destination directory
        lbl_dst = tk.Label(master=file_info_frame, text="Destination", fg="coral4", font=bc12b, anchor="w")
        lbl_dst.place(x=10, y=60)
        self.btn_dst_path_var = tk.StringVar()
        self.btn_dst_path_var.set("Destination directory")
        self.btn_dst_path = tk.Button(master=file_info_frame, textvariable=self.btn_dst_path_var, font=bc12i, fg="gray",
                                      width=40, bg='white', anchor="w", command=lambda: self.select_dst_folder())
        self.btn_dst_path.place(x=115, y=55)

        # Definition for device settings frame
        dev_info_frame = tk.Frame(master=self.window, relief="solid", bd=1, height=190, width=345)
        dev_info_frame.place(x=520, y=10)

        # Combobox Definition for Sample Rate
        lbl_sample_rate = tk.Label(master=dev_info_frame, text="Sampling", fg="coral4", font=bc12b, anchor="w")
        lbl_sample_rate.place(x=10, y=15)
        self.cmb_sample_rate_var = tk.StringVar()
        self.cmb_sample_rate = ttk.Combobox(master=dev_info_frame, textvariable=self.cmb_sample_rate_var,
                                            state="readonly", values=[8000, 16000, 44100, 48000])
        self.cmb_sample_rate.config(height=1, width=10, font=bc10i)
        self.cmb_sample_rate.place(x=100, y=18)
        self.cmb_sample_rate.current(1)
        print("default sample rate = ", self.cmb_sample_rate.get())

        # Combobox Definition for Channel number
        lbl_channel = tk.Label(master=dev_info_frame, text="Channel", fg="coral4", font=bc12b, anchor="w")
        lbl_channel.place(x=10, y=60)
        self.cmb_channel_var = tk.StringVar()
        self.cmb_channel = ttk.Combobox(master=dev_info_frame, textvariable=self.cmb_channel_var, state="readonly",
                                        values=[1, 2])
        self.cmb_channel.config(height=1, width=10, font=bc10i)
        self.cmb_channel.place(x=100, y=63)
        self.cmb_channel.current(0)
        print("default channel numbers = ", self.cmb_channel.get())

        # Combobox Definition for Output device
        lbl_out_dev = tk.Label(master=dev_info_frame, text="Output", fg="coral4", font=bc12b, anchor="w")
        lbl_out_dev.place(x=10, y=105)
        # self.cmb_out_dev_var = tk.StringVar()
        self.cmb_out_dev = ttk.Combobox(master=dev_info_frame, state="readonly", values=[],
                                        postcommand=self.cmb_out_dev_update)
        self.cmb_out_dev.config(height=1, width=28, font=bc10i)
        self.cmb_out_dev.place(x=100, y=108)
        self.cmb_out_dev_update()
        self.cmb_out_dev_init()
        print("default output device = ", self.cmb_out_dev.get())

        # Combobox Definition for Input device
        lbl_in_dev = tk.Label(master=dev_info_frame, text="Input", fg="coral4", font=bc12b, anchor="w")
        lbl_in_dev.place(x=10, y=150)
        self.cmb_in_dev_var = tk.StringVar()
        self.cmb_in_dev = ttk.Combobox(master=dev_info_frame, textvariable=self.cmb_in_dev_var,
                                       state="readonly", values=[], postcommand=self.cmb_in_dev_update)
        self.cmb_in_dev.config(height=1, width=28, font=bc10i)
        self.cmb_in_dev.place(x=100, y=153)
        self.cmb_in_dev_update()
        self.cmb_in_dev_init()
        print("default input device = ", self.cmb_in_dev.get())

        # Definition for Progress Info Frame
        prog_info_frame = tk.Frame(master=self.window, relief="solid", bd=1, height=80, width=500)
        prog_info_frame.place(x=10, y=120)

        # Definition for Current working file entry
        lbl_curr = tk.Label(master=prog_info_frame, text="Current file", fg="coral4", font=bc12b, anchor="w")
        lbl_curr.place(x=10, y=15)
        self.ent_curr_file_var = tk.StringVar()
        self.ent_curr_file_var.set("Working file...")
        ent_curr_file = tk.Entry(master=prog_info_frame, textvariable=self.ent_curr_file_var, font=bc12i, fg="gray",
                                 width=30, bg="white")
        ent_curr_file.place(x=115, y=15)

        # Definition for Progress information
        lbl_prog = tk.Label(master=prog_info_frame, text="Progress", fg="coral4", font=bc12b, anchor="w")
        lbl_prog.place(x=10, y=45)
        self.prog_bar = ttk.Progressbar(master=prog_info_frame, orient=HORIZONTAL, length=370, mode="determinate")
        self.prog_bar.place(x=115, y=47)
        self.update_prog_bar(0)

        # Definition for Reference Waveform Frame
        self.frm_src_wave = tk.Canvas(master=self.window, relief="solid", bd=2, height=150, width=855, bg="white")
        self.frm_src_wave.place(x=10, y=210)
        lbl_ref = tk.Label(master=self.frm_src_wave, text="Reference", fg="gray", font=bc12i, anchor="w", bg="white")
        lbl_ref.place(x=10, y=10)

        # Draw blank wave box for source
        self.fig_src = Figure(figsize=(8.45, 1.43), dpi=100)
        self.fig_src.subplots_adjust(bottom=0.18, left=0.1)
        self.a1 = self.fig_src.add_subplot(111)
        self.a1.set_ylim([-32768, 32767])
        self.a1.set_yticklabels([])
        self.a1.set_xticklabels([])
        self.a1.plot([])
        self.canvas_src = FigureCanvasTkAgg(self.fig_src, master=self.frm_src_wave)
        self.canvas_src.get_tk_widget().place(x=10, y=10)
        self.canvas_src.draw_idle()

        # Definition for Recorded Waveform Frame
        self.frm_rec_wave = tk.Canvas(master=self.window, relief="solid", bd=2, height=150, width=855, bg="white")
        self.frm_rec_wave.place(x=10, y=370)
        lbl_rec = tk.Label(master=self.frm_rec_wave, text="Recorded", fg="gray", font=bc12i, anchor="w", bg="white")
        lbl_rec.place(x=10, y=10)

        # Draw blank wave box for recorded
        self.fig_rec = Figure(figsize=(8.45, 1.43), dpi=100)
        self.fig_rec.subplots_adjust(bottom=0.18, left=0.1)
        self.a2 = self.fig_rec.add_subplot(111)
        self.a2.set_ylim([-32768, 32767])
        self.a2.set_yticklabels([])
        self.a2.set_xticklabels([])
        self.a2.plot([])
        self.canvas_rec = FigureCanvasTkAgg(self.fig_rec, master=self.frm_rec_wave)
        self.canvas_rec.get_tk_widget().place(x=10, y=10)
        self.canvas_rec.draw_idle()

        # Definition for option checkbox
        frm_conv = tk.Frame(master=self.window, relief='solid', bd=1, height=70, width=400)
        frm_conv.place(x=10, y=540)

        self.play_checkVar = tk.IntVar()
        play_check = tk.Checkbutton(master=frm_conv, text="play & record", variable=self.play_checkVar, font=bc12i,
                                    command=lambda: self.play_check_chk())
        play_check.place(x=15, y=20)
        self.play_checkVar.set(1)

        self.flac_checkVar = tk.IntVar()
        flac_check = tk.Checkbutton(master=frm_conv, text="flac to wav", variable=self.flac_checkVar, font=bc12i,
                                    command=lambda: self.flac_check_chk())
        flac_check.place(x=150, y=20)

        self.mp3_checkVar = tk.IntVar()
        mp3_check = tk.Checkbutton(master=frm_conv, text="mp3 to wav", variable=self.mp3_checkVar, font=bc12i,
                                   command=lambda: self.mp3_check_chk())
        mp3_check.place(x=270, y=20)

        # Definition for MOS score
        frm_mos = tk.Frame(master=self.window, relief='solid', bd=1, height=70, width=130)
        frm_mos.place(x=430, y=540)
        lbl_mos = tk.Label(master=frm_mos, text='MOS', fg='gray', font=bc12b)
        lbl_mos.place(x=10, y=23)
        self.ent_mos_var = tk.StringVar()
        self.ent_mos_var.set("0.00")
        self.ent_mos = tk.Label(master=frm_mos, textvariable=self.ent_mos_var, font=bc12i, fg='black', anchor="e",
                                width=5, height=2)
        self.ent_mos.place(x=60, y=15)

        # Definition for Buttons
        self.img_start = PhotoImage(file="resources\\start.png").subsample(10, 10)
        self.img_pause = PhotoImage(file="resources\\pause.png").subsample(10, 10)
        self.img_stop = PhotoImage(file="resources\\stop.png").subsample(10, 10)

        self.tool_started = tk.IntVar()
        self.tool_started.set(STOPPED)
        self.btn_start = tk.Button(master=self.window, image=self.img_start, font=bc12b,
                                   command=lambda: self.tool_start(), borderwidth=0)
        self.btn_start.place(x=700, y=538)

        self.btn_stop = tk.Button(master=self.window, image=self.img_stop, font=bc12b,
                                  command=lambda: self.tool_stop(), borderwidth=0)
        self.btn_stop.place(x=785, y=538)
        self.btn_stop["state"] = "disabled"

    def find_device(self):
        audio = pyaudio.PyAudio()
        device_num = audio.get_device_count()

        info = audio.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        indev = {}
        outdev = {}
        self.input_devices_list.clear()
        self.output_devices_list.clear()
        for i in range(numdevices):
            # print("Input Device id", i, "-", audio.get_device_info_by_host_api_device_index(0, i))
            if audio.get_device_info_by_host_api_device_index(0, i)['maxInputChannels'] > 0:
                indev['name'] = audio.get_device_info_by_host_api_device_index(0, i)['name']
                indev['index'] = audio.get_device_info_by_host_api_device_index(0, i)['index']
                self.input_devices_list.append(indev)
                indev = {}
            if audio.get_device_info_by_host_api_device_index(0, i)['maxOutputChannels'] > 0:
                outdev["name"] = audio.get_device_info_by_host_api_device_index(0, i)['name']
                outdev['index'] = audio.get_device_info_by_host_api_device_index(0, i)['index']
                self.output_devices_list.append(outdev)
                outdev = {}

        for i in range(len(self.input_devices_list)):
            if audio.get_default_input_device_info()['name'] == self.input_devices_list[i]['name']:
                self.input_device_index = i

        for i in range(len(self.output_devices_list)):
            if audio.get_default_output_device_info()['name'] == self.output_devices_list[i]['name']:
                self.output_device_index = i
        audio.terminate()

    # update input devices Combobox
    def cmb_in_dev_update(self):
        self.find_device()
        self.cmb_in_dev["values"] = []
        lst = []
        for i in range(len(self.input_devices_list)):
            lst.append(self.input_devices_list[i]['name'])
        self.cmb_in_dev["values"] = lst

    # set Default input device
    def cmb_in_dev_init(self):
        self.cmb_in_dev.current(self.input_device_index)

    # update output devices Combobox
    def cmb_out_dev_update(self):
        self.find_device()
        self.cmb_out_dev["values"] = []
        lst = []
        for i in range(len(self.output_devices_list)):
            lst.append(self.output_devices_list[i]['name'])
        self.cmb_out_dev["values"] = lst

    # set Default output device
    def cmb_out_dev_init(self):
        self.cmb_out_dev.current(self.output_device_index)

    def cmb_out_dev_index_get(self):
        self.output_device_index = self.output_devices_list[self.cmb_out_dev.current()]['index']
        # print("output_device_index = ", self.output_device_index)

    def cmb_in_dev_index_get(self):
        self.input_device_index = self.input_devices_list[self.cmb_in_dev.current()]['index']
        # print("input_device_index = ", self.input_device_index)

    # Update Progress information
    def update_prog_bar(self, percent):
        self.prog_bar["value"] = int(370 * percent / 370)

    def thread_play_and_record(self):
        self.cmb_out_dev_index_get()
        self.cmb_in_dev_index_get()

        # copy files from source directories to destination directories
        dirs_list = []
        files_list = []
        for (root, dirs, files) in os.walk(self.btn_src_path_var.get(), topdown=True):
            dirs_list.append(root)
            # print("root =", root)
            # print(dirs)
            # # print(files)
            if files:
                for file in files:
                    if file.endswith(".wav"):
                        files_list.append(os.path.join(root, file))

        print("total files = ", len(files_list))

        total_number = len(files_list)

        # new destination directories list
        new_dirs_list = []
        for i in range(len(dirs_list)):
            new_dir = self.btn_dst_path_var.get() + "\\" + dirs_list[i][len(dirs_list[0]):]
            new_dirs_list.append(os.path.abspath(new_dir))
            # print(new_dirs_list[i])
        new_files_list = []
        for i in range(len(files_list)):
            new_file = self.btn_dst_path_var.get() + "\\" + files_list[i][len(dirs_list[0]):]
            # new_file_wav = new_file.replace(".flac", ".wav")
            new_files_list.append(os.path.abspath(new_file))

        # make destination directories
        for i in range(1, len(new_dirs_list)):
            print(new_dirs_list[i])
            try:
                os.mkdir(new_dirs_list[i])
            except FileExistsError:
                print(new_dirs_list[i], " exists.")

        for i in range(len(files_list)):
            # flac2wav(files_list[i], new_files_list[i])
            # print(files_list[i])
            # print(new_files_list[i])
            self.ent_curr_file_var.set(os.path.basename(new_files_list[i]))
            self.update_prog_bar(int(i / total_number * 100))
            # shutil.copy(files_list[i], new_files_list[i])

            if self.tool_started.get() == STOPPED:
                print(self.tool_started.get())
                break

            play_and_record(int(self.cmb_sample_rate.get()), int(self.cmb_channel.get()), self.input_device_index,
                            self.output_device_index, files_list[i], new_files_list[i])
            self.draw_src_wave(files_list[i])

            self.draw_rec_wave(new_files_list[i])
            mos = pesq_assess.evaluate(files_list[i], new_files_list[i], 16000, 'wb')
            
            self.ent_mos_var.set(f'{mos:.2f}')
            self.update_prog_bar((int(i+1)/total_number * 100))

        self.tool_stop()
        print("thread end")
        messagebox.showwarning("Information", "Play and Record finished.")


    def thread_pause_play_and_record(self):
        pass

    def thread_stop_play_and_record(self):
        pass

    def tool_start(self):
        print("src=", self.btn_src_path_var.get())
        print("dst=", self.btn_dst_path_var.get())
        if not(os.path.isdir(self.btn_src_path_var.get())) or not(os.path.isdir(self.btn_dst_path_var.get())):
            messagebox.showwarning("Warning", "To check Source or Destination directories.")
            return
        if self.tool_started.get() == STOPPED:
            self.tool_started.set(STARTED)
            self.btn_start.config(image=self.img_pause)
            self.btn_stop["state"] = "normal"
            self.dialog_selectable(False)

            if self.flac_checkVar.get():
                tool = threading.Thread(target=self.thread_flac_to_wav, )
                tool.start()
            elif self.mp3_checkVar.get():
                tool = threading.Thread(target=self.thread_mp3_to_wav, )
                tool.start()
            else:
                tool = threading.Thread(target=self.thread_play_and_record, )
                tool.start()
        elif self.tool_started.get() == STARTED:
            self.tool_started.set(PAUSED)
            self.btn_start.config(image=self.img_start)
            self.btn_stop["state"] = "normal"
            self.dialog_selectable(False)
        elif self.tool_started.get() == PAUSED:
            self.tool_started.set(STARTED)
            self.btn_start.config(image=self.img_pause)
            self.btn_stop["state"] = "normal"
            self.dialog_selectable(False)
        print("start thread started")

    def tool_stop(self):
        if self.tool_started.get() == STARTED:
            self.tool_started.set(STOPPED)
            self.btn_start.config(image=self.img_start)
            self.btn_stop.config(relief="flat")
            self.btn_stop["state"] = "disabled"
            self.dialog_selectable(True)
        elif self.tool_started.get() == PAUSED:
            self.tool_started.set(STOPPED)
            self.btn_start.config(image=self.img_start)
            self.btn_stop["state"] = "disabled"
            self.dialog_selectable(False)

    def dialog_selectable(self, enable):
        if not enable:
            self.btn_src_path["state"] = "disabled"
            self.btn_dst_path["state"] = "disabled"
            self.cmb_sample_rate["state"] = "disabled"
            self.cmb_channel["state"] = "disabled"
            self.cmb_out_dev["state"] = "disabled"
            self.cmb_in_dev["state"] = "disabled"
        else:
            self.btn_src_path["state"] = "normal"
            self.btn_dst_path["state"] = "normal"
            self.cmb_sample_rate["state"] = "normal"
            self.cmb_channel["state"] = "normal"
            self.cmb_out_dev["state"] = "normal"
            self.cmb_in_dev["state"] = "normal"

    def select_src_folder(self):
        new_folder = filedialog.askdirectory(initialdir=str(Path.home()), title="Select a Source directory")
        try:
            if new_folder != "":
                if os.path.isdir(new_folder):
                    self.btn_src_path_var.set(os.path.abspath(new_folder))
                else:
                    messagebox.showwarning("Warning", "The selected location is not a directory")
        except:
            messagebox.showwarning("Warning", "Warning: There is a problem with the Directory !")

    def select_dst_folder(self):
        new_dst_folder = filedialog.askdirectory(initialdir=str(Path.home()), title="Select a Destination directory")
        try:
            if new_dst_folder != "":
                if os.path.isdir(new_dst_folder):
                    self.btn_dst_path_var.set(os.path.abspath(new_dst_folder))
                else:
                    messagebox.showwarning("Warning", "The selected location is not a directory")
        except:
            messagebox.showwarning("Warning", "Warning: There is a problem with the Directory !")

    def draw_src_wave(self, src_file):
        spf = wave.open(src_file, "rb")
        signal = spf.readframes(-1)
        spf.close()
        signal = np.frombuffer(signal, "int16")
        print("source samples = ", len(signal))
        fs = spf.getframerate()
        Time = np.linspace(0, len(signal) / fs, num=len(signal))
        self.a1.clear()
        self.a1.set_ylim([-32768, 32767])
        self.a1.set_xlim([0, len(signal) / fs])
        self.a1.set_yticklabels([])
        self.a1.plot(Time, signal)
        self.canvas_src.draw_idle()

    def draw_rec_wave(self, rec_file):
        spf = wave.open(rec_file, "rb")
        rec_signal = spf.readframes(-1)
        spf.close()
        rec_signal = np.frombuffer(rec_signal, "int16")
        print("recorded samples = ", len(rec_signal))
        fs = spf.getframerate()
        Time = np.linspace(0, len(rec_signal) / fs, num=len(rec_signal))
        self.a2.clear()
        self.a2.set_ylim([-32768, 32767])
        self.a2.set_xlim([0, len(rec_signal) / fs])
        self.a2.set_yticklabels([])
        self.a2.plot(Time, rec_signal)
        self.canvas_rec.draw_idle()

    def play_check_chk(self):
        if self.play_checkVar.get():
            self.mp3_checkVar.set(0)
            self.flac_checkVar.set(0)

    def flac_check_chk(self):
        if self.flac_checkVar.get():
            self.play_checkVar.set(0)
            self.mp3_checkVar.set(0)

    def mp3_check_chk(self):
        if self.mp3_checkVar.get():
            self.play_checkVar.set(0)
            self.flac_checkVar.set(0)

    def thread_flac_to_wav(self):
        # conv_thread = threading.Thread(target=self.flac_to_wav, )
        # conv_thread.start()
        self.flac_to_wav()
        self.tool_stop()
        print("flac to wav thread end.")
        messagebox.showwarning("Information", "File conversion from flac to wav finished.")

    def flac_to_wav(self):
        # copy files from source directories to destination directories
        dirs_list = []
        files_list = []
        for (root, dirs, files) in os.walk(self.btn_src_path_var.get(), topdown=True):
            dirs_list.append(root)
            # print("root =", root)
            # print(dirs)
            # # print(files)
            if files:
                for file in files:
                    if file.endswith(".flac"):
                        files_list.append(os.path.join(root, file))

        print("total files = ", len(files_list))

        total_number = len(files_list)

        # new destination directories list
        new_dirs_list = []
        for i in range(len(dirs_list)):
            new_dir = self.btn_dst_path_var.get() + "\\" + dirs_list[i][len(dirs_list[0]):]
            new_dirs_list.append(os.path.abspath(new_dir))
            # print(new_dirs_list[i])
        new_files_list = []
        for i in range(len(files_list)):
            new_file = self.btn_dst_path_var.get() + "\\" + files_list[i][len(dirs_list[0]):]
            new_file_wav = new_file.replace(".flac", ".wav")
            new_files_list.append(os.path.abspath(new_file_wav))

        # make destination directories
        for i in range(1, len(new_dirs_list)):
            print(new_dirs_list[i])
            try:
                os.mkdir(new_dirs_list[i])
            except FileExistsError:
                print(new_dirs_list[i], " exists.")

        for i in range(len(files_list)):
            if self.tool_started.get() == STOPPED:
                break
            flac2wav(files_list[i], new_files_list[i])
            print(files_list[i])
            print(new_files_list[i])
            self.ent_curr_file_var.set(os.path.basename(new_files_list[i]))
            self.update_prog_bar(int((i+1) / total_number * 100))
            # shutil.copy(files_list[i], new_files_list[i])

    def thread_mp3_to_wav(self):
        # conv_thread = threading.Thread(target=self.flac_to_wav, )
        # conv_thread.start()
        self.mp3_to_wav()
        self.tool_stop()
        print("flac to wav thread end.")
        messagebox.showwarning("Information", "File conversion from mp3 to wav finished.")

    def mp3_to_wav(self):
        # copy files from source directories to destination directories
        dirs_list = []
        files_list = []
        for (root, dirs, files) in os.walk(self.btn_src_path_var.get(), topdown=True):
            dirs_list.append(root)
            # print("root =", root)
            # print(dirs)
            # # print(files)
            if files:
                for file in files:
                    if file.endswith(".mp3"):
                        files_list.append(os.path.join(root, file))

        print("total files = ", len(files_list))

        total_number = len(files_list)

        # new destination directories list
        new_dirs_list = []
        for i in range(len(dirs_list)):
            new_dir = self.btn_dst_path_var.get() + "\\" + dirs_list[i][len(dirs_list[0]):]
            new_dirs_list.append(os.path.abspath(new_dir))
            # print(new_dirs_list[i])
        new_files_list = []
        for i in range(len(files_list)):
            new_file = self.btn_dst_path_var.get() + "\\" + files_list[i][len(dirs_list[0]):]
            new_file_wav = new_file.replace(".mp3", ".wav")
            new_files_list.append(os.path.abspath(new_file_wav))

        # make destination directories
        for i in range(1, len(new_dirs_list)):
            print(new_dirs_list[i])
            try:
                os.mkdir(new_dirs_list[i])
            except FileExistsError:
                print(new_dirs_list[i], " exists.")

        for i in range(len(files_list)):
            if self.tool_started.get() == STOPPED:
                break
            mp3towav(files_list[i], new_files_list[i])
            print(files_list[i])
            print(new_files_list[i])
            self.ent_curr_file_var.set(os.path.basename(new_files_list[i]))
            self.update_prog_bar((int(i+1) / total_number * 100))


if __name__ == '__main__':
    root = tk.Tk()
    asr_tool = Tool_GUI(root)

    root.mainloop()
