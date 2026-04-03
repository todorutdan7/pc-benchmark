import tkinter as tk
from tkinter import ttk
import threading
import time
from config import TEST_DESCRIPTIONS, BENCHMARK_ITERATIONS

def _format_detailed_results(data_dict, test_id):

    output = ""
    if 'device_name' in data_dict:
        output += f"{'Device Name':<22}: {data_dict['device_name']}\n\n"

    preferred_order = []
    
    if test_id == 'cpu':
        preferred_order = [
            "pi_single_thread", "pi_multi_thread",
            "matrix_single_thread", "matrix_multi_thread",
            "integer_hashing_single", "float_math_single"
        ]
    elif test_id == 'storage':
        preferred_order = [
            "sequential_read", "sequential_write", "random_read_iops", "random_write_iops"
        ]
    elif test_id == 'ram':
        preferred_order = ["l1_cache", "l2_cache", "l3_cache", "main_memory", "ram_latency"]
    elif test_id == 'gpu':
        preferred_order = ["mandelbrot", "fps_test"]
    
    keys_to_process = [k for k in preferred_order if k in data_dict]
    remaining = [k for k in data_dict.keys() if k not in preferred_order and isinstance(data_dict[k], dict)]
    keys_to_process.extend(remaining)

    for test_name in keys_to_process:
        metrics = data_dict.get(test_name)
        if not isinstance(metrics, dict): continue

        title = test_name.replace('_', ' ').title()
        if "label" in metrics: title = metrics["label"]

        output += f"--- {title} ---\n"

        metric_order = [
            "time_seconds", "duration_seconds", "iterations", "operations",
            "read_bandwidth_gbs", "write_bandwidth_gbs", "bandwidth_gbs", 
            "avg_latency_ns", "matrix_size", "threads", "block_size_used",
            "ops_per_sec", "ops", "gflops", "iops", "fps", "total_frames", "description"
        ]
        
        sorted_metrics = []
        for m in metric_order:
            if m in metrics: sorted_metrics.append(m)
        for m in metrics:
            if m not in sorted_metrics: sorted_metrics.append(m)

        for key in sorted_metrics:
            value = metrics[key]
            if key == "label": continue 

            label = key.replace('_', ' ').capitalize()
            formatted_value = str(value)
            unit = ""
            
            try:
                if key in ['time_seconds', 'duration_seconds']:
                    label = "Avg Time"
                    formatted_value = f"{float(value):.4f}"
                    unit = "s"
                elif key == 'iterations':
                    label = "Iterations"
                    formatted_value = f"{int(value):,}"
                elif key == 'operations':
                    label = "Operations"
                    formatted_value = f"{int(value):,}"
                elif key == 'read_bandwidth_gbs':
                    label = "Avg Read BW"
                    formatted_value = f"{value:,.2f}"
                    unit = "GB/s"
                elif key == 'write_bandwidth_gbs':
                    label = "Avg Write BW"
                    formatted_value = f"{value:,.2f}"
                    unit = "GB/s"
                elif key == 'bandwidth_gbs':
                    label = "Avg Bandwidth"
                    formatted_value = f"{value:,.2f}"
                    unit = "GB/s"
                elif key == 'avg_latency_ns':
                    label = "Avg Latency"
                    formatted_value = f"{value:,.2f}"
                    unit = "ns"
                elif key == 'threads':
                    label = "Threads"
                    formatted_value = str(value)
                elif key == 'matrix_size':
                    label = "Matrix Size"
                    formatted_value = f"{value}x{value}"
                elif key == 'block_size_used':
                    label = "Block Size"
                    formatted_value = f"{int(value):,}"
                    unit = "bytes"
                elif key == 'iops':
                    label = "Avg IOPS"
                    formatted_value = f"{int(float(value)):,}" 
                elif key == 'gflops':
                    label = "Avg Perf"
                    formatted_value = f"{value:,.2f}"
                    unit = "GFLOPS"
                elif key == 'fps':
                    label = "Avg FPS"
                    formatted_value = f"{value:,.2f}"
                elif key == 'total_frames':
                    label = "Total Frames"
                    formatted_value = f"{int(value):,}"
            except: pass

            if key == 'description': output += f"{label:<15}: {formatted_value}\n"
            else: output += f"{label:<15}: {formatted_value} {unit}\n"
        output += "\n"
    return output.strip()


