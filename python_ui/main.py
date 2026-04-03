import tkinter as tk
from tkinter import ttk
from backend_manager import SubprocessManager
from scoring_engine import ScoringEngine
from ui_components import BenchmarkPanel

try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SCS Benchmark Suite")
        
        self.state('zoomed') 
        
        style = ttk.Style()
        style.theme_use('clam')
        
        self.bg_color = "#f4f4f4"
        self.card_bg = "#ffffff"
        self.configure(bg=self.bg_color)
        
        style.configure("TFrame", background=self.bg_color)
        style.configure("Card.TFrame", background=self.card_bg, relief="flat", borderwidth=1)
        
        style.configure("TLabel", background=self.bg_color, font=("Segoe UI", 12))
        style.configure("Card.TLabel", background=self.card_bg, font=("Segoe UI", 14, "bold"))
        style.configure("Header.TLabel", font=("Segoe UI", 32, "bold"), foreground="#333")
        style.configure("Score.TLabel", font=("Segoe UI", 64, "bold"), foreground="#555")
        style.configure("SubScore.TLabel", font=("Segoe UI", 14), foreground="#666")
        style.configure("Component.TLabel", font=("Segoe UI", 12, "bold"), foreground="#0066cc")

        self.manager = SubprocessManager()
        self.scoring = ScoringEngine()
        
        self.panels = {}

        self._build_header()
        self._build_scroll_area()
        self._build_panels()

        self.after(500, self.load_sysinfo)

    def _build_header(self):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", pady=20)
        
        ttk.Label(header_frame, text="System Score", style="Header.TLabel").pack()
        self.lbl_score = ttk.Label(header_frame, text="---", style="Score.TLabel")
        self.lbl_score.pack()
        self.lbl_comparison = ttk.Label(header_frame, text="Run tests to calculate score", style="SubScore.TLabel")
        self.lbl_comparison.pack(pady=(5, 0))
        
        self.btn_run_all = ttk.Button(header_frame, text="RUN FULL SUITE", command=self.run_full_suite)
        self.btn_run_all.pack(pady=10)
        
        scores_row = ttk.Frame(header_frame, style="TFrame")
        scores_row.pack(pady=(20, 0))
        
        self.lbl_cpu_score = ttk.Label(scores_row, text="CPU: ---", style="Component.TLabel")
        self.lbl_cpu_score.pack(side="left", padx=25)
        
        self.lbl_ram_score = ttk.Label(scores_row, text="RAM: ---", style="Component.TLabel")
        self.lbl_ram_score.pack(side="left", padx=25)
        
        self.lbl_storage_score = ttk.Label(scores_row, text="Storage: ---", style="Component.TLabel")
        self.lbl_storage_score.pack(side="left", padx=25)
        
        self.lbl_gpu_score = ttk.Label(scores_row, text="GPU: ---", style="Component.TLabel")
        self.lbl_gpu_score.pack(side="left", padx=25)

    def _build_scroll_area(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(container, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        
        self.scroll_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="n")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.scroll_frame.bind("<Configure>", lambda e: self._on_frame_configure(canvas))
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _configure_canvas(event):
            canvas.itemconfig(canvas.find_all()[0], width=event.width)
        canvas.bind("<Configure>", _configure_canvas)

    def _on_frame_configure(self, canvas):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _build_panels(self):
        self.card_container = ttk.Frame(self.scroll_frame)
        self.card_container.pack(pady=10, fill="y")
        
        CARD_WIDTH = 1200

        sys_wrapper = ttk.Frame(self.card_container, width=CARD_WIDTH)
        sys_wrapper.pack(pady=10)
        
        info_card = ttk.Frame(sys_wrapper, style="Card.TFrame", padding=20)
        info_card.pack(fill="both", expand=True)
        
        ttk.Label(info_card, text="System Hardware", style="Card.TLabel").pack(anchor="w", pady=(0, 15))
        
        text_frame = ttk.Frame(info_card, style="Card.TFrame")
        text_frame.pack(fill="x", expand=True)
        
        self.txt_sysinfo = tk.Text(text_frame, height=1, width=90, borderwidth=0, font=("Consolas", 11), 
                                   bg="#f9f9f9", padx=15, pady=10)
        self.txt_sysinfo.pack(side="left", fill="both", expand=True)
        self.txt_sysinfo.insert("1.0", "Loading system info...")
        self.txt_sysinfo.config(state="disabled")

        tests = [
            ("CPU Processing", "cpu"), 
            ("Memory Subsystem", "ram"), 
            ("Storage Drives", "storage"), 
            ("Graphics Compute", "gpu")
        ]
        
        for title, tid in tests:
            wrapper = ttk.Frame(self.card_container, width=CARD_WIDTH)
            wrapper.pack(pady=15)
            
            p = BenchmarkPanel(wrapper, title, tid, self.manager, self.scoring, self.update_total_score)
            p.pack(fill="x", expand=True)
            
            self.panels[tid] = p

    def load_sysinfo(self):
        data = self.manager.execute_backend("sysinfo")
        self.txt_sysinfo.config(state="normal")
        self.txt_sysinfo.delete("1.0", tk.END)
        
        if "error" in data:
            self.txt_sysinfo.insert("1.0", f"Error: {data['error']}")
        else:
            info = data.get("sysinfo", {})
            output = ""

            cpu = info.get("cpu", {})
            if cpu:
                output += "--- Processor (CPU) ---\n"
                output += f"{'Name':<25}: {cpu.get('Name', 'N/A').strip()}\n"
                output += f"{'Cores / Threads':<25}: {cpu.get('NumberOfCores', '?')} / {cpu.get('NumberOfLogicalProcessors', '?')}\n"
                output += f"{'Max Clock Speed':<25}: {cpu.get('MaxClockSpeed', 0)} MHz\n"
                output += f"{'L3 Cache':<25}: {cpu.get('L3CacheSize', 0)} KB\n\n"

            gpus = info.get("gpu", [])
            if gpus:
                output += "--- Graphics (GPU) ---\n"
                for i, gpu in enumerate(gpus, 1):
                    name = gpu.get("Name", "N/A").strip()
                    try:
                        vram_bytes = int(gpu.get("AdapterRAM", 0))
                        if vram_bytes < 0: vram_bytes += 2**32
                        vram_gb = vram_bytes / (1024**3)
                        vram_str = f"{vram_gb:.1f} GB"
                    except (ValueError, TypeError):
                        vram_str = "N/A"
                    driver = gpu.get('DriverVersion', 'N/A')
                    output += f"GPU {i}:\n"
                    output += f"{'  Name':<25}: {name}\n"
                    output += f"{'  VRAM':<25}: {vram_str}\n"
                    output += f"{'  Driver Version':<25}: {driver}\n"
                output += "\n"

            ram = info.get("ram", {})
            if ram:
                output += "--- Memory (RAM) ---\n"
                output += f"{'Total Installed':<25}: {ram.get('total_size_gb', '?')} GB\n\n"
                for i, stick in enumerate(ram.get("sticks", []), 1):
                    manufacturer = stick.get('Manufacturer', 'N/A').strip()
                    part_num = stick.get('PartNumber', 'N/A').strip()
                    capacity = stick.get('capacity_gb', '?')
                    speed = stick.get('Speed', '?')
                    output += f"Module {i}:\n"
                    output += f"{'  Manufacturer':<25}: {manufacturer}\n"
                    output += f"{'  Capacity':<25}: {capacity} GB\n"
                    output += f"{'  Speed':<25}: {speed} MHz\n"
                    output += f"{'  Part Number':<25}: {part_num}\n"
                output += "\n"

            storage = info.get("storage", [])
            if storage:
                output += "--- Storage (Drives) ---\n"
                for i, drive in enumerate(storage, 1):
                    model = drive.get('Model', 'N/A').strip()
                    capacity = drive.get('capacity_gb', '?')
                    output += f"Drive {i}:\n"
                    output += f"{'  Model':<25}: {model}\n"
                    output += f"{'  Capacity':<25}: {capacity} GB\n"
                output += "\n"

            self.txt_sysinfo.insert("1.0", output.strip())

        try:
            num_lines = int(self.txt_sysinfo.index('end-1c').split('.')[0])
        except:
            num_lines = 10
            
        self.txt_sysinfo.config(height=num_lines + 1)
        self.txt_sysinfo.config(state="disabled")

    def run_full_suite(self):
    
        self.btn_run_all.config(state="disabled")
        
        self.lbl_comparison.config(text="Running Full Suite... Please do not use the computer.", foreground="#cc3300")
        
        for p in self.panels.values():
            p.btn_run.config(state="disabled")

        def run_cpu():
            self.panels['cpu'].on_complete = run_ram
            self.panels['cpu'].start_test()
            
        def run_ram():
            self.panels['ram'].on_complete = run_storage
            self.panels['ram'].start_test()
            
        def run_storage():
            self.panels['storage'].on_complete = run_gpu
            self.panels['storage'].start_test()
            
        def run_gpu():
            self.panels['gpu'].on_complete = finish_suite
            self.panels['gpu'].start_test()
            
        def finish_suite():
            for tid, panel in self.panels.items():
                panel.on_complete = self.update_total_score
                panel.btn_run.config(state="normal")
            
            self.btn_run_all.config(state="normal")
            self.update_total_score()

        run_cpu()

    def update_total_score(self):
        total_score, component_scores = self.scoring.calculate_total_score()
        
        self.lbl_cpu_score.config(text=f"CPU: {component_scores.get('cpu', 0)}")
        self.lbl_ram_score.config(text=f"RAM: {component_scores.get('ram', 0)}")
        self.lbl_storage_score.config(text=f"Storage: {component_scores.get('storage', 0)}")
        self.lbl_gpu_score.config(text=f"GPU: {component_scores.get('gpu', 0)}")
        
        if total_score > 0:
            self.lbl_score.config(text=f"{total_score}")
            ref = 1000
            diff = ((total_score - ref) / ref) * 100
            if diff >= 0:
                self.lbl_comparison.config(text=f"Your system is {diff:.1f}% faster than Baseline.", 
                                          foreground="#009933")
            else:
                self.lbl_comparison.config(text=f"Your system is {abs(diff):.1f}% slower than Baseline.", 
                                          foreground="#cc3300")

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()