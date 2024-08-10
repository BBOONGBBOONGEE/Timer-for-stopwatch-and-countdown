import tkinter as tk
from tkinter import font as tkFont, colorchooser, filedialog
from PIL import Image, ImageDraw, ImageFont, ImageTk
from threading import Event
import time
import os
import winreg
from fontTools.ttLib import TTFont

def get_font_path_from_registry(font_name):
    """
    레지스트리에서 폰트 경로를 가져옵니다.
    """
    font_path = None
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts") as key:
            for i in range(0, winreg.QueryInfoKey(key)[1]):
                font, path = winreg.EnumValue(key, i)[:2]
                if font_name.lower() in font.lower():
                    font_path = path
                    break
    except Exception as e:
        print(f"Error reading registry: {e}")

    if font_path and not os.path.isabs(font_path):
        font_path = os.path.join(os.environ['WINDIR'], 'Fonts', font_path)

    return font_path

def get_korean_font_name(font_path):
    """
    폰트 파일에서 한글 이름을 가져옵니다.
    """
    try:
        font = TTFont(font_path)
        for record in font['name'].names:
            if record.nameID == 1 and record.platformID == 3 and record.langID == 1042:  # Windows, Korean
                return record.toUnicode()
    except Exception as e:
        return str(e)
    return None

def get_font_name_from_file(font_path):
    """
    주어진 폰트 파일에서 글꼴 이름을 가져옵니다.
    """
    try:
        pil_font = ImageFont.truetype(font_path)
        return pil_font.getname()[0]
    except Exception as e:
        return os.path.basename(font_path).split('.')[0]

def get_installed_fonts():
    """
    레지스트리와 사용자 폴더에서 설치된 폰트 목록을 가져옵니다.
    """
    fonts = []
    font_folder = os.path.join(os.getenv('LOCALAPPDATA'), 'Microsoft', 'Windows', 'Fonts')
    
    # 레지스트리에서 폰트 가져오기
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts") as key:
            for i in range(0, winreg.QueryInfoKey(key)[1]):
                font, path = winreg.EnumValue(key, i)[:2]
                if '@' not in font and path.lower().endswith(('.ttf', '.otf')):  # 세로쓰기 폰트 및 불가능한 포맷 제외
                    if not os.path.isabs(path):
                        path = os.path.join(os.environ['WINDIR'], 'Fonts', path)
                    font_name = get_korean_font_name(path) or get_font_name_from_file(path)
                    fonts.append((font_name, path))
    except Exception as e:
        print(f"Error reading registry: {e}")

    # 사용자 폴더에서 폰트 가져오기
    if os.path.exists(font_folder):
        for file in os.listdir(font_folder):
            if file.endswith(('.ttf', '.otf')):
                font_path = os.path.join(font_folder, file)
                font_name = get_korean_font_name(font_path) or get_font_name_from_file(font_path)
                fonts.append((font_name, font_path))

    # 한글 포함 글꼴 먼저 정렬
    korean_fonts = sorted([font for font in fonts if any('\uAC00' <= char <= '\uD7A3' for char in font[0])], key=lambda x: x[0])
    other_fonts = sorted([font for font in fonts if not any('\uAC00' <= char <= '\uD7A3' for char in font[0])], key=lambda x: x[0])

    return korean_fonts + other_fonts