class ScoreChart(tk.Canvas):
    def __init__(self, parent, width=300, height=150, line_color="#0066cc", y_label="Score", is_integer=False):
        super().__init__(parent, width=width, height=height, bg='#f9f9f9', highlightthickness=1, highlightbackground='#ccc')
        self.width = width
        self.height = height
        self.line_color = line_color
        self.y_label = y_label
        self.is_integer = is_integer
        
        self.pad_left = 60 
        self.pad_right = 10
        self.pad_y = 25
        self.pad_bottom = 30 
        
        self.scores = []
        
    def update_scores(self, scores):
        self.scores = scores
        self.draw_chart()
        
    def draw_chart(self):
        self.delete("all")
        
        self.create_text(15, self.height // 2, text=self.y_label, angle=90, 
                         font=("Segoe UI", 8, "bold"), fill="#555")
        self.create_text(self.width // 2, self.height - 10, text="Iteration", 
                         font=("Segoe UI", 8), fill="#555")

        if not self.scores:
            self.create_text(self.width // 2, self.height // 2, 
                           text="Waiting...", fill="#999", font=("Segoe UI", 9))
            return
            
        min_val = min(self.scores)
        max_val = max(self.scores)
        
        if min_val == max_val: buffer = max_val * 0.1 if max_val > 0 else 1.0
        else: buffer = (max_val - min_val) * 0.1
        
        y_max = max_val + buffer
        y_min = max(0, min_val - buffer)
        y_range = y_max - y_min
        
        plot_w = self.width - (self.pad_left + self.pad_right)
        plot_h = self.height - (self.pad_y + self.pad_bottom)
        
        self.create_line(self.pad_left, self.pad_y + 10, self.pad_left, self.height - self.pad_bottom, fill="#ddd") 
        self.create_line(self.pad_left, self.height - self.pad_bottom, self.width - self.pad_right, self.height - self.pad_bottom, fill="#ddd") 
        
        if self.is_integer:
            lbl_max = f"{int(y_max)}"
            lbl_min = f"{int(y_min)}"
        else:
            lbl_max = f"{y_max:.2f}"
            lbl_min = f"{y_min:.2f}"

        self.create_text(self.pad_left - 5, self.pad_y + 10, 
                        text=lbl_max, anchor="e", fill="#555", font=("Segoe UI", 7))
        self.create_text(self.pad_left - 5, self.height - self.pad_bottom, 
                        text=lbl_min, anchor="e", fill="#555", font=("Segoe UI", 7))

        count = len(self.scores)
        if count == 0: return

        iter_width = plot_w / count
        bar_width = iter_width * 0.6
        spacing = (iter_width - bar_width) / 2

        for i, score in enumerate(self.scores):
            if y_range > 0:
                rel_y = (score - y_min) / y_range
            else:
                rel_y = 0.5
            
            bar_height = rel_y * plot_h
            
            x0 = self.pad_left + (i * iter_width) + spacing
            y0 = (self.height - self.pad_bottom) - bar_height
            x1 = x0 + bar_width
            y1 = self.height - self.pad_bottom
            
            self.create_rectangle(x0, y0, x1, y1, fill=self.line_color, outline="")


