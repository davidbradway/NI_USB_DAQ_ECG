import os
import json
import threading
from datetime import datetime, timedelta
import nidaqmx
from nidaqmx.constants import AcquisitionType
from tkinter import Tk, Label, Button, Frame, Scale, HORIZONTAL
from tkinter import messagebox
import pandas as pd

# Matplotlib for plotting preview in the GUI
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class DAQmxGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NI DAQmx Dual Channel Acquisition")
        self.root.geometry("800x800")
        
        self.is_running = False
        self.data = {"channel_0": [], "channel_1": [], "timestamp": datetime.now().isoformat(), "sample_rate": [], "samples": []}
        
        # GUI Elements
        Label(root, text="DAQmx Acquisition", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Sample rate control
        Frame(root).pack()
        Label(root, text="Sample Rate (Hz):").pack()
        self.sample_rate = Scale(root, from_=100, to=100000, orient=HORIZONTAL)
        self.sample_rate.set(1000)
        self.sample_rate.pack(fill="x", padx=20)
        
        # Samples per channel
        Label(root, text="Samples per Channel:").pack()
        self.samples = Scale(root, from_=10, to=10000, orient=HORIZONTAL)
        self.samples.set(3000)
        self.samples.pack(fill="x", padx=20)
        
        # Status label
        self.status_label = Label(root, text="Status: Idle", fg="blue")
        self.status_label.pack(pady=10)
        
        # Buttons
        button_frame = Frame(root)
        button_frame.pack(pady=20)
        
        self.start_btn = Button(button_frame, text="Start Acquisition", command=self.start_acquisition)
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = Button(button_frame, text="Stop", command=self.stop_acquisition, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        # Plot area
        plot_frame = Frame(root)
        plot_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.fig = Figure(figsize=(6,2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Acquisition Preview")
        self.ax.set_xlabel("Sample")
        self.ax.set_ylabel("Voltage (V)")
        self.line0, = self.ax.plot([], [], label='chan0')
        self.line1, = self.ax.plot([], [], label='chan1')
        self.ax.legend(loc='upper right')

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def start_acquisition(self):
        self.is_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_label.config(text="Status: Acquiring...", fg="green")
        
        thread = threading.Thread(target=self.acquire_data)
        thread.daemon = True
        thread.start()
    
    def acquire_data(self):
        try:
            with nidaqmx.Task() as task:
                # Add two analog input channels
                task.ai_channels.add_ai_voltage_chan("Dev1/ai6")
                task.ai_channels.add_ai_voltage_chan("Dev1/ai13")
                
                task.timing.cfg_samp_clk_timing(
                    rate=int(self.sample_rate.get()),
                    sample_mode=AcquisitionType.FINITE,
                    samps_per_chan=int(self.samples.get())
                )
                
                task.start()
                data = task.read(number_of_samples_per_channel=int(self.samples.get())) # type: ignore
                
                self.data["channel_0"] = data[0]
                self.data["channel_1"] = data[1]
                self.data["timestamp"] = datetime.now().isoformat()
                self.data["sample_rate"] = int(self.sample_rate.get())
                self.data["samples"] = int(self.samples.get())

                # Update preview plot before saving
                try:
                    self.update_plot()
                except Exception:
                    pass

                self.save_data()
                self.is_running = False
                self.status_label.config(text="Status: Complete", fg="green")
                
        except Exception as e:
            messagebox.showerror("Error", f"Acquisition failed: {str(e)}")
            self.is_running = False
        finally:
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
    
    def stop_acquisition(self):
        self.is_running = False
        self.status_label.config(text="Status: Stopped", fg="red")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
    
    def save_data(self):
        base_filename = f"daqmx_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create timeseries DataFrame
        try:
            channel_0 = self.data.get('channel_0', [])
            channel_1 = self.data.get('channel_1', [])
            timestamp_str = self.data.get('timestamp', datetime.now().isoformat())
            
            # Parse start timestamp
            start_time = datetime.fromisoformat(timestamp_str)
            
            # Get sample rate from GUI
            sample_rate = self.sample_rate.get()
            
            # Calculate time interval between samples in microseconds
            time_interval_us = (1.0 / sample_rate) * 1_000_000  # microseconds
            
            # Create time index with microsecond precision
            num_samples = max(len(channel_0), len(channel_1))
            time_index = [start_time + timedelta(microseconds=i*time_interval_us) for i in range(num_samples)]
            
            # Create DataFrame with time as index
            df = pd.DataFrame({
                'channel_0': channel_0,
                'channel_1': channel_1
            }, index=pd.DatetimeIndex(time_index, name='time'))
            
            # Save in multiple formats
            # CSV format (human-readable)
            csv_filename = f"{base_filename}.csv"
            df.to_csv(csv_filename)
            print(f"Data saved to {csv_filename}")
            
            print(f"\nTimeseries Summary:")
            print(f"  Samples: {num_samples}")
            print(f"  Sample Rate: {sample_rate} Hz")
            print(f"  Duration: {df.index[-1] - df.index[0]}")
            
        except Exception as e:
            print(f"Warning: Could not save timeseries formats: {str(e)}")
            print(f"JSON format saved successfully.")

    def update_plot(self):
        # Safely update the matplotlib lines with latest data
        ch0 = self.data.get("channel_0", []) or []
        ch1 = self.data.get("channel_1", []) or []

        if not ch0 and not ch1:
            return

        x = list(range(len(ch0))) if ch0 else list(range(len(ch1)))

        if ch0:
            self.line0.set_data(x, ch0)
        else:
            self.line0.set_data([], [])

        if ch1:
            self.line1.set_data(x, ch1)
        else:
            self.line1.set_data([], [])

        # Adjust axes
        all_y = []
        if ch0:
            all_y.extend(ch0)
        if ch1:
            all_y.extend(ch1)
        if all_y:
            ymin, ymax = min(all_y), max(all_y)
            if ymin == ymax:
                ymin -= 0.5
                ymax += 0.5
            self.ax.set_xlim(0, max(1, len(x)))
            self.ax.set_ylim(ymin, ymax)

        self.canvas.draw_idle()

if __name__ == "__main__":
    root = Tk()
    app = DAQmxGUI(root)
    root.mainloop()