class FontDialog(tk.Toplevel):
    def __init__(self, parent, font_list):
        super().__init__(parent)
        self.title("폰트 선택")
        self.font_list = font_list
        self.selected_font = None

        self.font_listbox = tk.Listbox(self, selectmode=tk.SINGLE, width=50, height=20)
        self.font_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = tk.Scrollbar(self, orient="vertical")
        self.scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.font_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.font_listbox.yview, width=20)

        for font, path in font_list:
            self.font_listbox.insert(tk.END, font)

        self.font_listbox.bind("<<ListboxSelect>>", self.show_font_preview)

        self.preview_frame = tk.Frame(self, width=300, height=100, bg="white")
        self.preview_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.preview_label = tk.Label(self.preview_frame, text="미리보기", font=("TkDefaultFont", 14), bg="lightgrey")
        self.preview_label.pack(side=tk.TOP, fill=tk.X)

        self.preview_canvas = tk.Canvas(self.preview_frame, width=300, height=50, bg="white")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)

        self.select_button = tk.Button(self, text="선택", command=self.select_font, width=20)
        self.select_button.pack(side=tk.RIGHT, padx=5)

        self.file_button = tk.Button(self, text="글꼴 파일로 불러오기", command=self.select_font_file, width=20)
        self.file_button.pack(side=tk.RIGHT, padx=5)

    def show_font_preview(self, event):
        selection = event.widget.curselection()
        if selection:
            index = selection[0]
            font_name, font_path = self.font_list[index]
            try:
                self.preview_canvas.delete("all")
                if font_path.lower().endswith(('.ttf', '.otf')):
                    pil_font = ImageFont.truetype(font_path, 20)
                    img = Image.new("RGBA", (300, 50), (255, 255, 255, 0))
                    draw = ImageDraw.Draw(img)
                    draw.text((10, 10), "ABCD 1234 ㄱㄴㄷㄹ", font=pil_font, fill="black")
                    self.preview_image = ImageTk.PhotoImage(img)
                    self.preview_canvas.create_image(0, 0, anchor="nw", image=self.preview_image)
                else:
                    self.preview_canvas.create_text(150, 25, text="미리보기 불가\n(하지만 적용 가능합니다.)", fill="red")
            except Exception as e:
                self.preview_canvas.delete("all")
                self.preview_canvas.create_text(150, 25, text="미리보기 불가\n(하지만 적용 가능합니다.)", fill="red")

    def select_font(self):
        selection = self.font_listbox.curselection()
        if selection:
            index = selection[0]
            font_name, font_path = self.font_list[index]
            if font_path.lower().endswith(('.ttf', '.otf')):
                self.selected_font = (font_name, font_path)
            else:
                self.selected_font = None
            self.destroy()

    def select_font_file(self):
        font_path = filedialog.askopenfilename(filetypes=[("Font files", "*.ttf *.otf")])
        if font_path:
            font_name = get_korean_font_name(font_path) or get_font_name_from_file(font_path)
            self.selected_font = (font_name, font_path)
            self.destroy()

class TimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("스탑워치 및 카운트다운용 타이머")
        self.timer_task = None  # timer_task 변수 정의

        self.current_image = None
        self.next_image = None

        # 초기 창 크기 설정
        self.default_width = 600
        self.default_height = 400
        self.root.geometry(f"{self.default_width}x{self.default_height}")
        self.root.minsize(self.default_width, self.default_height)

        # 타이머 변수들
        self.hours = 0
        self.minutes = 0
        self.seconds = 0
        self.is_running = False
        self.stop_event = Event()

        # 기본 폰트 크기 설정
        self.default_font_size = 48
        self.border_thickness = 2  # 기본 테두리 두께
        self.font_family = "arial"  # 기본 폰트 패밀리 (시스템 폰트 이름 사용)
        self.font_path = get_font_path_from_registry(self.font_family)  # 기본 폰트 파일 경로
        self.border_color = "white"
        self.fg_color = "black"
        self.bg_color = "#A9A9A9"
        self.button_color = "#D3D3D3"

        # 타이머 캔버스
        self.timer_canvas = tk.Canvas(root, bg=self.bg_color, highlightthickness=0)
        self.timer_canvas.grid(row=0, column=0, columnspan=3, pady=0, sticky="nsew")

        # 버튼 프레임
        button_frame = tk.Frame(root, bg=self.button_color)
        button_frame.grid(row=1, column=0, columnspan=3, pady=0, sticky="sew")

        # 폰트 크기 입력 필드 및 버튼
        self.font_size_entry = tk.Entry(button_frame, width=5, bg="white")
        self.font_size_entry.insert(0, str(self.default_font_size))
        self.set_font_size_btn = tk.Button(button_frame, text="폰트 크기 설정", command=self.set_font_size)

        # 테두리 두께 입력 필드 및 버튼
        self.border_thickness_entry = tk.Entry(button_frame, width=5, bg="white")
        self.border_thickness_entry.insert(0, str(self.border_thickness))
        self.set_border_thickness_btn = tk.Button(button_frame, text="테두리 두께 설정", command=self.set_border_thickness)

        # 폰트 선택 버튼
        self.select_font_btn = tk.Button(button_frame, text="폰트 선택", command=self.select_font)

        # 버튼들
        self.start_stopwatch_btn = tk.Button(button_frame, text="스탑워치 시작/정지", command=self.start_stopwatch)
        self.start_countdown_btn = tk.Button(button_frame, text="카운트다운 시작/정지", command=self.start_countdown)
        self.reset_btn = tk.Button(button_frame, text="타이머 초기화", command=self.reset_timer)

        # 시간 조정 버튼에 대한 command를 제거합니다.
        self.adjust_hour_up_btn = tk.Button(button_frame, text="시간 +1")
        self.adjust_hour_down_btn = tk.Button(button_frame, text="시간 -1")
        self.adjust_minute_up_btn = tk.Button(button_frame, text="분 +1")
        self.adjust_minute_down_btn = tk.Button(button_frame, text="분 -1")
        self.adjust_second_up_btn = tk.Button(button_frame, text="초 +1")
        self.adjust_second_down_btn = tk.Button(button_frame, text="초 -1")
        
        # 배경 색 변경 버튼 및 입력
        self.bg_color_btn = tk.Button(button_frame, text="배경 색 변경", command=self.change_bg_color)

        # 글씨 색 변경 버튼 및 입력
        self.fg_color_btn = tk.Button(button_frame, text="글씨 색 변경", command=self.change_fg_color)

        # 글씨 테두리 선택 및 설정
        self.border_color_btn = tk.Button(button_frame, text="테두리 색 변경", command=self.change_border_color)

        # 폰트 색 변경, 폰트 선택, 글씨 테두리 넣기를 3분할하여 추가
        self.font_color_btn = tk.Button(button_frame, text="폰트 색 변경", command=self.change_font_color)
        self.font_select_btn = tk.Button(button_frame, text="폰트 선택", command=self.select_font)

        # 글씨 테두리 활성화 체크박스
        self.border_var = tk.IntVar(value=1)
        self.border_check = tk.Checkbutton(button_frame, text=" 글씨 테두리 넣기", variable=self.border_var, command=self.toggle_border, bg=self.button_color, anchor="w", borderwidth=0, relief="flat")

        # 6행 1, 2열에 빈 레이블 추가
        self.empty_label1 = tk.Label(button_frame, bg=self.button_color, borderwidth=0, relief="flat")
        self.empty_label2 = tk.Label(button_frame, bg=self.button_color, borderwidth=0, relief="flat")
        # 체크박스 추가
        self.football_mode_var = tk.IntVar(value=0)  # 0 = 일반 모드, 1 = 축구용 타이머 모드
        self.football_mode_check = tk.Checkbutton(button_frame, text=" 축구용 타이머", variable=self.football_mode_var, command=self.toggle_football_mode, bg=self.button_color, anchor="w", borderwidth=0, relief="flat")

        # 버튼 배치
        self.start_stopwatch_btn.grid(row=0, column=0, sticky="ew")
        self.start_countdown_btn.grid(row=0, column=1, sticky="ew")
        self.reset_btn.grid(row=0, column=2, sticky="ew")
        
        self.adjust_hour_up_btn.grid(row=1, column=0, sticky="ew")
        self.adjust_minute_up_btn.grid(row=1, column=1, sticky="ew")
        self.adjust_second_up_btn.grid(row=1, column=2, sticky="ew")

        self.adjust_hour_down_btn.grid(row=2, column=0, sticky="ew")
        self.adjust_minute_down_btn.grid(row=2, column=1, sticky="ew")
        self.adjust_second_down_btn.grid(row=2, column=2, sticky="ew")

        self.bg_color_btn.grid(row=3, column=0, sticky="ew")
        self.set_font_size_btn.grid(row=3, column=1, sticky="ew")
        self.font_size_entry.grid(row=3, column=2, padx=0, pady=0, sticky="ew")

        self.border_color_btn.grid(row=4, column=0, sticky="ew")
        self.set_border_thickness_btn.grid(row=4, column=1, sticky="ew")
        self.border_thickness_entry.grid(row=4, column=2, padx=0, pady=0, sticky="ew")

        self.font_color_btn.grid(row=5, column=0, sticky="ew")
        self.font_select_btn.grid(row=5, column=1, sticky="ew")
        self.border_check.grid(row=5, column=2, sticky="ew",)

        self.empty_label1.grid(row=6, column=0, sticky="news")
        self.empty_label2.grid(row=6, column=1, sticky="news")
        self.football_mode_check.grid(row=6, column=2, sticky="news")
        
        button_frame.grid_rowconfigure(0, weight=1)
        button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # 창 크기 고정 비율 설정
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.update_idletasks()
        self.root.geometry(f"{self.default_width}x{self.default_height}")

        # 버튼 누르기 이벤트
        self.button_press_time = 0
        self.button_hold_task = None

        # bind를 사용하여 클릭 및 길게 누르기 동작을 처리합니다.
        self.adjust_hour_up_btn.bind("<ButtonPress-1>", lambda event, unit='hours', amount=1: self.start_adjust_time(event, amount, unit))
        self.adjust_hour_down_btn.bind("<ButtonPress-1>", lambda event, unit='hours', amount=-1: self.start_adjust_time(event, amount, unit))
        self.adjust_minute_up_btn.bind("<ButtonPress-1>", lambda event, unit='minutes', amount=1: self.start_adjust_time(event, amount, unit))
        self.adjust_minute_down_btn.bind("<ButtonPress-1>", lambda event, unit='minutes', amount=-1: self.start_adjust_time(event, amount, unit))
        self.adjust_second_up_btn.bind("<ButtonPress-1>", lambda event, unit='seconds', amount=1: self.start_adjust_time(event, amount, unit))
        self.adjust_second_down_btn.bind("<ButtonPress-1>", lambda event, unit='seconds', amount=-1: self.start_adjust_time(event, amount, unit))
        
        # 폰트 설정
        self.custom_font = tkFont.Font(family=self.font_family, size=self.default_font_size, weight='bold')
        self.update_display()

        # 프로그램 시작 시 폰트 크기 설정 액션 한 번 호출
        self.root.after(100, self.set_font_size)

        # 프로그램 종료 시 이벤트 처리
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def select_font(self):
        font_list = get_installed_fonts()
        font_dialog = FontDialog(self.root, font_list)
        self.root.wait_window(font_dialog)
        if font_dialog.selected_font:
            font_name, font_path = font_dialog.selected_font
            self.font_family = font_name
            self.font_path = font_path
            # print(f"Selected Font: {self.font_family}")
            # print(f"Font Path: {self.font_path}")
            self.custom_font = tkFont.Font(family=self.font_family, size=self.default_font_size, weight='bold')
            self.update_display()
            
    # 폰트 색 변경 기능 추가
    def change_font_color(self):
        color = colorchooser.askcolor(title="배경 색 선택")
        if color:
            self.fg_color = color[1]
            self.update_display()

    def start_adjust_time(self, event, amount, unit):
        self.button_press_time = time.time()
        self.adjust_amount = amount
        self.adjust_unit = unit
        self.is_holding = False
        self.button_hold_task = self.root.after(500, self.trigger_hold_adjust)
        event.widget.bind("<ButtonRelease-1>", self.stop_adjust_time)

    def trigger_hold_adjust(self):
        self.is_holding = True
        self.hold_adjust_time()

    def hold_adjust_time(self):
        if not self.is_holding:
            return

        elapsed_time = time.time() - self.button_press_time

        if elapsed_time >= 4:
            amount = self.adjust_amount * 5  # 4초 이상일 때 5씩 증감
        elif elapsed_time >= 2:
            amount = self.adjust_amount * 2  # 2초 이상일 때 2씩 증감
        else:
            amount = self.adjust_amount  # 2초 미만일 때 1씩 증감

        self.adjust_time(amount, self.adjust_unit)
        self.button_hold_task = self.root.after(100, self.hold_adjust_time)

    def stop_adjust_time(self, event):
        # 0.5초 이상 눌렀다면 추가 증감을 하지 않음
        if not self.is_holding and time.time() - self.button_press_time < 0.5:
            self.adjust_time(self.adjust_amount, self.adjust_unit)

        self.is_holding = False

        if self.button_hold_task:
            self.root.after_cancel(self.button_hold_task)
            self.button_hold_task = None

        event.widget.unbind("<ButtonRelease-1>")

    def set_font_size(self):
        try:
            new_size = int(self.font_size_entry.get())
            self.default_font_size = new_size
            self.custom_font = tkFont.Font(family=self.font_family, size=self.default_font_size, weight='bold')
            self.update_display()
        except ValueError:
            pass  # 잘못된 값이 입력된 경우 무시

    def change_bg_color(self):
        color_code = colorchooser.askcolor(title="배경 색 선택")
        if color_code:
            self.bg_color = color_code[1]
            self.root.configure(bg=self.bg_color)
            self.timer_canvas.configure(bg=self.bg_color)
            self.font_size_entry.configure(bg="white")
            self.border_thickness_entry.configure(bg="white")
            # self.border_check.configure(bg=self.bg_color)
            # self.football_mode_check.configure(bg=self.bg_color)  # 축구모드 체크박스의 배경색 변경
            # self.empty_label1.configure(bg=self.bg_color)
            # self.empty_label2.configure(bg=self.bg_color)
            self.update_display()

    def change_fg_color(self):
        color_code = colorchooser.askcolor(title="글씨 색 선택")
        if color_code:
            self.fg_color = color_code[1]
            self.update_display()

    def change_border_color(self):
        color_code = colorchooser.askcolor(title="테두리 색 선택")
        if color_code:
            self.border_color = color_code[1]
            self.update_display()

    def set_border_thickness(self):
        try:
            self.border_thickness = int(self.border_thickness_entry.get())
            self.update_display()
        except ValueError:
            pass  # 잘못된 값이 입력된 경우 무시

    def toggle_border(self):
        self.update_display()

    def validate_time(self, input_value, max_value):
        num = int(input_value) if input_value.isdigit() else 0
        return max(0, min(num, max_value))

    def update_display(self):
        # 타이머 캔버스 초기화
        self.timer_canvas.delete("all")
        
        if self.football_mode_var.get() == 1:
            # 축구 모드일 때는 시간 부분을 제외하고, 60분 이상으로 표시
            total_minutes = self.hours * 60 + self.minutes
            time_text = f"{total_minutes:02}:{self.seconds:02}"
        else:
            time_text = f"{self.hours:02}:{self.minutes:02}:{self.seconds:02}"
        
        # 현재 이미지를 표시
        if self.border_var.get():
            self.draw_text_with_outline(self.timer_canvas, self.timer_canvas.winfo_width()//2, self.timer_canvas.winfo_height()//2, time_text, self.font_path, self.default_font_size, self.fg_color, self.border_color, self.border_thickness)
        else:
            self.timer_canvas.create_text(self.timer_canvas.winfo_width()//2, self.timer_canvas.winfo_height()//2, text=time_text, font=self.custom_font, fill=self.fg_color, anchor="center")
        
        # 다음 이미지를 미리 생성하여 저장
        self.next_time_text = self.calculate_next_time()
        self.next_image = self.create_image_for_next_time(self.next_time_text)

    def draw_text_with_outline(self, canvas, x, y, text, font_path, font_size, fill, outline, thickness):
        # 외곽선을 그리기 위해 Pillow 사용
        img_width, img_height = 800, 200  # 이미지의 크기 조정
        img = Image.new("RGBA", (img_width, img_height), (255, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        if not font_path:
            font_path = get_font_path_from_registry(self.font_family)
        
        try:
            pil_font = ImageFont.truetype(font_path, font_size)
        except IOError:
            pil_font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=pil_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (img_width - text_width) // 2
        text_y = (img_height - text_height) // 2

        # 텍스트 중심에 외곽선을 그리기 위해 네 방향으로 그린다.
        for adj in range(-thickness, thickness+1):
            draw.text((text_x+adj, text_y), text, font=pil_font, fill=outline)
            draw.text((text_x, text_y+adj), text, font=pil_font, fill=outline)

        # 중심점에 텍스트 그리기
        draw.text((text_x, text_y), text, font=pil_font, fill=fill)

        # 이미지 변환
        self.tk_image = ImageTk.PhotoImage(img)
        canvas.create_image(x, y, image=self.tk_image, anchor="center")

    def create_image_for_next_time(self, next_time_text):
        # 다음 텍스트 이미지를 생성하여 반환
        img_width, img_height = 800, 200  # 이미지의 크기 조정
        img = Image.new("RGBA", (img_width, img_height), (255, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        pil_font = ImageFont.truetype(self.font_path, self.default_font_size)
        bbox = draw.textbbox((0, 0), next_time_text, font=pil_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (img_width - text_width) // 2
        text_y = (img_height - text_height) // 2

        for adj in range(-self.border_thickness, self.border_thickness+1):
            draw.text((text_x+adj, text_y), next_time_text, font=pil_font, fill=self.border_color)
            draw.text((text_x, text_y+adj), next_time_text, font=pil_font, fill=self.border_color)

        draw.text((text_x, text_y), next_time_text, font=pil_font, fill=self.fg_color)
        return ImageTk.PhotoImage(img)

    def calculate_next_time(self):
        # 현재 시간에서 다음 시간을 계산하여 텍스트로 반환
        next_seconds = (self.seconds + 1) % 60
        next_minutes = self.minutes + (1 if next_seconds == 0 else 0)
        next_minutes %= 60
        next_hours = self.hours + (1 if next_minutes == 0 and next_seconds == 0 else 0)

        if self.football_mode_var.get() == 1:
            return f"{next_minutes:02}:{next_seconds:02}"
        else:
            next_minutes %= 60
            next_hours = self.hours + (1 if next_minutes == 0 and next_seconds == 0 else 0)
        return f"{next_hours:02}:{next_minutes:02}:{next_seconds:02}"

    def stopwatch(self):
        self.seconds += 1
        if self.seconds >= 60:
            self.minutes += 1
            self.seconds = 0
        if self.minutes >= 60:
            if self.football_mode_var.get() == 0:
                self.hours += 1
                self.minutes = 0
        self.update_display()

    def countdown(self):
        if self.hours == 0 and self.minutes == 0 and self.seconds == 0:
            self.stop_timer()  # 타이머를 완전히 멈추도록 설정
            self.blink_timer()  # 깜빡임 시작
            return
        if self.seconds > 0:
            self.seconds -= 1
        elif self.minutes > 0:
            self.minutes -= 1
            self.seconds = 59
        elif self.hours > 0:
            if self.football_mode_var.get() == 0:
                self.hours -= 1
                self.minutes = 59
                self.seconds = 59
        self.update_display()

    # 타이머 동작 버튼을 새로 누르는 순간에 타이머에 떠있던 시간을 기준으로 시작하도록 수정
    def start_stopwatch(self):
        if self.is_running:
            self.stop_timer()  # 기존 타이머 작업이 있으면 중지
        else:
            # 스톱워치 시작
            self.is_running = True
            self.update_display()  # 현재 시간 이미지를 표시하고, 다음 시간 이미지 생성
            self.timer_task = self.root.after(1000, self.update_stopwatch)  # 1초 대기 후 타이머 시작

    def start_countdown(self):
        if self.is_running:
            self.stop_timer()  # 기존 타이머 작업이 있으면 중지
        else:
            # 카운트다운 시작
            self.is_running = True
            self.update_display()  # 현재 시간 이미지를 표시하고, 다음 시간 이미지 생성
            self.timer_task = self.root.after(1000, self.update_countdown)  # 1초 대기 후 타이머 시작

    def stop_timer(self):
        if self.timer_task:  # 기존 타이머 작업이 있으면 중지
            self.root.after_cancel(self.timer_task)
            self.timer_task = None
        self.is_running = False

    def reset_timer(self):
        self.stop_timer()  # 타이머 중지

        # 타이머 시간 초기화
        self.hours = 0
        self.minutes = 0
        self.seconds = 0
        self.update_display()


    # 타이머 일시정지 및 시작 기능 추가
    def update_stopwatch(self):
        if self.is_running:
            self.stopwatch()
            self.timer_task = self.root.after(1000, self.update_stopwatch)  # 1초 대기 후 다음 시간 갱신

    def update_countdown(self):
        if self.is_running:
            self.countdown()
            if self.is_running:  # 카운트다운이 종료되지 않았으면 계속 진행
                self.timer_task = self.root.after(1000, self.update_countdown)

    def adjust_time(self, amount, unit):
        if unit == 'hours':
            if self.football_mode_var.get() == 1:  # 축구 타이머 모드
                return  # 시간 증감 무효화
            self.hours = max(0, self.hours + amount)  # 음수로 내려가지 않도록 수정
        elif unit == 'minutes':
            if self.football_mode_var.get() == 1:  # 축구 타이머 모드
                self.minutes += amount  # 분을 계속 증가시키도록
                if self.minutes < 0:
                    self.minutes = 0  # 분이 음수가 되지 않도록
            else:
                self.minutes += amount
                if self.minutes >= 60:
                    self.minutes -= 60
                    self.hours = max(0, self.hours + 1)
                elif self.minutes < 0:
                    if self.hours > 0:
                        self.minutes += 60
                        self.hours = max(0, self.hours - 1)
                    else:
                        self.minutes = 0  # 음수일 때 0분으로 돌려줌
        elif unit == 'seconds':
            self.seconds += amount
            if self.seconds >= 60:
                self.seconds -= 60
                self.adjust_time(1, 'minutes')
            elif self.seconds < 0:
                if self.minutes > 0 or self.hours > 0:
                    self.seconds += 60
                    self.adjust_time(-1, 'minutes')
                else:
                    self.seconds = 0  # 음수일 때 0초로 돌려줌
        self.update_display()

    # 카운트다운이 0초가 되었을 때 깜빡이게 설정
    def blink_timer(self, blink_count=5):
        if blink_count > 0:
            # 전체 타이머 캔버스를 배경색으로 덮어 깜빡이게 하는 방법
            self.timer_canvas.create_rectangle(0, 0, self.timer_canvas.winfo_width(), self.timer_canvas.winfo_height(), fill=self.bg_color, outline=self.bg_color)
            
            # 0.5초 후 타이머 다시 표시
            self.root.after(500, self.update_display)

            # 1초 후에 다음 깜빡임을 처리
            self.root.after(1000, self.blink_timer, blink_count - 1)
        else:
            # 깜빡임이 끝나면 타이머를 다시 정상 상태로 표시
            self.update_display()

    def toggle_football_mode(self):
        if self.football_mode_var.get() == 1:
            self.hours = 0  # 축구 모드에서는 시간 부분을 없애기 위해 시간값을 0으로 설정
        self.reset_timer()
        self.update_display()

    def on_closing(self):
        # 프로그램이 종료될 때 타이머 스레드를 정상적으로 종료
        self.stop_event.set()
        self.root.destroy()

root = tk.Tk()
app = TimerApp(root)
root.configure(bg="#A9A9A9")  # 배경색 설정
root.mainloop()