class MultiBarChart(tk.Canvas):
    def __init__(self, parent, width=300, height=150, legend_labels=None, y_label="Value", colors=None):
        super().__init__(parent, width=width, height=height, bg='#f9f9f9', highlightthickness=1, highlightbackground='#ccc')
        self.width = width
        self.height = height
        self.y_label = y_label
        
        self.pad_left = 60 
        self.pad_right = 10
        self.pad_y = 25 
        self.pad_bottom = 30 
        
        self.data_lists = [] 
        self.labels = legend_labels if legend_labels else ["Line 1", "Line 2"]
        self.colors = colors if colors else ["#cc3300", "#009933", "#0066cc"]
        
    def update_data(self, *lists):
        self.data_lists = list(lists)
        self.draw_chart()
        
    def draw_chart(self):
        self.delete("all")
        
        self.create_text(15, self.height // 2, text=self.y_label, angle=90, 
                         font=("Segoe UI", 8, "bold"), fill="#555")
        self.create_text(self.width // 2, self.height - 10, text="Iteration", 
                         font=("Segoe UI", 8), fill="#555")

        for i, label in enumerate(self.labels):
            if i >= len(self.colors): break
            offset_x = self.width - 10 - (len(self.labels) - i) * 60
            self.create_oval(offset_x, 8, offset_x + 10, 18, fill=self.colors[i], outline="")
            self.create_text(offset_x + 15, 13, text=label, anchor="w", font=("Segoe UI", 8))

        if not self.data_lists or not any(self.data_lists):
            self.create_text(self.width // 2, self.height // 2, text="Waiting...", fill="#999")
            return
            
        all_vals = [val for sublist in self.data_lists for val in sublist]
        if not all_vals: return

        min_val = min(all_vals)
        max_val = max(all_vals)
        
        if min_val == max_val: buffer = max_val * 0.1 if max_val > 0 else 1.0
        else: buffer = (max_val - min_val) * 0.1
            
        y_max = max_val + buffer
        y_min = max(0, min_val - buffer)
        y_range = y_max - y_min
        
        plot_w = self.width - (self.pad_left + self.pad_right)
        plot_h = self.height - (self.pad_y + self.pad_bottom)

        self.create_line(self.pad_left, self.pad_y + 10, self.pad_left, self.height - self.pad_bottom, fill="#ddd")
        self.create_line(self.pad_left, self.height - self.pad_bottom, self.width - self.pad_right, self.height - self.pad_bottom, fill="#ddd")

        self.create_text(self.pad_left - 5, self.pad_y + 10, text=f"{y_max:.2f}", anchor="e", fill="#555", font=("Segoe UI", 7))
        self.create_text(self.pad_left - 5, self.height - self.pad_bottom, text=f"{y_min:.2f}", anchor="e", fill="#555", font=("Segoe UI", 7))
        
        num_groups = len(self.data_lists[0]) if self.data_lists else 0
        if num_groups == 0: return

        num_series = len(self.data_lists)
        
        group_width = plot_w / num_groups
        block_width = group_width * 0.8
        single_bar_width = block_width / num_series
        group_spacing = (group_width - block_width) / 2

        for i in range(num_groups): 
            group_x_start = self.pad_left + (i * group_width) + group_spacing
            
            for j, d_list in enumerate(self.data_lists):
                if j >= len(self.colors): break
                if i >= len(d_list): continue
                
                val = d_list[i]
                
                if y_range > 0:
                    rel_y = (val - y_min) / y_range
                else:
                    rel_y = 0.5
                
                bar_h = rel_y * plot_h
                
                x0 = group_x_start + (j * single_bar_width)
                y0 = (self.height - self.pad_bottom) - bar_h
                x1 = x0 + single_bar_width
                y1 = self.height - self.pad_bottom
                
                self.create_rectangle(x0, y0, x1, y1, fill=self.colors[j], outline="")


class BenchmarkPanel(ttk.Frame):
    def __init__(self, parent, title, test_id, manager, scoring_engine, on_complete):
        super().__init__(parent, style="Card.TFrame", padding=15)
        self.test_id = test_id
        self.manager = manager
        self.scoring_engine = scoring_engine
        self.on_complete = on_complete
        
        self.data_history = {} 
        self.pack_propagate(True)

        top_row = ttk.Frame(self, style="Card.TFrame")
        top_row.pack(fill="x", pady=(0, 5))
        
        lbl_title = ttk.Label(top_row, text=title, font=("Segoe UI", 12, "bold"), background="#ffffff")
        lbl_title.pack(side="left")
        
        self.lbl_score = ttk.Label(top_row, text="Score: ---", font=("Segoe UI", 11, "bold"), 
                                   foreground="#0066cc", background="#ffffff")
        self.lbl_score.pack(side="right", padx=(10, 0))
        
        self.btn_run = ttk.Button(top_row, text=f"Run Test ({BENCHMARK_ITERATIONS}x)", command=self.start_test)
        self.btn_run.pack(side="right")

        desc_text = TEST_DESCRIPTIONS.get(test_id, "Benchmark Test")
        lbl_desc = ttk.Label(self, text=desc_text, font=("Segoe UI", 11), foreground="#666", 
                           background="#ffffff", wraplength=1000)
        lbl_desc.pack(fill="x", pady=(0, 10))

        chart_row = ttk.Frame(self, style="Card.TFrame")
        chart_row.pack(fill="x", pady=(0, 10))
        
        self.tabs = ttk.Notebook(chart_row, width=520, height=250) 
        self.tabs.pack(side="left", padx=(0, 10))
        
        CHART_W = 500
        CHART_H = 220

        t_score = ttk.Frame(self.tabs, style="Card.TFrame")
        self.tabs.add(t_score, text="Score")
        self.chart_score = ScoreChart(t_score, width=CHART_W, height=CHART_H, y_label="Score", is_integer=True)
        self.chart_score.pack(pady=5)

        if self.test_id == 'cpu':
            t_pi = ttk.Frame(self.tabs, style="Card.TFrame")
            self.tabs.add(t_pi, text="Pi")
            self.chart_pi = MultiBarChart(t_pi, width=CHART_W, height=CHART_H, 
                                           legend_labels=["Single", "Multi"], y_label="Time (s)")
            self.chart_pi.pack(pady=5)
            
            t_mat = ttk.Frame(self.tabs, style="Card.TFrame")
            self.tabs.add(t_mat, text="Matrix")
            self.chart_mat = MultiBarChart(t_mat, width=CHART_W, height=CHART_H, 
                                            legend_labels=["Single", "Multi"], y_label="Time (s)")
            self.chart_mat.pack(pady=5)

            t_int = ttk.Frame(self.tabs, style="Card.TFrame")
            self.tabs.add(t_int, text="Int Hash")
            self.chart_int = ScoreChart(t_int, width=CHART_W, height=CHART_H, line_color="#cc3300", y_label="Time (s)")
            self.chart_int.pack(pady=5)

            t_flt = ttk.Frame(self.tabs, style="Card.TFrame")
            self.tabs.add(t_flt, text="Float")
            self.chart_flt = ScoreChart(t_flt, width=CHART_W, height=CHART_H, line_color="#009933", y_label="Time (s)")
            self.chart_flt.pack(pady=5)

        elif self.test_id == 'ram':
            t_cache = ttk.Frame(self.tabs, style="Card.TFrame")
            self.tabs.add(t_cache, text="Cache BW")
            self.chart_cache = MultiBarChart(t_cache, width=CHART_W, height=CHART_H, 
                                              legend_labels=["L1", "L2", "L3"], y_label="GB/s")
            self.chart_cache.pack(pady=5)

            t_ram = ttk.Frame(self.tabs, style="Card.TFrame")
            self.tabs.add(t_ram, text="RAM BW")
            self.chart_ram = ScoreChart(t_ram, width=CHART_W, height=CHART_H, line_color="#6600cc", y_label="GB/s")
            self.chart_ram.pack(pady=5)

            t_lat = ttk.Frame(self.tabs, style="Card.TFrame")
            self.tabs.add(t_lat, text="Latency")
            self.chart_lat = ScoreChart(t_lat, width=CHART_W, height=CHART_H, line_color="#cc0000", y_label="ns")
            self.chart_lat.pack(pady=5)

        elif self.test_id == 'storage':
            t_seq = ttk.Frame(self.tabs, style="Card.TFrame")
            self.tabs.add(t_seq, text="Sequential")
            self.chart_seq = MultiBarChart(t_seq, width=CHART_W, height=CHART_H,
                                            legend_labels=["Read", "Write"], y_label="IOPS")
            self.chart_seq.pack(pady=5)

            t_rnd = ttk.Frame(self.tabs, style="Card.TFrame")
            self.tabs.add(t_rnd, text="Random")
            self.chart_rnd = MultiBarChart(t_rnd, width=CHART_W, height=CHART_H,
                                            legend_labels=["Read", "Write"], y_label="IOPS")
            self.chart_rnd.pack(pady=5)

        elif self.test_id == 'gpu':
            t_gflops = ttk.Frame(self.tabs, style="Card.TFrame")
            self.tabs.add(t_gflops, text="GFLOPS")
            self.chart_gflops = ScoreChart(t_gflops, width=CHART_W, height=CHART_H, line_color="#009933", y_label="GFLOPS")
            self.chart_gflops.pack(pady=5)
            
            t_fps = ttk.Frame(self.tabs, style="Card.TFrame")
            self.tabs.add(t_fps, text="FPS")
            self.chart_fps = ScoreChart(t_fps, width=CHART_W, height=CHART_H, line_color="#cc3300", y_label="FPS", is_integer=True)
            self.chart_fps.pack(pady=5)
        
        progress_frame = ttk.Frame(chart_row, style="Card.TFrame")
        progress_frame.pack(side="left", fill="both", expand=True)
        
        self.lbl_progress = ttk.Label(progress_frame, text="Ready", font=("Segoe UI", 9), 
                                     background="#ffffff", foreground="#666")
        self.lbl_progress.pack(anchor="w", pady=(0, 5))
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate', maximum=BENCHMARK_ITERATIONS)
        self.progress.pack(fill="x", pady=5)

        results_frame = ttk.Frame(self, style="Card.TFrame")
        results_frame.pack(fill="both", expand=True, pady=(5, 0))

        v_scrollbar = ttk.Scrollbar(results_frame, orient="vertical")
        v_scrollbar.pack(side="right", fill="y")

        self.txt_result = tk.Text(results_frame, height=10, font=("Consolas", 11), 
                                 fg="#444", bg="#f9f9f9", 
                                 padx=10, pady=10, relief="solid", borderwidth=1,
                                 yscrollcommand=v_scrollbar.set)
        
        self.txt_result.pack(side="left", fill="both", expand=True)
        v_scrollbar.config(command=self.txt_result.yview)
        self.txt_result.insert("1.0", "Ready to benchmark.")
        self.txt_result.config(state="disabled") 

    def start_test(self):
        self.btn_run.config(state="disabled")
        self.progress['value'] = 0
        
        self.scoring_engine.clear_component_history(self.test_id)
        self.chart_score.update_scores([]) 
        
        self.data_history = {k: [] for k in [
            'pi_s', 'pi_m', 'mat_s', 'mat_m', 'int', 'flt', 
            'l1_r', 'l1_w', 'l2_r', 'l2_w', 'l3_r', 'l3_w', 
            'ram_r', 'ram_w', 'lat', 
            'seq_r', 'seq_w', 'rnd_r', 'rnd_w', 
            'gflops', 'gpu_time', 'fps', 'fps_time'
        ]}
        
        if self.test_id == 'cpu':
            self.chart_pi.update_data([], [])
            self.chart_mat.update_data([], [])
            self.chart_int.update_scores([])
            self.chart_flt.update_scores([])
        elif self.test_id == 'ram':
            self.chart_cache.update_data([], [], [])
            self.chart_ram.update_scores([])
            self.chart_lat.update_scores([])
        elif self.test_id == 'storage':
            self.chart_seq.update_data([], [])
            self.chart_rnd.update_data([], [])
        elif self.test_id == 'gpu':
            self.chart_gflops.update_scores([])
            self.chart_fps.update_scores([])

        self.txt_result.config(state="normal")
        self.txt_result.delete("1.0", tk.END)
        self.txt_result.insert("1.0", f"Running {BENCHMARK_ITERATIONS} iterations...\nPlease wait...")
        self.txt_result.config(state="disabled")
        
        t = threading.Thread(target=self._worker)
        t.daemon = True
        t.start()

    def _worker(self):
        kwargs = {}
        if self.test_id == "cpu":
            kwargs['pi_digits'] = 512000
            kwargs['matrix_size'] = 2048

        final_data = {}

        for i in range(BENCHMARK_ITERATIONS):
            self.after(0, self._update_progress, i + 1)
            
            if self.test_id == "gpu":
                time.sleep(0.5) 
                data_compute = self.manager.execute_backend("gpu", subtest="compute")
                if "error" in data_compute: final_data = data_compute; break
                
                time.sleep(0.2)
                data_fps = self.manager.execute_backend("gpu", subtest="fps")
                if "error" in data_fps: final_data = data_fps; break

                combined_gpu_data = {}
                if "gpu" in data_compute: combined_gpu_data.update(data_compute["gpu"])
                if "gpu" in data_fps: combined_gpu_data.update(data_fps["gpu"])
                
                final_data = {"gpu": combined_gpu_data}
                self.scoring_engine.update_result("gpu", final_data, iteration=i)
            else:
                final_data = self.manager.execute_backend(self.test_id, **kwargs)
                self.scoring_engine.update_result(self.test_id, final_data, iteration=i)

            comp_data = final_data.get(self.test_id, {})
            
            if self.test_id == 'cpu':
                self.data_history['pi_s'].append(comp_data.get('pi_single_thread', {}).get('time_seconds', 0))
                self.data_history['pi_m'].append(comp_data.get('pi_multi_thread', {}).get('time_seconds', 0))
                self.data_history['mat_s'].append(comp_data.get('matrix_single_thread', {}).get('time_seconds', 0))
                self.data_history['mat_m'].append(comp_data.get('matrix_multi_thread', {}).get('time_seconds', 0))
                self.data_history['int'].append(comp_data.get('integer_hashing_single', {}).get('time_seconds', 0))
                self.data_history['flt'].append(comp_data.get('float_math_single', {}).get('time_seconds', 0))
                
                self.after(0, lambda: self.chart_pi.update_data(self.data_history['pi_s'], self.data_history['pi_m']))
                self.after(0, lambda: self.chart_mat.update_data(self.data_history['mat_s'], self.data_history['mat_m']))
                self.after(0, lambda: self.chart_int.update_scores(self.data_history['int']))
                self.after(0, lambda: self.chart_flt.update_scores(self.data_history['flt']))

            elif self.test_id == 'ram':
                self.data_history['l1_r'].append(comp_data.get('l1_cache', {}).get('read_bandwidth_gbs', 0))
                self.data_history['l1_w'].append(comp_data.get('l1_cache', {}).get('write_bandwidth_gbs', 0))
                
                self.data_history['l2_r'].append(comp_data.get('l2_cache', {}).get('read_bandwidth_gbs', 0))
                self.data_history['l2_w'].append(comp_data.get('l2_cache', {}).get('write_bandwidth_gbs', 0))
                
                self.data_history['l3_r'].append(comp_data.get('l3_cache', {}).get('read_bandwidth_gbs', 0))
                self.data_history['l3_w'].append(comp_data.get('l3_cache', {}).get('write_bandwidth_gbs', 0))
                
                self.data_history['ram_r'].append(comp_data.get('main_memory', {}).get('read_bandwidth_gbs', 0))
                self.data_history['ram_w'].append(comp_data.get('main_memory', {}).get('write_bandwidth_gbs', 0))
                
                self.data_history['lat'].append(comp_data.get('ram_latency', {}).get('avg_latency_ns', 0))

                self.after(0, lambda: self.chart_cache.update_data(self.data_history['l1_r'], self.data_history['l2_r'], self.data_history['l3_r']))
                self.after(0, lambda: self.chart_ram.update_scores(self.data_history['ram_r']))
                self.after(0, lambda: self.chart_lat.update_scores(self.data_history['lat']))

            elif self.test_id == 'storage':
                self.data_history['seq_r'].append(comp_data.get('sequential_read', {}).get('iops', 0))
                self.data_history['seq_w'].append(comp_data.get('sequential_write', {}).get('iops', 0))
                self.data_history['rnd_r'].append(comp_data.get('random_read_iops', {}).get('iops', 0))
                self.data_history['rnd_w'].append(comp_data.get('random_write_iops', {}).get('iops', 0))

                self.after(0, lambda: self.chart_seq.update_data(self.data_history['seq_r'], self.data_history['seq_w']))
                self.after(0, lambda: self.chart_rnd.update_data(self.data_history['rnd_r'], self.data_history['rnd_w']))
                
            elif self.test_id == 'gpu':
                self.data_history['gflops'].append(comp_data.get('mandelbrot', {}).get('gflops', 0))
                self.data_history['gpu_time'].append(comp_data.get('mandelbrot', {}).get('time_seconds', 0))
                
                self.data_history['fps'].append(comp_data.get('fps_test', {}).get('fps', 0))
                
                self.after(0, lambda: self.chart_gflops.update_scores(self.data_history['gflops']))
                self.after(0, lambda: self.chart_fps.update_scores(self.data_history['fps']))

            scores = self.scoring_engine.get_iteration_scores(self.test_id)
            self.after(0, self.chart_score.update_scores, scores)
            
        self.after(0, self._finish, final_data)

    def _update_progress(self, iteration):
        self.progress['value'] = iteration
        self.lbl_progress.config(text=f"Iteration {iteration}/{BENCHMARK_ITERATIONS}")

    def _finish(self, last_data):
        self.btn_run.config(state="normal")
        self.lbl_progress.config(text="Complete")
        
        avg_score = self.scoring_engine.get_component_score(self.test_id)
        self.lbl_score.config(text=f"Score: {avg_score}")
        self.on_complete()

        def safe_avg(lst): return sum(lst) / len(lst) if lst else 0

        target = last_data.get(self.test_id, last_data)
        
        if self.test_id == 'cpu':
            if 'pi_single_thread' in target: target['pi_single_thread']['time_seconds'] = safe_avg(self.data_history['pi_s'])
            if 'pi_multi_thread' in target: target['pi_multi_thread']['time_seconds'] = safe_avg(self.data_history['pi_m'])
            if 'matrix_single_thread' in target: target['matrix_single_thread']['time_seconds'] = safe_avg(self.data_history['mat_s'])
            if 'matrix_multi_thread' in target: target['matrix_multi_thread']['time_seconds'] = safe_avg(self.data_history['mat_m'])
            if 'integer_hashing_single' in target: target['integer_hashing_single']['time_seconds'] = safe_avg(self.data_history['int'])
            if 'float_math_single' in target: target['float_math_single']['time_seconds'] = safe_avg(self.data_history['flt'])

        elif self.test_id == 'ram':
            if 'l1_cache' in target: 
                target['l1_cache']['read_bandwidth_gbs'] = safe_avg(self.data_history['l1_r'])
                target['l1_cache']['write_bandwidth_gbs'] = safe_avg(self.data_history['l1_w'])
            if 'l2_cache' in target: 
                target['l2_cache']['read_bandwidth_gbs'] = safe_avg(self.data_history['l2_r'])
                target['l2_cache']['write_bandwidth_gbs'] = safe_avg(self.data_history['l2_w'])
            if 'l3_cache' in target: 
                target['l3_cache']['read_bandwidth_gbs'] = safe_avg(self.data_history['l3_r'])
                target['l3_cache']['write_bandwidth_gbs'] = safe_avg(self.data_history['l3_w'])
            if 'main_memory' in target: 
                target['main_memory']['read_bandwidth_gbs'] = safe_avg(self.data_history['ram_r'])
                target['main_memory']['write_bandwidth_gbs'] = safe_avg(self.data_history['ram_w'])
            
            if 'ram_latency' in target: target['ram_latency']['avg_latency_ns'] = safe_avg(self.data_history['lat'])

        elif self.test_id == 'storage':
            if 'sequential_read' in target: target['sequential_read']['iops'] = safe_avg(self.data_history['seq_r'])
            if 'sequential_write' in target: target['sequential_write']['iops'] = safe_avg(self.data_history['seq_w'])
            if 'random_read_iops' in target: target['random_read_iops']['iops'] = safe_avg(self.data_history['rnd_r'])
            if 'random_write_iops' in target: target['random_write_iops']['iops'] = safe_avg(self.data_history['rnd_w'])
        
        elif self.test_id == 'gpu':
            if 'mandelbrot' in target: 
                target['mandelbrot']['gflops'] = safe_avg(self.data_history['gflops'])
                target['mandelbrot']['time_seconds'] = safe_avg(self.data_history['gpu_time'])
            if 'fps_test' in target: 
                target['fps_test']['fps'] = safe_avg(self.data_history['fps'])
        
        summary = ""
        color = "#003366"
        
        if "error" in last_data:
            summary = f"Error: {last_data['error']}"
            color = "red"
        else:
            summary = _format_detailed_results(target, self.test_id)
            header = f"=== AVERAGE SCORE: {avg_score} ===\n(Calculated over {BENCHMARK_ITERATIONS} runs)\n\n"
            summary = header + summary

        self.txt_result.config(state="normal")
        self.txt_result.delete("1.0", tk.END)
        self.txt_result.insert("1.0", summary)
        self.txt_result.config(fg=color)
        self.txt_result.config(height=12) 
        self.txt_result.config(state="disabled")