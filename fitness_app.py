import tkinter as tk
from tkinter import messagebox, ttk
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time
from datetime import datetime, timedelta
import unicodedata

class FitnessApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ứng dụng Hỗ trợ Tập luyện và Giảm cân")
        self.root.geometry("1000x750")

        # Cấu hình style cho giao diện đẹp hơn
        self.style = ttk.Style()
        self.style.configure("TLabel", font=("Arial", 12))
        self.style.configure("TButton", font=("Arial", 11))
        self.style.configure("TCombobox", font=("Arial", 11))
        self.style.configure("Treeview.Heading", font=("Arial", 12, "bold"))
        self.style.configure("Treeview", font=("Arial", 11), rowheight=30)
        self.style.theme_use("clam")

        self.conn = sqlite3.connect("D:/ki3nam4/thuctap/fitness.db")
        self.cursor = self.conn.cursor()
        self.create_tables()

        try:
            self.food_df = pd.read_csv("D:/ki3nam4/thuctap/food.csv", encoding="utf-8")
            self.exercise_df = pd.read_csv("D:/ki3nam4/thuctap/exercise.csv", encoding="utf-8")
            print("Food DataFrame:\n", self.food_df.head())
            print("Exercise DataFrame:\n", self.exercise_df.head())
        except FileNotFoundError as e:
            messagebox.showerror("Lỗi", f"Không tìm thấy file: {str(e)}. Vui lòng kiểm tra đường dẫn D:/ki3nam4/thuctap/")
            self.root.destroy()
            return

        self.profile = {}
        self.tdee = 0
        self.date_selector = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=15, padx=10, fill="both", expand=True)

        self.create_profile_tab()
        self.create_workout_tab()
        self.create_weight_tab()
        self.create_food_tab()
        self.create_report_tab()

        self.water_reminder_running = True
        self.start_water_reminder()

        self.update_bmi_display()
        self.update_weight_progress()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY,
                name TEXT,
                age INTEGER,
                gender TEXT,
                weight REAL,
                height REAL,
                goal TEXT,
                weight_goal REAL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, age INTEGER, weight REAL,
                height REAL, activity TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS workout_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, date TEXT,
                exercise TEXT, duration REAL, calories REAL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS weight_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, date TEXT, weight REAL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS food_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, date TEXT,
                meal_type TEXT, food TEXT, amount REAL, calories REAL,
                protein REAL, fat REAL, carbs REAL
            )
        ''')
        try:
            self.cursor.execute("ALTER TABLE food_log ADD COLUMN meal_type TEXT")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            self.cursor.execute("ALTER TABLE user_profile ADD COLUMN weight_goal REAL")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass
        self.conn.commit()

    def create_profile_tab(self):
        frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(frame, text="Hồ sơ cá nhân")
        input_frame = ttk.LabelFrame(frame, text="Thông tin cá nhân", padding=15)
        input_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.name_var = tk.StringVar()
        self.age_var = tk.IntVar()
        self.gender_var = tk.StringVar()
        self.weight_var = tk.DoubleVar()
        self.height_var = tk.DoubleVar()
        self.goal_var = tk.StringVar()
        ttk.Label(input_frame, text="Họ và tên:").grid(row=0, column=0, padx=5, pady=8, sticky='w')
        ttk.Entry(input_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, padx=5, pady=8)
        ttk.Label(input_frame, text="Tuổi:").grid(row=1, column=0, padx=5, pady=8, sticky='w')
        ttk.Entry(input_frame, textvariable=self.age_var, width=30).grid(row=1, column=1, padx=5, pady=8)
        ttk.Label(input_frame, text="Giới tính:").grid(row=2, column=0, padx=5, pady=8, sticky='w')
        self.gender_var.set("Nam")
        gender_menu = ttk.Combobox(input_frame, textvariable=self.gender_var, values=["Nam", "Nữ", "Khác"])
        gender_menu.grid(row=2, column=1, padx=5, pady=8)
        ttk.Label(input_frame, text="Cân nặng (kg):").grid(row=3, column=0, padx=5, pady=8, sticky='w')
        ttk.Entry(input_frame, textvariable=self.weight_var, width=30).grid(row=3, column=1, padx=5, pady=8)
        ttk.Label(input_frame, text="Chiều cao (cm):").grid(row=4, column=0, padx=5, pady=8, sticky='w')
        ttk.Entry(input_frame, textvariable=self.height_var, width=30).grid(row=4, column=1, padx=5, pady=8)
        ttk.Label(input_frame, text="Mục tiêu:").grid(row=5, column=0, padx=5, pady=8, sticky='w')
        ttk.Entry(input_frame, textvariable=self.goal_var, width=30).grid(row=5, column=1, padx=5, pady=8)
        ttk.Button(input_frame, text="Lưu hồ sơ", command=self.save_profile).grid(row=6, column=0, columnspan=2, pady=15)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.load_profile()

    def create_workout_tab(self):
        frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(frame, text="Nhật ký tập luyện")

        input_frame = ttk.LabelFrame(frame, text="Thêm bài tập", padding=15)
        input_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        ttk.Label(input_frame, text="Lọc bài tập:").grid(row=0, column=0, sticky="w", padx=5, pady=8)
        self.exercise_filter = ttk.Combobox(input_frame,
                                            values=["Tất cả"] + self.exercise_df["exercise_name"].to_list(),
                                            state="normal")
        self.exercise_filter.grid(row=0, column=1, pady=8, padx=5, sticky="ew")
        self.exercise_filter.set("Tất cả")
        self.exercise_filter.bind("<<ComboboxSelected>>", self.filter_workout_history)

        ttk.Label(input_frame, text="Lọc theo năm:").grid(row=1, column=0, sticky="w", padx=5, pady=8)
        years = ["Tất cả"] + [str(year) for year in range(2020, datetime.now().year + 1)]
        self.year_filter = ttk.Combobox(input_frame, values=years, state="normal")
        self.year_filter.grid(row=1, column=1, pady=8, padx=5, sticky="ew")
        self.year_filter.set("Tất cả")
        self.year_filter.bind("<<ComboboxSelected>>", self.filter_workout_history)

        ttk.Label(input_frame, text="Bài tập:").grid(row=2, column=0, sticky="w", padx=5, pady=8)
        self.exercise_combo = ttk.Combobox(input_frame, values=self.exercise_df["exercise_name"].to_list(),
                                           state="normal")
        self.exercise_combo.grid(row=2, column=1, pady=8, padx=5, sticky="ew")
        self.exercise_combo.bind('<KeyRelease>',
                                 lambda e: [self.update_exercise_suggestions(e),
                                            print(f"Exercise KeyRelease triggered, Key: {e.keysym}")])
        self.exercise_combo.focus_set()

        ttk.Label(input_frame, text="Thời gian (phút):").grid(row=3, column=0, sticky="w", padx=5, pady=8)
        self.duration_entry = ttk.Entry(input_frame)
        self.duration_entry.grid(row=3, column=1, pady=8, padx=5, sticky="ew")

        ttk.Button(input_frame, text="Lưu bài tập", command=self.log_workout).grid(row=4, column=0, columnspan=2,
                                                                                   pady=15)

        overview_frame = ttk.LabelFrame(frame, text="Tổng quan", padding=15)
        overview_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")

        self.total_duration_label = ttk.Label(overview_frame, text="Tổng thời gian: 0 phút")
        self.total_duration_label.grid(row=0, column=0, padx=15, pady=5)

        self.total_sessions_label = ttk.Label(overview_frame, text="Số buổi: 0")
        self.total_sessions_label.grid(row=0, column=1, padx=15, pady=5)

        self.total_calories_label = ttk.Label(overview_frame, text="Tổng calo: 0 kcal")
        self.total_calories_label.grid(row=0, column=2, padx=15, pady=5)

        main_frame = ttk.Frame(frame)
        main_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="nsew")

        self.workout_tree = ttk.Treeview(main_frame, columns=("date", "exercise", "duration", "calories"),
                                         show="headings")
        self.workout_tree.heading("date", text="Ngày")
        self.workout_tree.heading("exercise", text="Bài tập")
        self.workout_tree.heading("duration", text="Phút")
        self.workout_tree.heading("calories", text="Calo")
        self.workout_tree.column("date", width=120)
        self.workout_tree.column("exercise", width=200)
        self.workout_tree.column("duration", width=100)
        self.workout_tree.column("calories", width=100)
        self.workout_tree.grid(row=0, column=0, padx=5, sticky="nsew")

        self.workout_tree.bind('<Double-1>', self.on_workout_double_click)

        self.calorie_frame = ttk.LabelFrame(main_frame, text=f"Tình trạng calo ngày {self.date_selector.get()}",
                                            padding=15)
        self.calorie_frame.grid(row=0, column=1, padx=10, sticky="nsew")

        self.calories_in_label = ttk.Label(self.calorie_frame, text="Calo nạp: 0 kcal", font=("Arial", 12))
        self.calories_in_label.grid(row=0, column=0, padx=5, pady=8, sticky="w")

        self.calories_out_label = ttk.Label(self.calorie_frame, text="Calo tiêu: 0 kcal", font=("Arial", 12))
        self.calories_out_label.grid(row=1, column=0, padx=5, pady=8, sticky="w")

        self.calorie_deficit_label = ttk.Label(self.calorie_frame, text="Thâm hụt: 0 kcal", font=("Arial", 12))
        self.calorie_deficit_label.grid(row=2, column=0, padx=5, pady=8, sticky="w")

        self.calorie_status_label = ttk.Label(self.calorie_frame, text="", font=("Arial", 12, "italic"))
        self.calorie_status_label.grid(row=3, column=0, padx=5, pady=8, sticky="w")

        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)
        frame.columnconfigure(0, weight=1)

        self.load_workout_history()

    def create_food_tab(self):
        frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(frame, text="Nhật ký ăn uống")

        input_frame = ttk.LabelFrame(frame, text="Nhập món ăn", padding=15)
        input_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        ttk.Label(input_frame, text="Chọn ngày:").grid(row=0, column=0, sticky="w", padx=5, pady=8)
        date_combo = ttk.Combobox(input_frame, textvariable=self.date_selector, state="readonly")
        date_combo.grid(row=0, column=1, pady=8, padx=5, sticky="ew")
        date_combo.bind("<<ComboboxSelected>>", self.on_date_selected)
        self.update_date_selector()

        ttk.Label(input_frame, text="Bữa ăn:").grid(row=1, column=0, sticky="w", padx=5, pady=8)
        self.meal_type_combo = ttk.Combobox(input_frame, values=[
            "Bữa sáng", "Bữa trưa", "Bữa tối",
            "Bữa phụ sáng", "Bữa phụ chiều", "Bữa phụ tối"
        ], state="normal")
        self.meal_type_combo.grid(row=1, column=1, pady=8, padx=5, sticky="ew")
        self.meal_type_combo.set("Bữa sáng")

        ttk.Label(input_frame, text="Thực phẩm:").grid(row=2, column=0, sticky="w", padx=5, pady=8)
        self.food_combo = ttk.Combobox(input_frame, values=self.food_df["food_name"].to_list(), state="normal")
        self.food_combo.grid(row=2, column=1, pady=8, padx=5, sticky="ew")
        self.food_combo.bind('<KeyRelease>',
                             lambda e: [self.update_food_suggestions(e),
                                        print(f"Food KeyRelease triggered, Key: {e.keysym}")])
        self.food_combo.focus_set()

        ttk.Label(input_frame, text="Số gram (g):").grid(row=3, column=0, sticky="w", padx=5, pady=8)
        self.food_amount_entry = ttk.Entry(input_frame)
        self.food_amount_entry.grid(row=3, column=1, pady=8, padx=5, sticky="ew")

        ttk.Button(input_frame, text="Lưu món ăn", command=self.log_food).grid(row=4, column=0, columnspan=2, pady=15)

        summary_frame = ttk.LabelFrame(frame, text="Tổng dinh dưỡng hôm nay", padding=15)
        summary_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.total_calories_label = ttk.Label(summary_frame, text="Tổng calo: 0 kcal")
        self.total_calories_label.grid(row=0, column=0, padx=15, pady=5)

        self.total_protein_label = ttk.Label(summary_frame, text="Protein: 0 g")
        self.total_protein_label.grid(row=0, column=1, padx=15, pady=5)

        self.total_carbs_label = ttk.Label(summary_frame, text="Carbs: 0 g")
        self.total_carbs_label.grid(row=0, column=2, padx=15, pady=5)

        self.total_fat_label = ttk.Label(summary_frame, text="Fat: 0 g")
        self.total_fat_label.grid(row=0, column=3, padx=15, pady=5)

        self.calorie_warning_label = ttk.Label(frame, text="", font=("Arial", 12, "italic"))
        self.calorie_warning_label.grid(row=2, column=0, columnspan=2, pady=10)

        self.food_log_frame = ttk.Frame(frame)
        self.food_log_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        self.food_log_canvas = tk.Canvas(self.food_log_frame)
        self.food_log_scrollbar = ttk.Scrollbar(self.food_log_frame, orient="vertical",
                                                command=self.food_log_canvas.yview)
        self.food_log_scrollable_frame = ttk.Frame(self.food_log_canvas)

        self.food_log_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.food_log_canvas.configure(scrollregion=self.food_log_canvas.bbox("all"))
        )

        self.food_log_canvas.create_window((0, 0), window=self.food_log_scrollable_frame, anchor="nw")
        self.food_log_canvas.configure(yscrollcommand=self.food_log_scrollbar.set)

        self.food_log_canvas.pack(side="left", fill="both", expand=True)
        self.food_log_scrollbar.pack(side="right", fill="y")

        self.meal_treeviews = {}
        self.meal_calorie_labels = {}

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(3, weight=1)

        self.load_food_log()

    def create_weight_tab(self):
        frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(frame, text="Cập nhật cân nặng")

        input_frame = ttk.LabelFrame(frame, text="Cập nhật cân nặng và mục tiêu", padding=15)
        input_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        ttk.Label(input_frame, text="Cân nặng hiện tại (kg):").grid(row=0, column=0, sticky="w", padx=5, pady=8)
        self.weight_update_entry = ttk.Entry(input_frame, width=30)
        self.weight_update_entry.grid(row=0, column=1, pady=8, padx=5)

        ttk.Label(input_frame, text="Mục tiêu cân nặng (kg):").grid(row=1, column=0, sticky="w", padx=5, pady=8)
        self.weight_goal_entry = ttk.Entry(input_frame, width=30)
        self.weight_goal_entry.grid(row=1, column=1, pady=8, padx=5)

        ttk.Button(input_frame, text="Lưu", command=self.log_weight_and_goal).grid(row=2, column=0, columnspan=2, pady=15)

        self.bmi_label = ttk.Label(input_frame, text="BMI hiện tại: Chưa có dữ liệu", font=("Arial", 12))
        self.bmi_label.grid(row=3, column=0, columnspan=2, pady=8)

        self.bmi_reminder_label = ttk.Label(input_frame, text="", font=("Arial", 12, "italic"))
        self.bmi_reminder_label.grid(row=4, column=0, columnspan=2, pady=8)

        self.weight_progress_label = ttk.Label(input_frame, text="Tiến độ giảm cân: Chưa có dữ liệu", font=("Arial", 12))
        self.weight_progress_label.grid(row=5, column=0, columnspan=2, pady=8)

        self.weight_remaining_label = ttk.Label(input_frame, text="Còn lại để đạt mục tiêu: Chưa có dữ liệu", font=("Arial", 12))
        self.weight_remaining_label.grid(row=6, column=0, columnspan=2, pady=8)

        history_frame = ttk.LabelFrame(frame, text="Lịch sử cập nhật cân nặng", padding=15)
        history_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        self.weight_tree = ttk.Treeview(history_frame, columns=("date", "weight"), show="headings")
        self.weight_tree.heading("date", text="Ngày")
        self.weight_tree.heading("weight", text="Cân nặng (kg)")
        self.weight_tree.column("date", width=120)
        self.weight_tree.column("weight", width=100)
        self.weight_tree.pack(fill="x", padx=5, pady=5)

        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.weight_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.weight_tree.configure(yscrollcommand=scrollbar.set)

        self.weight_tree.bind('<Double-1>', self.on_weight_double_click)

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=2)

        self.load_weight_history()

    def create_report_tab(self):
        frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(frame, text="Báo cáo")

        # Tạo notebook con cho các loại báo cáo
        report_notebook = ttk.Notebook(frame)
        report_notebook.pack(pady=15, fill="both", expand=True)

        # Tạo các tab con
        self.workout_week_tab = ttk.Frame(report_notebook)
        self.workout_month_tab = ttk.Frame(report_notebook)
        self.weight_month_tab = ttk.Frame(report_notebook)
        self.weight_year_tab = ttk.Frame(report_notebook)

        report_notebook.add(self.workout_week_tab, text="Tập luyện tuần")
        report_notebook.add(self.workout_month_tab, text="Tập luyện tháng")
        report_notebook.add(self.weight_month_tab, text="Cân nặng tháng")
        report_notebook.add(self.weight_year_tab, text="Cân nặng năm")

        # Tạo canvas cho từng tab con
        self.workout_week_canvas = tk.Canvas(self.workout_week_tab, width=900, height=450)
        self.workout_week_canvas.pack(pady=10, fill="both", expand=True)
        self.workout_month_canvas = tk.Canvas(self.workout_month_tab, width=900, height=450)
        self.workout_month_canvas.pack(pady=10, fill="both", expand=True)
        self.weight_month_canvas = tk.Canvas(self.weight_month_tab, width=900, height=450)
        self.weight_month_canvas.pack(pady=10, fill="both", expand=True)
        self.weight_year_canvas = tk.Canvas(self.weight_year_tab, width=900, height=450)
        self.weight_year_canvas.pack(pady=10, fill="both", expand=True)

        # Biến để theo dõi trạng thái biểu đồ
        self.chart_displayed = {
            "workout_week": False,
            "workout_month": False,
            "weight_month": False,
            "weight_year": False
        }

        # Bind sự kiện khi chuyển tab
        report_notebook.bind("<<NotebookTabChanged>>", self.on_report_tab_changed)

        self.load_profile()

    def on_report_tab_changed(self, event):
        """Xử lý khi chuyển tab con trong tab Báo cáo"""
        notebook = event.widget
        selected_tab = notebook.index(notebook.select())

        # Vẽ biểu đồ tương ứng nếu chưa được vẽ
        if selected_tab == 0 and not self.chart_displayed["workout_week"]:
            self.show_workout_report("week", self.workout_week_canvas)
            self.chart_displayed["workout_week"] = True
        elif selected_tab == 1 and not self.chart_displayed["workout_month"]:
            self.show_workout_report("month", self.workout_month_canvas)
            self.chart_displayed["workout_month"] = True
        elif selected_tab == 2 and not self.chart_displayed["weight_month"]:
            self.show_weight_report("month", self.weight_month_canvas)
            self.chart_displayed["weight_month"] = True
        elif selected_tab == 3 and not self.chart_displayed["weight_year"]:
            self.show_weight_report("year", self.weight_year_canvas)
            self.chart_displayed["weight_year"] = True

    def show_workout_report(self, period, canvas):
        """Hiển thị biểu đồ calo đốt theo thời gian"""
        today = datetime.now()
        start = today - timedelta(days=7 if period == "week" else 30)
        self.cursor.execute("SELECT date, SUM(calories) FROM workout_log WHERE user_id=? AND date >= ? GROUP BY date",
                            (self.profile.get("id", 1), start.strftime("%Y-%m-%d")))
        data = dict(self.cursor.fetchall())
        dates = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((today - start).days + 1)]
        values = [data.get(d, 0) for d in dates]

        # Xóa nội dung cũ trong canvas
        for widget in canvas.winfo_children():
            widget.destroy()

        # Kiểm tra nếu không có dữ liệu
        if not any(values):
            label = ttk.Label(canvas, text="Chưa có dữ liệu tập luyện để hiển thị biểu đồ", font=("Arial", 12))
            label.pack(pady=200)
            return

        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.bar(dates, values, color="#4CAF50")
        ax.set_title(f"Calo đốt mỗi ngày ({'tuần' if period == 'week' else 'tháng'})", fontsize=14)
        ax.set_xlabel("Ngày", fontsize=12)
        ax.set_ylabel("Calo (kcal)", fontsize=12)
        ax.set_xticks(dates)
        ax.set_xticklabels(dates, rotation=45, ha="right")
        ax.grid(True, axis="y", linestyle="--", alpha=0.7)
        plt.tight_layout()

        chart_canvas = FigureCanvasTkAgg(fig, master=canvas)
        chart_canvas.draw()
        chart_canvas.get_tk_widget().pack(fill="both", expand=True)

        plt.close(fig)

    def show_weight_report(self, period, canvas):
        """Hiển thị biểu đồ cân nặng theo thời gian"""
        today = datetime.now()
        start = today - timedelta(days=30 if period == "month" else 365)
        self.cursor.execute("SELECT date, weight FROM weight_log WHERE user_id=? AND date >= ? ORDER BY date",
                            (self.profile.get("id", 1), start.strftime("%Y-%m-%d")))
        rows = self.cursor.fetchall()

        # Xóa nội dung cũ trong canvas
        for widget in canvas.winfo_children():
            widget.destroy()

        # Kiểm tra nếu không có dữ liệu
        if not rows:
            label = ttk.Label(canvas, text="Chưa có dữ liệu cân nặng để hiển thị biểu đồ", font=("Arial", 12))
            label.pack(pady=200)
            return

        dates, weights = zip(*rows)
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.plot(dates, weights, marker="o", color="#2196F3")
        ax.set_title(f"Cân nặng theo thời gian ({'tháng' if period == 'month' else 'năm'})", fontsize=14)
        ax.set_xlabel("Ngày", fontsize=12)
        ax.set_ylabel("Cân nặng (kg)", fontsize=12)
        ax.set_xticks(dates)
        ax.set_xticklabels(dates, rotation=45, ha="right")
        ax.grid(True, linestyle="--", alpha=0.7)
        plt.tight_layout()

        chart_canvas = FigureCanvasTkAgg(fig, master=canvas)
        chart_canvas.draw()
        chart_canvas.get_tk_widget().pack(fill="both", expand=True)

        plt.close(fig)

    def clear_report(self):
        # Không cần thiết trong cách tiếp cận mới
        pass

    def calculate_tdee(self, weight, height, age, activity_level):
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
        activity_factors = {
            "Ít vận động": 1.2,
            "Vận động nhẹ": 1.375,
            "Vận động vừa": 1.55,
            "Vận động nhiều": 1.725
        }
        return bmr * activity_factors.get(activity_level, 1.2)

    def calculate_bmi(self, weight, height):
        if height <= 0 or weight <= 0:
            return 0
        height_m = height / 100
        return weight / (height_m ** 2)

    def get_bmi_message(self, bmi, name):
        if bmi == 0:
            return "Chưa có đủ dữ liệu cân nặng hoặc chiều cao để tính BMI."
        elif bmi < 18.5:
            return f"{name}, bạn đang thiếu cân! Hãy tăng cường dinh dưỡng."
        elif 18.5 <= bmi < 25:
            return f"{name}, bạn có cân nặng bình thường. Giữ vững nhé!"
        elif 25 <= bmi < 30:
            return f"{name}, bạn đang thừa cân! Hãy chú ý chế độ ăn và tập luyện."
        else:
            return f"{name}, bạn đang trong tình trạng béo phì. Cần điều chỉnh lối sống ngay!"

    def update_bmi_display(self):
        if not hasattr(self, 'bmi_label') or not hasattr(self, 'bmi_reminder_label'):
            return

        self.cursor.execute("SELECT weight FROM weight_log WHERE user_id=? ORDER BY date DESC LIMIT 1",
                            (self.profile.get("id", 1),))
        weight_result = self.cursor.fetchone()
        weight = weight_result[0] if weight_result else self.profile.get("weight", 0)

        height = self.profile.get("height", 0)
        name = self.profile.get("name", "Bạn")

        bmi = self.calculate_bmi(weight, height)
        self.bmi_label.config(text=f"BMI hiện tại: {bmi:.1f}" if bmi > 0 else "BMI hiện tại: Chưa có dữ liệu")
        self.bmi_reminder_label.config(text=self.get_bmi_message(bmi, name))

    def log_workout(self):
        try:
            exercise = self.exercise_combo.get()
            if not exercise:
                raise ValueError("Vui lòng chọn bài tập")
            duration = float(self.duration_entry.get())
            if duration <= 0:
                raise ValueError("Thời gian phải lớn hơn 0")
            cal = self.exercise_df[self.exercise_df["exercise_name"] == exercise]["calories_per_minute"].iloc[0]
            total_cal = cal * duration

            self.cursor.execute(
                "INSERT INTO workout_log (user_id, date, exercise, duration, calories) VALUES (?, ?, ?, ?, ?)",
                (self.profile.get("id", 1), self.date_selector.get(), exercise, duration, total_cal))
            self.conn.commit()
            self.load_workout_history()

            messagebox.showinfo("Thành công", f"Đã lưu: {exercise} - {duration} phút - {total_cal:.1f} calo")
        except ValueError as ve:
            messagebox.showerror("Lỗi", str(ve))
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi lưu bài tập: {str(e)}")

    def on_workout_double_click(self, event):
        item = self.workout_tree.selection()
        if not item:
            return
        item = item[0]
        values = self.workout_tree.item(item, "values")
        exercise_name = values[1]
        if messagebox.askyesno("Xác nhận", f"Bạn có muốn xóa bài tập: {exercise_name}?"):
            self.delete_workout_entry(item)

    def delete_workout_entry(self, item_id):
        try:
            values = self.workout_tree.item(item_id, "values")
            exercise_name = values[1]
            date = values[0]
            duration = float(values[2])
            self.cursor.execute(
                "DELETE FROM workout_log WHERE user_id=? AND date=? AND exercise=? AND duration=?",
                (self.profile.get("id", 1), date, exercise_name, duration))
            self.conn.commit()
            self.load_workout_history()
            messagebox.showinfo("Thành công", f"Đã xóa bài tập: {exercise_name}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xóa bài tập: {str(e)}")

    def load_workout_history(self):
        for row in self.workout_tree.get_children():
            self.workout_tree.delete(row)

        query = '''
            SELECT date, exercise, duration, calories
            FROM workout_log
            WHERE user_id = ?
        '''
        params = [self.profile.get("id", 1)]

        exercise_filter = self.exercise_filter.get()
        if exercise_filter != "Tất cả":
            query += " AND exercise = ?"
            params.append(exercise_filter)

        year_filter = self.year_filter.get()
        if year_filter != "Tất cả":
            query += " AND strftime('%Y', date) = ?"
            params.append(year_filter)

        query += " ORDER BY date DESC"
        self.cursor.execute(query, params)

        for row in self.cursor.fetchall():
            self.workout_tree.insert('', 'end', values=row)

        summary_query = '''
            SELECT SUM(duration), COUNT(DISTINCT date), SUM(calories)
            FROM workout_log
            WHERE user_id = ?
        '''
        summary_params = [self.profile.get("id", 1)]

        if exercise_filter != "Tất cả":
            summary_query += " AND exercise = ?"
            summary_params.append(exercise_filter)

        if year_filter != "Tất cả":
            summary_query += " AND strftime('%Y', date) = ?"
            summary_params.append(year_filter)

        self.cursor.execute(summary_query, summary_params)
        result = self.cursor.fetchone()
        total_duration = result[0] or 0
        total_sessions = result[1] or 0
        total_calories = result[2] or 0

        self.total_duration_label.config(text=f"Tổng thời gian: {total_duration:.1f} phút")
        self.total_sessions_label.config(text=f"Số buổi: {total_sessions}")
        self.total_calories_label.config(text=f"Tổng calo: {total_calories:.1f} kcal")

        selected_date = self.date_selector.get()
        self.calorie_frame.config(text=f"Tình trạng calo ngày {selected_date}")

        self.cursor.execute("SELECT SUM(calories) FROM food_log WHERE date=? AND user_id=?", (selected_date, self.profile.get("id", 1)))
        calories_in = self.cursor.fetchone()[0] or 0

        self.cursor.execute("SELECT SUM(calories) FROM workout_log WHERE date=? AND user_id=?", (selected_date, self.profile.get("id", 1)))
        workout_calories = self.cursor.fetchone()[0] or 0
        calories_out = workout_calories + self.tdee

        deficit = calories_out - calories_in

        self.calories_in_label.config(text=f"Calo nạp: {calories_in:.1f} kcal")
        self.calories_out_label.config(text=f"Calo tiêu: {calories_out:.1f} kcal")
        self.calorie_deficit_label.config(text=f"Thâm hụt: {deficit:.1f} kcal")

        if deficit < 0:
            self.calorie_status_label.config(
                text=f"⚠️ Dư {-deficit:.1f} calo! Giảm ăn hoặc tập thêm nhé!",
                foreground="red"
            )
        else:
            self.calorie_status_label.config(
                text=f"👍 Đạt thâm hụt {deficit:.1f} calo. Tốt lắm!",
                foreground="green"
            )

    def filter_workout_history(self, event):
        self.load_workout_history()

    def log_food(self):
        try:
            meal_type = self.meal_type_combo.get()
            if not meal_type:
                raise ValueError("Vui lòng chọn bữa ăn")

            food = self.food_combo.get()
            if not food:
                raise ValueError("Vui lòng chọn thực phẩm")

            amount = self.food_amount_entry.get()
            if not amount:
                raise ValueError("Vui lòng nhập số gram")
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Số gram phải lớn hơn 0")

            food_data = self.food_df[self.food_df["food_name"] == food]
            if food_data.empty:
                raise ValueError(f"Thực phẩm '{food}' không tồn tại trong cơ sở dữ liệu")

            food_data = food_data.iloc[0]
            amount_per_100g = amount / 100

            self.cursor.execute('''
                INSERT INTO food_log (user_id, date, meal_type, food, amount, calories, protein, fat, carbs)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.profile.get("id", 1),
                self.date_selector.get(),
                meal_type,
                food,
                amount,
                food_data["calories"] * amount_per_100g,
                food_data["protein"] * amount_per_100g,
                food_data["fat"] * amount_per_100g,
                food_data["carbs"] * amount_per_100g
            ))
            self.conn.commit()
            self.update_date_selector()
            self.load_food_log()
            self.load_workout_history()
            self.check_calorie_balance()
            messagebox.showinfo("Thành công", f"Đã lưu món: {food} cho {meal_type}")
        except ValueError as ve:
            messagebox.showerror("Lỗi", str(ve))
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi lưu món ăn: {str(e)}")

    def on_food_double_click(self, event, meal_type):
        item = self.meal_treeviews[meal_type].selection()
        if not item:
            return
        item = item[0]
        values = self.meal_treeviews[meal_type].item(item, "values")
        food_name = values[0]
        if messagebox.askyesno("Xác nhận", f"Bạn có muốn xóa món: {food_name}?"):
            self.delete_food_entry(meal_type, item)

    def delete_food_entry(self, meal_type, item_id):
        try:
            values = self.meal_treeviews[meal_type].item(item_id, "values")
            food_name = values[0]
            amount = float(values[1])
            selected_date = self.date_selector.get()
            self.cursor.execute(
                "DELETE FROM food_log WHERE user_id=? AND date=? AND meal_type=? AND food=? AND amount=?",
                (self.profile.get("id", 1), selected_date, meal_type, food_name, amount))
            self.conn.commit()
            self.load_food_log()
            self.load_workout_history()
            self.check_calorie_balance()
            messagebox.showinfo("Thành công", f"Đã xóa món: {food_name}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xóa món: {str(e)}")

    def load_food_log(self, event=None):
        for widget in self.food_log_scrollable_frame.winfo_children():
            widget.destroy()

        selected_date = self.date_selector.get()
        user_id = self.profile.get("id", 1)

        self.cursor.execute('''
            SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fat)
            FROM food_log
            WHERE user_id=? AND date=?
        ''', (user_id, selected_date))
        result = self.cursor.fetchone()
        total_calories = result[0] or 0
        total_protein = result[1] or 0
        total_carbs = result[2] or 0
        total_fat = result[3] or 0

        self.total_calories_label.config(text=f"Tổng calo: {total_calories:.1f} kcal")
        self.total_protein_label.config(text=f"Protein: {total_protein:.1f} g")
        self.total_carbs_label.config(text=f"Carbs: {total_carbs:.1f} g")
        self.total_fat_label.config(text=f"Fat: {total_fat:.1f} g")

        meal_types = ["Bữa sáng", "Bữa trưa", "Bữa tối", "Bữa phụ sáng", "Bữa phụ chiều", "Bữa phụ tối"]
        row = 0

        for meal_type in meal_types:
            self.cursor.execute('''
                SELECT SUM(calories)
                FROM food_log
                WHERE user_id=? AND date=? AND (meal_type=? OR meal_type IS NULL)
            ''', (user_id, selected_date, meal_type))
            meal_calories = self.cursor.fetchone()[0] or 0

            meal_frame = ttk.LabelFrame(self.food_log_scrollable_frame, text=f"{meal_type} (Tổng calo: {meal_calories:.1f} kcal)", padding=10)
            meal_frame.grid(row=row, column=0, padx=5, pady=5, sticky="ew")
            row += 1

            tree = ttk.Treeview(meal_frame, columns=("food", "amount", "calories", "protein", "fat", "carbs"), show="headings")
            tree.heading("food", text="Món ăn")
            tree.heading("amount", text="Lượng (g)")
            tree.heading("calories", text="Calo (kcal)")
            tree.heading("protein", text="Protein (g)")
            tree.heading("fat", text="Fat (g)")
            tree.heading("carbs", text="Carbs (g)")
            tree.column("food", width=200)
            tree.column("amount", width=100)
            tree.column("calories", width=100)
            tree.column("protein", width=100)
            tree.column("fat", width=100)
            tree.column("carbs", width=100)
            tree.pack(fill="x", padx=5, pady=5)

            tree.bind('<Double-1>', lambda e, mt=meal_type: self.on_food_double_click(e, mt))
            self.meal_treeviews[meal_type] = tree

            self.cursor.execute(''' 
                SELECT food, amount, calories, protein, fat, carbs
                FROM food_log
                WHERE user_id=? AND date=? AND (meal_type=? OR meal_type IS NULL)
                ORDER BY id DESC
            ''', (user_id, selected_date, meal_type))
            for food_entry in self.cursor.fetchall():
                tree.insert('', 'end', values=food_entry)

    def check_calorie_balance(self):
        selected_date = self.date_selector.get()
        self.cursor.execute("SELECT SUM(calories) FROM food_log WHERE date=? AND user_id=?", (selected_date, self.profile.get("id", 1)))
        calories_in = self.cursor.fetchone()[0] or 0

        self.cursor.execute("SELECT SUM(calories) FROM workout_log WHERE date=? AND user_id=?", (selected_date, self.profile.get("id", 1)))
        calories_out = (self.cursor.fetchone()[0] or 0) + self.tdee

        surplus = calories_in - calories_out
        if surplus > 0:
            self.calorie_warning_label.config(
                text=f"⚠️ Bạn đang dư {surplus:.1f} calo hôm nay!", foreground="red"
            )
        else:
            self.calorie_warning_label.config(
                text=f"👍 Bạn đang trong mức kiểm soát (-{abs(surplus):.1f} calo)", foreground="green"
            )

    def log_weight_and_goal(self):
        try:
            weight_input = self.weight_update_entry.get()
            if weight_input:
                weight = float(weight_input)
                if weight <= 0:
                    raise ValueError("Cân nặng phải lớn hơn 0")
            else:
                weight = None

            weight_goal_input = self.weight_goal_entry.get()
            if weight_goal_input:
                weight_goal = float(weight_goal_input)
                if weight_goal <= 0:
                    raise ValueError("Mục tiêu cân nặng phải lớn hơn 0")
            else:
                weight_goal = None

            user_id = self.profile.get("id", 1)
            date = self.date_selector.get()

            if weight is not None:
                self.cursor.execute("INSERT INTO weight_log (user_id, date, weight) VALUES (?, ?, ?)",
                                    (user_id, date, weight))
                self.cursor.execute("UPDATE user_profile SET weight = ? WHERE id = ?",
                                    (weight, user_id))
                self.profile["weight"] = weight
                self.weight_var.set(weight)

            if weight_goal is not None:
                self.cursor.execute("UPDATE user_profile SET weight_goal = ? WHERE id = ?",
                                    (weight_goal, user_id))
                self.profile["weight_goal"] = weight_goal

            self.conn.commit()

            self.update_bmi_display()
            self.load_weight_history()
            self.update_weight_progress()
            self.load_workout_history()
            messagebox.showinfo("Thành công", "Cập nhật cân nặng và/hoặc mục tiêu thành công")
        except ValueError as ve:
            messagebox.showerror("Lỗi", str(ve))
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi lưu: {str(e)}")

    def load_weight_history(self):
        if not hasattr(self, 'weight_tree'):
            return
        for row in self.weight_tree.get_children():
            self.weight_tree.delete(row)

        self.cursor.execute("SELECT date, weight FROM weight_log WHERE user_id=? ORDER BY date DESC",
                            (self.profile.get("id", 1),))
        for row in self.cursor.fetchall():
            self.weight_tree.insert('', 'end', values=row)

    def update_weight_progress(self):
        if not hasattr(self, 'weight_progress_label') or not hasattr(self, 'weight_remaining_label'):
            return

        self.cursor.execute("SELECT weight FROM weight_log WHERE user_id=? ORDER BY date ASC LIMIT 1",
                            (self.profile.get("id", 1),))
        initial_weight_result = self.cursor.fetchone()
        initial_weight = initial_weight_result[0] if initial_weight_result else self.profile.get("weight", 0)

        self.cursor.execute("SELECT weight FROM weight_log WHERE user_id=? ORDER BY date DESC LIMIT 1",
                            (self.profile.get("id", 1),))
        current_weight_result = self.cursor.fetchone()
        current_weight = current_weight_result[0] if current_weight_result else self.profile.get("weight", 0)

        weight_goal = self.profile.get("weight_goal", 0)

        if initial_weight and current_weight:
            weight_lost = initial_weight - current_weight
            self.weight_progress_label.config(text=f"Tiến độ giảm cân: Đã giảm {weight_lost:.1f} kg")
        else:
            self.weight_progress_label.config(text="Tiến độ giảm cân: Chưa có dữ liệu")

        if weight_goal and current_weight:
            remaining = current_weight - weight_goal
            if remaining > 0:
                self.weight_remaining_label.config(text=f"Còn lại để đạt mục tiêu: {remaining:.1f} kg")
            elif remaining == 0:
                self.weight_remaining_label.config(text="Chúc mừng! Bạn đã đạt mục tiêu cân nặng!")
            else:
                self.weight_remaining_label.config(text=f"Đã vượt mục tiêu: {-remaining:.1f} kg")
        else:
            self.weight_remaining_label.config(text="Còn lại để đạt mục tiêu: Chưa có dữ liệu")

    def on_weight_double_click(self, event):
        item = self.weight_tree.selection()
        if not item:
            return
        item = item[0]
        values = self.weight_tree.item(item, "values")
        date = values[0]
        weight = values[1]
        if messagebox.askyesno("Xác nhận", f"Bạn có muốn xóa bản ghi cân nặng {weight} kg vào ngày {date}?"):
            self.delete_weight_entry(item)

    def delete_weight_entry(self, item_id):
        try:
            values = self.weight_tree.item(item_id, "values")
            date = values[0]
            weight = float(values[1])
            self.cursor.execute("DELETE FROM weight_log WHERE user_id=? AND date=? AND weight=?",
                                (self.profile.get("id", 1), date, weight))
            self.conn.commit()
            self.load_weight_history()
            self.update_weight_progress()
            self.update_bmi_display()
            self.load_workout_history()
            messagebox.showinfo("Thành công", f"Đã xóa bản ghi cân nặng {weight} kg")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xóa bản ghi: {str(e)}")

    def save_profile(self):
        try:
            name = self.name_var.get()
            age = self.age_var.get()
            gender = self.gender_var.get()
            weight = self.weight_var.get()
            height = self.height_var.get()
            goal = self.goal_var.get()

            conn = sqlite3.connect("D:/ki3nam4/thuctap/fitness.db")
            c = conn.cursor()
            c.execute("DELETE FROM user_profile")
            c.execute('''
                INSERT INTO user_profile (name, age, gender, weight, height, goal, weight_goal)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, age, gender, weight, height, goal, self.profile.get("weight_goal", None)))
            conn.commit()
            conn.close()

            self.profile = {
                "id": 1,
                "name": name,
                "age": age,
                "gender": gender,
                "weight": weight,
                "height": height,
                "goal": goal,
                "weight_goal": self.profile.get("weight_goal", None)
            }
            self.tdee = self.calculate_tdee(weight, height, age, "Ít vận động")

            self.update_bmi_display()
            self.load_workout_history()
            self.update_weight_progress()
            messagebox.showinfo("Thành công", "Đã lưu hồ sơ cá nhân")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Vui lòng nhập thông tin hợp lệ! Lỗi: {str(e)}")

    def load_profile(self):
        conn = sqlite3.connect("D:/ki3nam4/thuctap/fitness.db")
        c = conn.cursor()
        result = c.execute("SELECT name, age, gender, weight, height, goal, weight_goal FROM user_profile").fetchone()
        conn.close()

        if result:
            self.name_var.set(result[0])
            self.age_var.set(result[1])
            self.gender_var.set(result[2])
            self.weight_var.set(result[3])
            self.height_var.set(result[4])
            self.goal_var.set(result[5])
            self.profile = {
                "id": 1,
                "name": result[0],
                "age": result[1],
                "gender": result[2],
                "weight": result[3],
                "height": result[4],
                "goal": result[5],
                "weight_goal": result[6]
            }
            if result[6] is not None and hasattr(self, 'weight_goal_entry'):
                self.weight_goal_entry.delete(0, tk.END)
                self.weight_goal_entry.insert(0, result[6])
            self.tdee = self.calculate_tdee(result[3], result[4], result[1], "Ít vận động")
        else:
            self.profile = {"id": 1, "name": "", "age": 0, "gender": "", "weight": 0, "height": 0, "goal": "", "weight_goal": None}
            self.tdee = 0

    def start_water_reminder(self):
        def remind():
            while self.water_reminder_running:
                time.sleep(60 * 60)
                messagebox.showinfo("Nhắc nhở", "Uống nước đi bạn ơi!")
        threading.Thread(target=remind, daemon=True).start()

    def update_food_suggestions(self, event):
        current_time = time.time()
        if hasattr(self, 'last_food_suggest_time') and current_time - self.last_food_suggest_time < 0.3:
            return
        self.last_food_suggest_time = current_time

        if event.keysym in ('Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Return', 'Tab', 'Up', 'Down', 'Left', 'Right', 'BackSpace'):
            return

        if self.food_combo != self.root.focus_get():
            self.food_combo.focus_set()

        self.root.update()
        typed_text = self.food_combo.get().strip().lower()
        food_list = self.food_df["food_name"].to_list()
        suggestions = [food for food in food_list if typed_text in food.lower()] if typed_text else food_list
        self.food_combo['values'] = suggestions

    def update_exercise_suggestions(self, event):
        current_time = time.time()
        if hasattr(self, 'last_exercise_suggest_time') and current_time - self.last_exercise_suggest_time < 0.3:
            return
        self.last_exercise_suggest_time = current_time

        if event.keysym in ('Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Return', 'Tab', 'Up', 'Down', 'Left', 'Right', 'BackSpace'):
            return

        if self.exercise_combo != self.root.focus_get():
            self.exercise_combo.focus_set()

        self.root.update()
        typed_text = self.exercise_combo.get().strip().lower()
        exercise_list = self.exercise_df["exercise_name"].to_list()
        suggestions = [exercise for exercise in exercise_list if typed_text in exercise.lower().replace('_', ' ')] if typed_text else exercise_list
        self.exercise_combo['values'] = suggestions

    def on_date_selected(self, event):
        self.load_food_log()
        self.load_workout_history()

    def update_date_selector(self):
        self.cursor.execute("SELECT DISTINCT date FROM food_log WHERE user_id=? ORDER BY date DESC", (self.profile.get("id", 1),))
        dates = [row[0] for row in self.cursor.fetchall()]
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in dates:
            dates.insert(0, today)
        self.date_selector.set(today)
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Combobox) and widget.cget("textvariable") == self.date_selector:
                widget['values'] = dates

    def __del__(self):
        self.conn.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = FitnessApp(root)
    root.mainloop()