import json
import nidaqmx
from nidaqmx.constants import AcquisitionType
from datetime import datetime
from tkinter import Tk, Label, Button, Frame, Scale, HORIZONTAL
from tkinter import messagebox
import threading
import os

class DAQmxGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NI DAQmx Dual Channel Acquisition")
        self.root.geometry("400x300")
        
        self.is_running = False
        self.data = {"channel_0": [], "channel_1": [], "timestamp": datetime.now().isoformat()}
        
        # GUI Elements
        Label(root, text="DAQmx Acquisition", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Sample rate control
        Frame(root).pack()
        Label(root, text="Sample Rate (Hz):").pack()
        self.sample_rate = Scale(root, from_=100, to=100000, orient=HORIZONTAL)
        self.sample_rate.set(10000)
        self.sample_rate.pack(fill="x", padx=20)
        
        # Samples per channel
        Label(root, text="Samples per Channel:").pack()
        self.samples = Scale(root, from_=10, to=10000, orient=HORIZONTAL)
        self.samples.set(1000)
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
                task.ai_channels.add_ai_voltage_chan("Dev1/ai0")
                task.ai_channels.add_ai_voltage_chan("Dev1/ai1")
                
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
                
                self.save_data()
                self.is_running = False
                self.status_label.config(text="Status: Complete", fg="green")
                messagebox.showinfo("Success", "Data acquired and saved!")
                
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
        filename = f"daqmx_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.data, f, indent=2)
        print(f"Data saved to {filename}")

if __name__ == "__main__":
    root = Tk()
    app = DAQmxGUI(root)
    root.mainloop()