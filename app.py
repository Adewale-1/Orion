import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, Toplevel, Label, Button

from tkinter.font import Font
from PIL import Image, ImageTk
import logging
import time
import random
from multiprocessing import Pool, cpu_count
import subprocess
import time
import re
import shutil
import threading
from skopt import gp_minimize
from skopt.space import Integer, Categorical
from skopt.utils import use_named_args
import numpy as np
from datetime import datetime

# Set up logging
logging.basicConfig(
    filename="app.log",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class RoundedButton(tk.Canvas):
    def __init__(
        self, parent, text, command=None, radius=20, padding=(10, 10), *args, **kwargs
    ):
        tk.Canvas.__init__(self, parent, *args, **kwargs)
        self.radius = radius
        self.command = command
        self.padding = padding
        self.text = text
        self.bg_color = parent.cget("bg")

        self.button_bg = "#000000"  # Black button background
        self.button_fg = "#FFFFFF"  # White button text
        self.highlight_bg = "#333333"  # Dark gray for button highlight

        # Calculate the required width and height based on text length and padding
        font = Font(size=14)
        text_width = font.measure(text)
        self.width = text_width + 2 * (radius + padding[0])
        self.height = 2 * (radius + padding[1] + font.metrics("ascent"))
        self.config(
            width=self.width,
            height=self.height,
            bg=parent.cget("bg"),
            highlightthickness=0,
        )

        # Draw rounded rectangle
        self.round_rect = self.create_rounded_rect(
            0, 0, self.width, self.height, radius=self.radius
        )
        self.text_item = self.create_text(
            self.width / 2, self.height / 2, text=text, font=font, fill="#FFFFFF"
        )

        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def create_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = [
            x1 + radius,
            y1,
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]

        return self.create_polygon(
            points, smooth=True, **kwargs, outline=self.button_bg, fill=self.button_bg
        )

    def _on_press(self, event):
        self.itemconfig(self.round_rect, fill=self.highlight_bg)

    def _on_release(self, event):
        self.itemconfig(self.round_rect, fill=self.button_bg)
        if self.command:
            self.command()


class App:
    def __init__(self):
        self.ROOT = tk.Tk()
        self.outputFinalFile = ""
        self.initial_energy = None

        self.output_directory = None
        self.input_tail = None
        self.args_file = None
        self.seq_filename = None
        self.results_heatmap_ortho = None
        self.results_heatmap_path = None
        self.results_plots = None
        self.autobreak_log = None
        self.json_legacy_output = None
        self.results_report = None
        self.results_excel_file = None

        # Define color scheme
        self.bg_color = "#FFFFFF"  # White background
        self.fg_color = "#000000"  # Black text
        self.button_bg = "#000000"  # Black button background
        self.button_fg = "#FFFFFF"  # White button text
        self.highlight_bg = "#333333"  # Dark gray for button highlight

        self.picture = resource_path("layout.png")
        self.root.title("Origami Design Uploader")

        # Try to load and set the logo
        try:
            # Check if the file exists
            if not os.path.isfile(self.picture):
                logging.error(f"The file '{self.picture}' does not exist.")
                raise FileNotFoundError

            # Load and resize the logo
            original_logo = Image.open(resource_path(self.picture))
            # original_logo = Image.open(layout_path)
            resized_logo = original_logo.resize(
                (60, 60), Image.LANCZOS
            )  # Increased size for visibility
            self.logo = ImageTk.PhotoImage(resized_logo)

            # Set the window icon
            self.root.iconphoto(False, self.logo)

        except Exception as e:
            logging.error(f"Error loading the logo: {str(e)}")

        self.root.geometry("900x1000")
        self.root.configure(bg=self.bg_color)

        self.uploaded_file = None
        self.download_location = None

        # Set up global exception handler
        sys.excepthook = self.handle_exception

        # Show the intro screen instead of creating widgets immediately
        self.show_intro_screen()

    def calculate_initial_energy(self):
        initial_params = {
            "nsol": 3,
            "npermute": 0,
            "minlength": 20,
            "maxlength": 60,
            "dontbreak": 21,
            "seed": 0,
            "rule_x": 3,
        }
        energy, _, _ = self.run_autobreak(initial_params, is_initial_run=True)
        return energy

    def select_download_location(self):
        try:
            download_path = filedialog.askdirectory()
            if download_path:
                self.download_location = download_path
                self.download_label.config(
                    text=f"Download Location: {os.path.basename(download_path)}"
                )
                self.check_run_button_state()
        except Exception as e:
            logging.error(f"Failed to select download location: {str(e)}")

    def check_run_button_state(self):
        if self.uploaded_file and self.download_location:
            self.run_button.config(state="normal")
        else:
            self.run_button.config(state="disabled")

    def upload_file(self):

        try:
            file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
            if file_path:
                self.uploaded_file = file_path
                self.file_label.config(
                    text=f"Selected File: {os.path.basename(file_path)}"
                )
                self.outputFinalFile = os.path.basename(file_path)
                self.check_run_button_state()
        except Exception as e:
            logging.error(f"Failed to upload file: {str(e)}")

    def show_intro_screen(self):
        intro_frame = tk.Frame(self.root, bg=self.bg_color)
        intro_frame.pack(expand=True, fill=tk.BOTH)

        # Load and resize the layout image
        try:
            original_image = Image.open(resource_path("layout.png"))
            # original_image = Image.open(layout_path)

            width, height = original_image.size
            new_width = 500  # You can adjust this value
            new_height = int(height * (new_width / width))
            resized_image = original_image.resize(
                (new_width, new_height), Image.LANCZOS
            )
            self.intro_image = ImageTk.PhotoImage(resized_image)

            image_label = tk.Label(
                intro_frame, image=self.intro_image, bg=self.bg_color
            )
            image_label.pack(expand=True)
        except Exception as e:
            logging.error(f"Failed to load intro image: {str(e)}")

        # Schedule the transition to the main screen
        self.root.after(3000, self.transition_to_main_screen)

    def transition_to_main_screen(self):
        # Clear the intro screen
        for widget in self.root.winfo_children():
            widget.destroy()

        # Create the main screen widgets
        self.create_widgets()

    def clear_main_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def create_widgets(self):
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Create a content frame to hold all widgets
        content_frame = tk.Frame(main_frame, bg=self.bg_color)
        content_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Display the logo at the top of the content frame
        if hasattr(self, "logo"):
            logo_label = tk.Label(content_frame, image=self.logo, bg=self.bg_color)
            logo_label.pack(pady=(0, 20))

        title_label = tk.Label(
            content_frame,
            text="Upload Your Origami Design",
            font=("Helvetica", 14),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        )
        title_label.pack(pady=20)

        upload_button = RoundedButton(
            content_frame, text="Upload JSON File", command=self.upload_file, radius=15
        )
        upload_button.pack(pady=20)

        self.file_label = tk.Label(
            content_frame,
            text="No file selected",
            font=("Helvetica", 14),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        )
        self.file_label.pack(pady=10)

        download_button = RoundedButton(
            content_frame,
            text="Select Download Location",
            command=self.select_download_location,
            radius=15,
        )
        download_button.pack(pady=20)

        self.download_label = tk.Label(
            content_frame,
            text="No location selected",
            font=("Helvetica", 14),
            bg=self.bg_color,
            fg=self.fg_color,
        )
        self.download_label.pack(pady=10)

        tk.Frame(content_frame, height=20, bg=self.bg_color).pack()

        self.run_button = tk.Button(
            content_frame,
            text="Run",
            command=self.run_process,
            bg="lightblue",
            fg="black",
            font=("Helvetica", 12, "bold"),
            padx=30,
            pady=15,
        )
        self.run_button.pack(pady=30)
        self.run_button.config(state="disabled")

    def estimate_runtime(self, space, sample_size=5):
        try:

            def objective(params):
                return self.run_autobreak(params)

            sample_times = []
            for _ in range(sample_size):
                params = {dim.name: space[i].rvs() for i, dim in enumerate(space)}
                result = objective(params)
                if result[1] is not None:
                    sample_times.append(result[1])

            if not sample_times:
                logging.error("All sample runs failed. Please check your setup.")
                return 0

            avg_time_per_run = sum(sample_times) / len(sample_times)
            num_cores = cpu_count()
            estimated_total_time = (
                50 * avg_time_per_run
            ) / num_cores  # Assuming 50 total evaluations

            return estimated_total_time
        except Exception as e:
            logging.error(f"Failed to estimate total runtime: {str(e)}")

    def ask_to_proceed(self, valid_params):
        proceed = messagebox.askyesno(
            "Proceed with Optimization",
            "Do you want to proceed with the full optimization?",
        )
        if proceed:
            self.run_full_optimization(valid_params)
        else:
            self.clear_main_window()
            self.create_widgets()  # Recreate the initial screen
            messagebox.showinfo(
                "Optimization Cancelled", "The optimization process has been cancelled."
            )

    def confirm_end_optimization(self):
        if messagebox.askyesno(
            "End Optimization",
            "Are you sure you want to end the current optimization process?",
        ):
            self.end_optimization()

    def end_optimization(self):
        self.stop_optimization = True
        self.root.after(100, self.check_optimization_ended)

    def check_optimization_ended(self):
        if self.optimization_thread.is_alive():
            self.root.after(100, self.check_optimization_ended)
        else:
            self.root.quit()

    def get_valid_params(self):
        self.space = [
            Integer(1, 30, name="nsol"),
            Integer(0, 30, name="npermute"),
            Integer(20, 24, name="minlength"),
            Integer(60, 64, name="maxlength"),
            Integer(20, 24, name="dontbreak"),
            Categorical([0, 3, 5, 10, 15, 20, 30, 40, 50], name="seed"),
            Categorical([2, 3, 4, 5, 6], name="rule_x"),
        ]
        return self.space

    def optimize_parameters(self, space):
        optimization_start_time = time.time()

        @use_named_args(space)
        def objective(**params):
            if self.stop_optimization:
                raise StopIteration("Optimization stopped by user")

            energy, _, _ = self.run_autobreak(params)
            return energy if energy is not None else 1e10

        try:
            self.n_calls = 50  # Total number of calls to make
            result = gp_minimize(
                objective,
                space,
                n_calls=self.n_calls,
                n_random_starts=10,
                n_jobs=cpu_count(),
                callback=self.update_progress,
            )
            optimization_end_time = time.time()
            total_optimization_time = optimization_end_time - optimization_start_time

            best_params = result.x

            # Pass the total optimization time to run_final_autobreak
            self.root.after(
                0,
                lambda: self.run_final_autobreak(best_params, total_optimization_time),
            )
        except StopIteration:
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Optimization Ended",
                    "The optimization process has been ended by the user.",
                ),
            )

    def run_process(self):
        try:
            # logging.info("Starting run_process")
            self.run_button.config(state="disabled")
            self.initial_energy = self.calculate_initial_energy()
            self.clear_main_window()
            self.setup_results_window()
            # logging.info("Finished run_process")
        except Exception as e:
            logging.error(f"Error running process: {str(e)}")
        finally:
            # logging.info(
            #     f"Button exists before re-enabling: {self.run_button is not None and self.run_button.winfo_exists()}")
            if self.run_button and self.run_button.winfo_exists():
                self.run_button.config(state="normal")

    def run_optimization(self):
        try:
            space = self.get_valid_params()
            num_cores = cpu_count()

            self.num_cores_label.config(
                text=f"Number of CPU cores: {num_cores}",
                font=("Helvetica", 14, "bold"),
                bg=self.bg_color,
                fg=self.fg_color,  # Use fg_color for text
                relief="flat",
            )

            self.estimated_runtime_label.config(
                text="Estimating runtime please wait ...",
                font=("Helvetica", 14, "bold"),
                bg=self.bg_color,
                fg=self.fg_color,  # Use fg_color for text
                relief="flat",
            )
            self.root.update()

            estimated_runtime = self.estimate_runtime(space, sample_size=5)

            self.estimated_runtime_label.config(
                text=f"Estimated total runtime: {estimated_runtime:.2f} seconds ({estimated_runtime/3600:.2f} hours)",
                font=("Helvetica", 14, "bold"),
                bg=self.bg_color,
                fg=self.fg_color,  # Use fg_color for text
                relief="flat",
            )
            self.root.update()

            self.root.after(1000, lambda: self.ask_to_proceed(space))
        except Exception as e:
            logging.error(f"Failed to run Optimization: {str(e)}")

    def run_full_optimization(self, valid_params):
        # Update the results window
        self.root.title("Optimization")
        for widget in self.root.winfo_children():
            widget.destroy()

        # Create a main frame to hold the content
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Create a frame for the content
        content_frame = tk.Frame(main_frame, bg=self.bg_color)
        content_frame.place(relx=0.5, rely=0.5, anchor="center")

        progress_label = tk.Label(
            content_frame,
            text="Optimization in progress...",
            font=("Helvetica", 20),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        )

        progress_label.pack(pady=10)

        self.progress_bar = ttk.Progressbar(
            content_frame, length=400, mode="determinate"
        )
        self.progress_bar.pack(pady=10)

        end_button = RoundedButton(
            content_frame,
            text="End Optimization",
            command=self.confirm_end_optimization,
            radius=10,
            padding=(10, 5),
        )
        end_button.pack(pady=50)

        # Start the optimization in a separate thread
        self.stop_optimization = False
        self.optimization_thread = threading.Thread(
            target=self.optimize_parameters, args=(valid_params,)
        )
        self.optimization_thread.start()

    def update_progress(self, optimization_result):
        progress = (len(optimization_result.x_iters) / self.n_calls) * 100
        self.root.after(0, lambda: self.progress_bar.config(value=progress))

    def run_autobreak(self, params, is_final_run=False, is_initial_run=False):
        start_time = time.time()

        def safe_convert(param, dtype):
            return dtype(param[0] if isinstance(param, np.ndarray) else param)

        nsol = safe_convert(params["nsol"], int)
        npermute = safe_convert(params["npermute"], int)
        minlength = safe_convert(params["minlength"], int)
        maxlength = safe_convert(params["maxlength"], int)
        dontbreak = safe_convert(params["dontbreak"], int)
        seed = safe_convert(params["seed"], int)
        rule_x = safe_convert(params["rule_x"], int)

        if is_initial_run:
            run_dir = os.path.join(self.download_location, "initial_run")
        elif is_final_run:
            input_filename = os.path.splitext(os.path.basename(self.uploaded_file))[0]
            result_folder_name = f"{input_filename}_Optimization_Result"
            run_dir = os.path.join(self.download_location, result_folder_name)

            # Check if the folder already exists and add a number if it does
            counter = 1
            while os.path.exists(run_dir):
                run_dir = os.path.join(
                    self.download_location, f"{result_folder_name}_{counter}"
                )
                counter += 1
        else:
            run_dir = os.path.join(
                self.download_location,
                f"temp_run_{nsol}_{npermute}_{minlength}_{maxlength}_{dontbreak}_{seed}_{rule_x}",
            )

        os.makedirs(run_dir, exist_ok=True)

        cmd = [
            "python",
            resource_path("autobreak_main.py"),  # Ensure correct path handling
            "-i",
            self.uploaded_file,
            "-o",
            run_dir,
            "--rule",
            f"xstap.all{rule_x}",
            "--func",
            "dG:50",
            "--nsol",
            str(nsol),
            "--minlength",
            str(minlength),
            "--maxlength",
            str(maxlength),
            "--verbose",
            "1",
            "--npermute",
            str(npermute),
            "--writeall",
            "--sequence",
            "yk_p7560.txt",
            "--dontbreak",
            str(dontbreak),
            "--seed",
            str(seed),
            "--score",
            "sum",
        ]

        try:
            logging.info("About to run autobreak_main.py")
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=3600
            )
            logging.info("Finished running autobreak_main.py")

            match = re.search(
                r"Final Gibbs Free Energy of the best solution: ([-\d.]+)",
                result.stdout,
            )

            # Capture the output directory and other file information
            self.output_directory = run_dir
            self.input_tail = os.path.basename(self.uploaded_file)

            # These file names are based on the typical output of autobreak_main.py
            # You may need to adjust them based on the actual output
            self.args_file = os.path.join(
                run_dir, "inputs", f"{os.path.splitext(self.input_tail)[0]}_args.txt"
            )
            self.seq_filename = os.path.join(run_dir, "inputs", "scaffold_sequence.txt")
            self.results_heatmap_ortho = os.path.join(
                run_dir,
                "intermediates",
                f"{os.path.splitext(self.input_tail)[0]}_ab_ortho.svg",
            )
            self.results_heatmap_path = os.path.join(
                run_dir,
                "intermediates",
                f"{os.path.splitext(self.input_tail)[0]}_ab_path.svg",
            )
            self.results_plots = os.path.join(
                run_dir,
                "intermediates",
                f"{os.path.splitext(self.input_tail)[0]}_plots.svg",
            )
            self.autobreak_log = os.path.join(
                run_dir, "intermediates", f"{os.path.splitext(self.input_tail)[0]}.log"
            )
            self.json_legacy_output = os.path.join(
                run_dir,
                "outputs",
                f"{os.path.splitext(self.input_tail)[0]}_autobreak.json",
            )
            self.results_report = os.path.join(
                run_dir, "outputs", f"{os.path.splitext(self.input_tail)[0]}_report.svg"
            )
            self.results_excel_file = os.path.join(
                run_dir,
                "outputs",
                f"{os.path.splitext(self.input_tail)[0]}_results.xlsx",
            )

            if match:
                energy = float(match.group(1))
                if not np.isfinite(energy):
                    return 1e10, time.time() - start_time, params
                run_time = time.time() - start_time
                return energy, run_time, params
            else:
                logging.error(f"Error: Couldn't extract Gibbs free energy for {params}")

                return None, time.time() - start_time, params
        except subprocess.CalledProcessError as e:
            print(
                f"Error running autobreak_main.py:\n\nStdout: {e.stdout}\n\nStderr: {e.stderr}"
            )
            logging.error(
                f"Error running autobreak_main.py:\n\nStdout: {e.stdout}\n\nStderr: {e.stderr}"
            )

            return 1e10, time.time() - start_time, params
        except subprocess.TimeoutExpired:
            logging.error(f"Timeout for parameters: {params}")
            return None, 3600, params
        except Exception as e:
            logging.error("autobreak_main.py timed out after 1 hour")
            return None, time.time() - start_time, params
        except subprocess.TimeoutExpired:
            # logging.error("autobreak_main.py timed out after 1 hour")
            return None, 3600, params
        finally:
            if not is_final_run:
                shutil.rmtree(run_dir, ignore_errors=True)

    def run_final_autobreak(self, best_params, total_optimization_time):
        # Clear the window
        for widget in self.root.winfo_children():
            widget.destroy()

        # Create a label to show progress
        progress_label = tk.Label(
            self.root,
            text="Running AutoBreak with optimized parameters...",
            font=("Helvetica", 14),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        )
        progress_label.pack(pady=20)

        # Convert best_params to dictionary
        param_dict = {dim.name: value for dim, value in zip(self.space, best_params)}

        # Run autobreak in a separate thread
        threading.Thread(
            target=self._execute_autobreak, args=(param_dict, total_optimization_time)
        ).start()

    def _execute_autobreak(self, params, total_optimization_time):
        energy, run_time, _ = self.run_autobreak(params, is_final_run=True)
        self.root.after(
            0,
            lambda: self._show_autobreak_results(
                energy, run_time, total_optimization_time
            ),
        )

    def format_energy(self, energy):
        return f"{energy:.2f}"

    def restart_app(self):
        # Destroy the current window
        self.root.destroy()
        # Create a new instance of Tk
        new_root = tk.Tk()
        # Create a new instance of OrigamiApp
        new_app = OrigamiApp(new_root)
        # Start the main loop for the new window
        new_root.mainloop()

    def show_output_info(self):
        if not self.output_directory:
            messagebox.showinfo(
                "Output Information", "No output information available yet."
            )
            return

        info_text = (
            "Output Information:\n\n\n"
            f"1. A folder named '{os.path.basename(self.output_directory)}' has been created in your chosen download location.\n\n"
            "2. Inside this folder, you'll find:\n\n"
            "   inputs/\n"
            f"   - {self.input_tail}  (Original input file)\n"
            f"   - {os.path.basename(self.args_file)}  (Run parameters)\n"
            f"   - {os.path.basename(self.seq_filename)}  (Scaffold sequence used)\n\n"
            "   intermediates/\n"
            f"   - {os.path.basename(self.results_heatmap_ortho)}  (Orthographic helix schematic)\n"
            f"   - {os.path.basename(self.results_heatmap_path)}  (Path Heatmap diagram)\n"
            f"   - {os.path.basename(self.results_plots)}  (Thermodynamic plots)\n"
            f"   - {os.path.basename(self.autobreak_log)}  (Debug and stderr log)\n\n"
            "   outputs/\n"
            f"   - {os.path.basename(self.json_legacy_output)}  (Break solution applied)\n"
            f"   - {os.path.basename(self.results_report)}  (Composite of heatmap and plots)\n"
            f"   - {os.path.basename(self.results_excel_file)}  (Per-staple model calculations)\n\n"
            "3. A zip file of the entire output folder has been created.\n\n"
            "4. The Gibbs Free Energy of the best solution has been calculated and saved."
        )
        messagebox.showinfo("Output Information", info_text)

    def setup_results_window(self):
        self.root.title("Optimization Results")

        # Create a main frame to hold the content
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Create a frame for the labels
        content_frame = tk.Frame(main_frame, bg=self.bg_color)
        content_frame.place(relx=0.5, rely=0.5, anchor="center")

        self.total_combinations_label = tk.Label(
            content_frame,
            text="Calculating...",
            font=("Helvetica", 12),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        )
        self.total_combinations_label.pack(pady=10)

        self.num_cores_label = tk.Label(
            content_frame, text="", font=("Helvetica", 12), background=self.bg_color
        )
        self.num_cores_label.pack(pady=10)

        self.estimated_runtime_label = tk.Label(
            content_frame,
            text="Estimating...",
            font=("Helvetica", 12),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        )
        self.estimated_runtime_label.pack(pady=10)

        threading.Thread(target=self.run_optimization).start()

    def _show_autobreak_results(self, energy, final_run_time, total_optimization_time):
        for widget in self.root.winfo_children():
            widget.destroy()

        frame = tk.Frame(self.root, bg=self.bg_color)
        frame.pack(expand=True, fill=tk.BOTH)

        # Add the tooltip button in the top right corner
        info_button = RoundedButton(
            frame,
            text="Get info 💡",
            command=self.show_output_info,
            radius=15,
            width=4,
            height=1,
        )
        info_button.pack(side=tk.TOP, anchor=tk.NE, padx=10, pady=10)

        content_frame = tk.Frame(frame, bg=self.bg_color)
        content_frame.pack(expand=True)
        tk.Label(
            content_frame,
            text="AutoBreak Execution Complete",
            font=("Helvetica", 18, "bold"),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        ).pack(pady=10)

        tk.Label(
            content_frame,
            text=f"Initial Gibbs Free Energy: {self.format_energy(self.initial_energy)} J/mol",
            font=("Helvetica", 18),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        ).pack(pady=5)

        tk.Label(
            content_frame,
            text=f"Final Gibbs Free Energy: {self.format_energy(energy)} J/mol",
            font=("Helvetica", 18),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        ).pack(pady=5)
        tk.Label(
            content_frame,
            text=f"An improvement of : {self.format_energy(energy - self.initial_energy)} J/mol",
            font=("Helvetica", 18),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        ).pack(pady=5)

        tk.Label(
            content_frame,
            text=f"Final Run Time: {final_run_time:.2f} seconds",
            font=("Helvetica", 18),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        ).pack(pady=5)

        tk.Label(
            content_frame,
            text=f"Total Optimization Time: {total_optimization_time:.2f} seconds ({total_optimization_time/3600:.2f} hours)",
            font=("Helvetica", 18),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        ).pack(pady=5)

        tk.Label(
            content_frame,
            text=f"Results saved in: {self.download_location}",
            font=("Helvetica", 16),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        ).pack(pady=5)

        try_another_button = RoundedButton(
            content_frame,
            text="Try another structure",
            command=self.restart_app,
            radius=15,
        )
        try_another_button.pack(pady=20)

        content_frame.pack(expand=True)

    def show_final_results(self, best_params, best_energy, total_time, total_params):
        for widget in self.root.winfo_children():
            widget.destroy()

        tk.Label(
            self.root,
            text="Optimization Complete",
            font=("Helvetica", 14, "bold"),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        ).pack(pady=10)

        param_names = [dim.name for dim in self.space]
        param_text = ", ".join(
            [f"{name}={value}" for name, value in zip(param_names, best_params)]
        )

        tk.Label(
            self.root,
            text=f"Best parameters: {param_text}",
            font=("Helvetica", 14),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            # relief="flat",
            wraplength=450,
        ).pack(pady=5)

        tk.Label(
            self.root,
            text=f"Best Gibbs free energy: {best_energy}",
            font=("Helvetica", 14),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        ).pack(pady=5)

        tk.Label(
            self.root,
            text=f"Total number of evaluations: {total_params}",
            font=("Helvetica", 14),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        ).pack(pady=5)

        tk.Label(
            self.root,
            text=f"Total run time: {total_time:.2f} seconds ({total_time/3600:.2f} hours)",
            font=("Helvetica", 14),
            bg=self.bg_color,
            fg=self.fg_color,  # Use fg_color for text
            relief="flat",
        ).pack(pady=5)

        if total_params > 0:
            tk.Label(
                self.root,
                text=f"Average time per run: {total_time/total_params:.2f} seconds",
                font=("Helvetica", 14),
                bg=self.bg_color,
                fg=self.fg_color,  # Use fg_color for text
                relief="flat",
            ).pack(pady=5)


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = App(root)
        root.mainloop()
    except Exception as e:
        logging.critical("A critical error occurred", exc_info=True)
