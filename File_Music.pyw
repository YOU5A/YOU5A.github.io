"""
媒体文件管理工具 - 修复版
修复了标签编辑问题，添加了批量修改功能，优化了界面颜色
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import os
import sys
import traceback
from pathlib import Path
from mutagen import File
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3  # 只导入MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC  # 添加TDRC用于年份
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis
from PIL import Image, ImageTk
import io

# ==================== 常量定义 ====================
SUPPORTED_FORMATS = ['.mp3', '.flac', '.ogg', '.m4a', '.wav', '.opus']
COVER_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
COVER_MAX_SIZE = 800
DEFAULT_COVER_SIZE = (200, 200)

# ==================== 辅助工具类 ====================
class FileUtils:
    """文件操作工具类"""
    
    @staticmethod
    def sanitize_filename(name):
        """清理文件名，移除非法字符"""
        if not name:
            return ""
        
        illegal_chars = '/\\:*?"<>|\n\r'
        for char in illegal_chars:
            name = name.replace(char, '')
        
        name = ' '.join(name.split())
        return name[:100].strip()
    
    @staticmethod
    def get_files_by_criteria(folder_path, extensions=None, recursive=True):
        """根据条件获取文件列表"""
        if not os.path.exists(folder_path):
            return []
        
        if extensions is None:
            extensions = []
        
        files = []
        if recursive:
            for root_dir, _, filenames in os.walk(folder_path):
                for filename in filenames:
                    if any(filename.lower().endswith(ext) for ext in extensions):
                        files.append(os.path.join(root_dir, filename))
        else:
            for entry in os.scandir(folder_path):
                if entry.is_file() and any(entry.name.lower().endswith(ext) for ext in extensions):
                    files.append(entry.path)
        
        return files
    
    @staticmethod
    def sort_files(files, method="modification"):
        """排序文件"""
        if method == "modification":
            return sorted(files, key=lambda x: os.path.getmtime(x))
        elif method == "filename":
            return sorted(files, key=lambda x: os.path.basename(x).lower())
        else:
            return files

# ==================== 音频文件处理器 ====================
class AudioFileProcessor:
    """音频文件处理类"""
    
    @staticmethod
    def load_audio_file(file_path):
        """加载音频文件"""
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == '.mp3':
                # 对于MP3文件，使用ID3标签
                try:
                    audio = MP3(file_path, ID3=ID3)
                except:
                    audio = MP3(file_path)
            elif ext == '.flac':
                audio = FLAC(file_path)
            elif ext in ['.ogg', '.opus']:
                audio = OggVorbis(file_path)
            elif ext in ['.m4a', '.mp4']:
                audio = MP4(file_path)
            elif ext == '.wav':
                audio = File(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {ext}")
            
            return audio
        except Exception as e:
            raise Exception(f"加载文件失败: {str(e)}")
    
    @staticmethod
    def get_metadata(file_path):
        """获取音频元数据"""
        try:
            audio = AudioFileProcessor.load_audio_file(file_path)
            ext = os.path.splitext(file_path)[1].lower()
            
            metadata = {"title": "", "artist": "", "album": "", "year": "", "genre": "", "track": "", "cover": None}
            
            if ext == '.mp3':
                # MP3文件使用ID3标签
                if hasattr(audio, 'tags') and audio.tags:
                    if 'TIT2' in audio.tags:
                        metadata["title"] = audio.tags['TIT2'].text[0]
                    if 'TPE1' in audio.tags:
                        metadata["artist"] = audio.tags['TPE1'].text[0]
                    if 'TALB' in audio.tags:
                        metadata["album"] = audio.tags['TALB'].text[0]
                    if 'TDRC' in audio.tags:
                        metadata["year"] = str(audio.tags['TDRC'].text[0])
                    if 'TCON' in audio.tags:
                        metadata["genre"] = audio.tags['TCON'].text[0]
                    if 'TRCK' in audio.tags:
                        metadata["track"] = audio.tags['TRCK'].text[0]
            elif ext == '.flac':
                metadata["title"] = audio.get('title', [''])[0]
                metadata["artist"] = audio.get('artist', [''])[0]
                metadata["album"] = audio.get('album', [''])[0]
                metadata["year"] = audio.get('date', [''])[0]
                metadata["genre"] = audio.get('genre', [''])[0]
                metadata["track"] = audio.get('tracknumber', [''])[0]
            elif ext in ['.ogg', '.opus']:
                metadata["title"] = audio.get('title', [''])[0]
                metadata["artist"] = audio.get('artist', [''])[0]
                metadata["album"] = audio.get('album', [''])[0]
                metadata["year"] = audio.get('date', [''])[0]
                metadata["genre"] = audio.get('genre', [''])[0]
                metadata["track"] = audio.get('tracknumber', [''])[0]
            elif ext in ['.m4a', '.mp4']:
                metadata["title"] = audio.get('\xa9nam', [''])[0]
                metadata["artist"] = audio.get('\xa9ART', [''])[0]
                metadata["album"] = audio.get('\xa9alb', [''])[0]
                metadata["year"] = audio.get('\xa9day', [''])[0]
                metadata["genre"] = audio.get('\xa9gen', [''])[0]
                metadata["track"] = audio.get('trkn', [(0, 0)])[0][0] if audio.get('trkn') else ''
            elif ext == '.wav':
                if hasattr(audio, 'tags') and audio.tags:
                    metadata["title"] = audio.tags.get('title', [''])[0]
                    metadata["artist"] = audio.tags.get('artist', [''])[0]
                    metadata["album"] = audio.tags.get('album', [''])[0]
                    metadata["year"] = audio.tags.get('year', [''])[0]
                    metadata["genre"] = audio.tags.get('genre', [''])[0]
                    metadata["track"] = audio.tags.get('track', [''])[0]
            
            return metadata
        except Exception as e:
            print(f"获取元数据失败 {file_path}: {e}")
            return {"title": "", "artist": "", "album": "", "year": "", "genre": "", "track": "", "cover": None}
    
    @staticmethod
    def extract_cover(file_path):
        """提取音频文件中的封面"""
        try:
            audio = AudioFileProcessor.load_audio_file(file_path)
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.mp3':
                if hasattr(audio, 'tags') and audio.tags:
                    for key in audio.tags.keys():
                        if key.startswith('APIC'):
                            return audio.tags[key].data
            elif ext == '.flac':
                if hasattr(audio, 'pictures') and audio.pictures:
                    return audio.pictures[0].data
            elif ext in ['.ogg', '.opus']:
                if 'metadata_block_picture' in audio:
                    return audio['metadata_block_picture'][0]
            elif ext in ['.m4a', '.mp4']:
                if 'covr' in audio:
                    return audio['covr'][0]
            
            return None
        except Exception:
            return None
    
    @staticmethod
    def save_tags(file_path, title="", artist="", album="", year="", genre="", track="", preserve_title=False):
        """保存标签到音频文件"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if preserve_title:
                # 获取原文件的标题
                metadata = AudioFileProcessor.get_metadata(file_path)
                title = metadata["title"]
            
            if ext == '.mp3':
                audio = AudioFileProcessor.load_audio_file(file_path)
                
                # 确保有标签
                if not hasattr(audio, 'tags') or audio.tags is None:
                    audio.add_tags()
                
                if title:
                    audio.tags.add(TIT2(encoding=3, text=title))
                if artist:
                    audio.tags.add(TPE1(encoding=3, text=artist))
                if album:
                    audio.tags.add(TALB(encoding=3, text=album))
                if year:
                    audio.tags.add(TDRC(encoding=3, text=year))
                
                audio.save()
                
            elif ext == '.flac':
                audio = FLAC(file_path)
                if title:
                    audio['title'] = [title]
                if artist:
                    audio['artist'] = [artist]
                if album:
                    audio['album'] = [album]
                if year:
                    audio['date'] = [year]
                if genre:
                    audio['genre'] = [genre]
                if track:
                    audio['tracknumber'] = [track]
                audio.save()
                
            elif ext in ['.ogg', '.opus']:
                audio = OggVorbis(file_path)
                if title:
                    audio['title'] = [title]
                if artist:
                    audio['artist'] = [artist]
                if album:
                    audio['album'] = [album]
                if year:
                    audio['date'] = [year]
                if genre:
                    audio['genre'] = [genre]
                if track:
                    audio['tracknumber'] = [track]
                audio.save()
                
            elif ext in ['.m4a', '.mp4']:
                audio = MP4(file_path)
                if title:
                    audio['\xa9nam'] = [title]
                if artist:
                    audio['\xa9ART'] = [artist]
                if album:
                    audio['\xa9alb'] = [album]
                if year:
                    audio['\xa9day'] = [year]
                if genre:
                    audio['\xa9gen'] = [genre]
                if track:
                    audio['trkn'] = [(int(track), 0)]
                audio.save()
                
            return True
        except Exception as e:
            raise Exception(f"保存标签失败: {str(e)}")
    
    @staticmethod
    def apply_cover(file_path, cover_data, mime_type="image/jpeg"):
        """应用封面到音频文件"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.mp3':
                audio = AudioFileProcessor.load_audio_file(file_path)
                
                # 确保有标签
                if not hasattr(audio, 'tags') or audio.tags is None:
                    audio.add_tags()
                
                # 移除现有封面
                if hasattr(audio, 'tags') and audio.tags:
                    for key in list(audio.tags.keys()):
                        if key.startswith('APIC'):
                            del audio.tags[key]
                
                # 添加新封面
                audio.tags.add(APIC(
                    encoding=3,
                    mime=mime_type,
                    type=3,
                    desc='Cover',
                    data=cover_data
                ))
                audio.save()
                
            elif ext == '.flac':
                audio = FLAC(file_path)
                audio.clear_pictures()
                pic = Picture()
                pic.data = cover_data
                pic.type = 3
                pic.mime = mime_type
                pic.desc = 'Cover'
                audio.add_picture(pic)
                audio.save()
                
            elif ext in ['.ogg', '.opus']:
                audio = OggVorbis(file_path)
                pic = Picture()
                pic.data = cover_data
                pic.type = 3
                pic.mime = mime_type
                pic.desc = 'Cover'
                audio['metadata_block_picture'] = [pic.write()]
                audio.save()
                
            elif ext in ['.m4a', '.mp4']:
                audio = MP4(file_path)
                cover_format = MP4Cover.FORMAT_PNG if mime_type == 'image/png' else MP4Cover.FORMAT_JPEG
                audio['covr'] = [MP4Cover(cover_data, cover_format)]
                audio.save()
                
            return True
        except Exception as e:
            raise Exception(f"应用封面失败: {str(e)}")
    
    @staticmethod
    def remove_cover(file_path):
        """删除音频文件的封面"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.mp3':
                audio = AudioFileProcessor.load_audio_file(file_path)
                if hasattr(audio, 'tags') and audio.tags:
                    for key in list(audio.tags.keys()):
                        if key.startswith('APIC'):
                            del audio.tags[key]
                    audio.save()
                    
            elif ext == '.flac':
                audio = FLAC(file_path)
                audio.clear_pictures()
                audio.save()
                
            elif ext in ['.ogg', '.opus']:
                audio = OggVorbis(file_path)
                if 'metadata_block_picture' in audio:
                    del audio['metadata_block_picture']
                audio.save()
                
            elif ext in ['.m4a', '.mp4']:
                audio = MP4(file_path)
                if 'covr' in audio:
                    del audio['covr']
                audio.save()
                
            return True
        except Exception as e:
            raise Exception(f"删除封面失败: {str(e)}")

# ==================== UI组件 ====================
class TagEditorTab:
    """音乐标签编辑器标签页"""
    
    def __init__(self, parent):
            self.parent = parent
            self.current_folder = ""
            self.current_file = None
            self.selected_cover = None

            # Scroll container refs (for better resizing + mousewheel scroll)
            self.canvas = None
            self.scrollable_frame = None
            self.canvas_window = None
            self._mousewheel_installed = False

            self.setup_ui()
            self._install_mousewheel_support()
    
    def setup_ui(self):
            """设置UI界面"""
            # 容器 + 滚动（解决小屏幕显示不全 + 鼠标滚轮只能在滑块上滚的问题）
            main_container = ttk.Frame(self.parent)
            main_container.pack(fill=tk.BOTH, expand=True)

            self.canvas = tk.Canvas(main_container, highlightthickness=0)
            scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=self.canvas.yview)
            self.canvas.configure(yscrollcommand=scrollbar.set)

            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # 可滚动内容区
            self.scrollable_frame = ttk.Frame(self.canvas)
            self.scrollable_frame.bind(
                "<Configure>",
                lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            )

            self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
            self.canvas.bind("<Configure>", self._on_canvas_configure)

            # 主布局：左右两栏
            main_frame = ttk.Frame(self.scrollable_frame, padding=10)
            main_frame.grid(row=0, column=0, sticky="nsew")
            self.scrollable_frame.columnconfigure(0, weight=1)

            left_panel = ttk.Frame(main_frame)
            right_panel = ttk.Frame(main_frame)

            left_panel.grid(row=0, column=0, sticky="ns", padx=(0, 10))
            right_panel.grid(row=0, column=1, sticky="nsew")

            main_frame.columnconfigure(1, weight=1)
            main_frame.rowconfigure(0, weight=1)

            # -------------------- 左侧：控制区 --------------------
            folder_frame = ttk.LabelFrame(left_panel, text="文件夹操作", padding=12)
            folder_frame.pack(fill=tk.X, pady=(0, 10))

            folder_frame.columnconfigure(1, weight=1)

            ttk.Label(folder_frame, text="音乐文件夹:").grid(row=0, column=0, sticky=tk.W, pady=5)
            self.folder_entry = ttk.Entry(folder_frame)
            self.folder_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
            ttk.Button(folder_frame, text="浏览", command=self.browse_folder, width=8).grid(row=0, column=2, padx=2)

            ttk.Label(folder_frame, text="支持格式:").grid(row=1, column=0, sticky=tk.W, pady=2)
            ttk.Label(folder_frame, text="MP3, FLAC, OGG, M4A, WAV, OPUS").grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=2)

            ttk.Button(folder_frame, text="扫描文件夹", command=self.scan_folder).grid(row=2, column=0, columnspan=3, pady=(10, 0), sticky="ew")

            # 标签编辑区域
            tag_frame = ttk.LabelFrame(left_panel, text="标签编辑", padding=12)
            tag_frame.pack(fill=tk.X, pady=(0, 10))

            tag_frame.columnconfigure(1, weight=1)

            ttk.Label(tag_frame, text="标题:").grid(row=0, column=0, sticky=tk.W, pady=5)
            self.title_entry = ttk.Entry(tag_frame)
            self.title_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

            ttk.Label(tag_frame, text="艺术家:").grid(row=1, column=0, sticky=tk.W, pady=5)
            self.artist_entry = ttk.Entry(tag_frame)
            self.artist_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

            ttk.Label(tag_frame, text="专辑:").grid(row=2, column=0, sticky=tk.W, pady=5)
            self.album_entry = ttk.Entry(tag_frame)
            self.album_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

            ttk.Label(tag_frame, text="年份:").grid(row=3, column=0, sticky=tk.W, pady=5)
            self.year_entry = ttk.Entry(tag_frame)
            self.year_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=5)

            ttk.Label(tag_frame, text="流派:").grid(row=4, column=0, sticky=tk.W, pady=5)
            self.genre_entry = ttk.Entry(tag_frame)
            self.genre_entry.grid(row=4, column=1, sticky="ew", padx=5, pady=5)

            button_frame = ttk.Frame(tag_frame)
            button_frame.grid(row=5, column=0, columnspan=2, pady=(12, 0), sticky="ew")
            ttk.Button(button_frame, text="保存标签", command=self.save_tags).pack(side=tk.LEFT, padx=2)
            ttk.Button(button_frame, text="清除标签", command=self.clear_tags).pack(side=tk.LEFT, padx=2)
            ttk.Button(button_frame, text="应用到所有", command=self.apply_tags_all).pack(side=tk.LEFT, padx=2)

            # 重命名区域
            rename_frame = ttk.LabelFrame(left_panel, text="文件重命名", padding=12)
            rename_frame.pack(fill=tk.X, pady=(0, 10))

            ttk.Button(rename_frame, text="重命名选中文件", command=self.rename_selected).pack(fill=tk.X, pady=5)
            ttk.Button(rename_frame, text="重命名所有文件", command=self.rename_all).pack(fill=tk.X, pady=5)

            # 封面操作区域
            cover_frame = ttk.LabelFrame(left_panel, text="封面操作", padding=12)
            cover_frame.pack(fill=tk.X, pady=(0, 10))

            ttk.Button(cover_frame, text="选择封面图片", command=self.select_cover).pack(fill=tk.X, pady=5)

            cover_button_frame = ttk.Frame(cover_frame)
            cover_button_frame.pack(fill=tk.X, pady=5)

            ttk.Button(cover_button_frame, text="应用到选中", command=self.apply_cover_selected).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
            ttk.Button(cover_button_frame, text="应用到所有", command=self.apply_cover_all).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

            remove_frame = ttk.Frame(cover_frame)
            remove_frame.pack(fill=tk.X, pady=5)

            ttk.Button(remove_frame, text="删除选中封面", command=self.remove_cover_selected).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
            ttk.Button(remove_frame, text="删除所有封面", command=self.remove_cover_all).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

            # 状态显示区域
            status_frame = ttk.LabelFrame(left_panel, text="操作日志", padding=10)
            status_frame.pack(fill=tk.BOTH, expand=True)

            self.status_text = scrolledtext.ScrolledText(status_frame, height=8, wrap=tk.WORD)
            self.status_text.pack(fill=tk.BOTH, expand=True)
            self.log_message("就绪")

            # -------------------- 右侧：预览区 --------------------
            list_frame = ttk.LabelFrame(right_panel, text="文件列表", padding=10)
            list_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
            right_panel.columnconfigure(0, weight=1)
            right_panel.rowconfigure(0, weight=1)

            list_container = ttk.Frame(list_frame)
            list_container.pack(fill=tk.BOTH, expand=True)

            self.file_list = tk.Listbox(list_container, selectmode=tk.SINGLE, exportselection=False)
            list_scrollbar = ttk.Scrollbar(list_container, command=self.file_list.yview)
            self.file_list.configure(yscrollcommand=list_scrollbar.set)

            self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            self.file_list.bind('<<ListboxSelect>>', self.on_file_select)

            preview_frame = ttk.LabelFrame(right_panel, text="封面预览", padding=10)
            preview_frame.grid(row=1, column=0, sticky="ew")
            right_panel.rowconfigure(1, weight=0)

            self.cover_label = ttk.Label(preview_frame)
            self.cover_label.pack()
            self.create_default_cover()

    def _install_mousewheel_support(self):
            """让鼠标滚轮在整个内容区域都能滚动（不需要把鼠标放到右侧滑块上）"""
            if self._mousewheel_installed:
                return
            self._mousewheel_installed = True

            toplevel = self.parent.winfo_toplevel()
            toplevel.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
            toplevel.bind_all("<Button-4>", self._on_mousewheel_linux, add="+")  # Linux
            toplevel.bind_all("<Button-5>", self._on_mousewheel_linux, add="+")  # Linux

    def _is_descendant_of_scroll_area(self, widget):
            """判断事件来源控件是否在可滚动区域内"""
            try:
                w = widget
                while w is not None:
                    if w == self.scrollable_frame:
                        return True
                    w = w.master
            except Exception:
                return False
            return False

    def _on_mousewheel(self, event):
            # 让 Text / Listbox 这类控件自己处理滚轮（例如日志框、文件列表）
            if event.widget.winfo_class() in {"Text", "Listbox", "Treeview"}:
                return

            if not self.canvas or not self.scrollable_frame:
                return

            if not self._is_descendant_of_scroll_area(event.widget):
                return

            delta = event.delta
            if abs(delta) >= 120:
                steps = int(-delta / 120)
            else:
                # macOS / 触控板可能是小步长
                steps = int(-delta)

            if steps != 0:
                self.canvas.yview_scroll(steps, "units")
                return "break"

    def _on_mousewheel_linux(self, event):
            if event.widget.winfo_class() in {"Text", "Listbox", "Treeview"}:
                return
            if not self.canvas or not self.scrollable_frame:
                return
            if not self._is_descendant_of_scroll_area(event.widget):
                return

            # Button-4 向上，Button-5 向下
            steps = -1 if event.num == 4 else 1
            self.canvas.yview_scroll(steps, "units")
            return "break"

    def _on_canvas_configure(self, event):
            """窗口尺寸变化时，让内容宽度跟随 canvas，避免右侧区域被截断"""
            if self.canvas_window is not None:
                self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def create_default_cover(self):
        """创建默认封面"""
        try:
            image = Image.new('RGB', DEFAULT_COVER_SIZE, color='#f0f0f0')
            photo = ImageTk.PhotoImage(image)
            self.default_cover = photo
            self.cover_label.config(image=photo)
            self.cover_label.image = photo
        except Exception:
            pass
    
    def log_message(self, message, level="info"):
        """记录日志消息"""
        self.status_text.config(state=tk.NORMAL)
        
        if level == "error":
            tag = "error"
        elif level == "warning":
            tag = "warning"
        elif level == "success":
            tag = "success"
        else:
            tag = "info"
        
        self.status_text.insert(tk.END, f"{message}\n", tag)
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        
        self.status_text.tag_config("error", foreground="red")
        self.status_text.tag_config("warning", foreground="orange")
        self.status_text.tag_config("success", foreground="green")
        self.status_text.tag_config("info", foreground="#333333")
    
    def browse_folder(self):
        """浏览文件夹"""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
            self.current_folder = folder
    
    def scan_folder(self):
        """扫描文件夹中的音频文件"""
        folder = self.folder_entry.get().strip()
        if not folder:
            messagebox.showwarning("警告", "请先选择文件夹")
            return
        
        if not os.path.exists(folder):
            self.log_message(f"文件夹不存在: {folder}", "error")
            return
        
        self.current_folder = folder

        self.file_list.delete(0, tk.END)
        files = FileUtils.get_files_by_criteria(folder, SUPPORTED_FORMATS, recursive=True)
        
        for file_path in files:
            self.file_list.insert(tk.END, os.path.relpath(file_path, folder))
        
        self.log_message(f"扫描完成，找到 {len(files)} 个音频文件")
    
    def on_file_select(self, event):
        """文件选择事件"""
        if not self.file_list.curselection():
            return
        
        selection = self.file_list.curselection()[0]
        file_name = self.file_list.get(selection)
        file_path = os.path.join(self.current_folder, file_name)
        self.current_file = file_path
        
        # 获取并显示元数据
        metadata = AudioFileProcessor.get_metadata(file_path)
        
        self.title_entry.delete(0, tk.END)
        self.artist_entry.delete(0, tk.END)
        self.album_entry.delete(0, tk.END)
        self.year_entry.delete(0, tk.END)
        self.genre_entry.delete(0, tk.END)
        
        if metadata["title"]:
            self.title_entry.insert(0, metadata["title"])
        if metadata["artist"]:
            self.artist_entry.insert(0, metadata["artist"])
        if metadata["album"]:
            self.album_entry.insert(0, metadata["album"])
        if metadata["year"]:
            self.year_entry.insert(0, metadata["year"])
        if metadata["genre"]:
            self.genre_entry.insert(0, metadata["genre"])
        
        # 显示封面
        self.display_cover(file_path)
    
    def display_cover(self, file_path):
        """显示封面图片"""
        try:
            cover_data = AudioFileProcessor.extract_cover(file_path)
            
            if cover_data:
                image = Image.open(io.BytesIO(cover_data))
                image.thumbnail(DEFAULT_COVER_SIZE)
                photo = ImageTk.PhotoImage(image)
                self.cover_label.config(image=photo)
                self.cover_label.image = photo
            else:
                self.cover_label.config(image=self.default_cover)
                self.cover_label.image = self.default_cover
        except Exception as e:
            self.log_message(f"显示封面失败: {str(e)}", "error")
            self.cover_label.config(image=self.default_cover)
            self.cover_label.image = self.default_cover
    
    def save_tags(self):
        """保存标签"""
        if not self.current_file:
            messagebox.showwarning("警告", "请先选择一个文件")
            return
        
        title = self.title_entry.get().strip()
        artist = self.artist_entry.get().strip()
        album = self.album_entry.get().strip()
        year = self.year_entry.get().strip()
        genre = self.genre_entry.get().strip()
        
        if not title and not artist and not album and not year and not genre:
            messagebox.showwarning("警告", "请输入至少一个标签信息")
            return
        
        try:
            AudioFileProcessor.save_tags(self.current_file, title, artist, album, year, genre)
            self.log_message(f"标签保存成功: {os.path.basename(self.current_file)}", "success")
        except Exception as e:
            self.log_message(f"保存标签失败: {str(e)}", "error")
    
    def clear_tags(self):
        """清除标签"""
        if not self.current_file:
            messagebox.showwarning("警告", "请先选择一个文件")
            return
        
        try:
            AudioFileProcessor.save_tags(self.current_file, "", "", "", "", "")
            self.title_entry.delete(0, tk.END)
            self.artist_entry.delete(0, tk.END)
            self.album_entry.delete(0, tk.END)
            self.year_entry.delete(0, tk.END)
            self.genre_entry.delete(0, tk.END)
            self.log_message(f"标签清除成功: {os.path.basename(self.current_file)}", "success")
        except Exception as e:
            self.log_message(f"清除标签失败: {str(e)}", "error")
    
    def apply_tags_all(self):
        """将当前标签应用到所有文件（除标题保留原文件）"""
        if not self.current_folder:
            messagebox.showwarning("警告", "请先选择文件夹")
            return
        
        artist = self.artist_entry.get().strip()
        album = self.album_entry.get().strip()
        year = self.year_entry.get().strip()
        genre = self.genre_entry.get().strip()
        
        if not artist and not album and not year and not genre:
            messagebox.showwarning("警告", "请输入至少一个标签信息（标题除外）")
            return
        
        files = FileUtils.get_files_by_criteria(self.current_folder, SUPPORTED_FORMATS, recursive=True)
        
        if not files:
            self.log_message("没有找到可处理的音频文件", "warning")
            return
        
        if not messagebox.askyesno("确认", f"确定要将当前标签（除标题外）应用到 {len(files)} 个文件吗？\n\n注意：将保留每个文件的原始标题，只更新艺术家、专辑、年份和流派。", icon=messagebox.WARNING):
            return
        
        success_count = 0
        error_count = 0
        
        for file_path in files:
            try:
                # 保留原文件标题，只更新其他标签
                AudioFileProcessor.save_tags(file_path, "", artist, album, year, genre, preserve_title=True)
                success_count += 1
            except Exception as e:
                error_count += 1
                self.log_message(f"处理失败 {os.path.basename(file_path)}: {str(e)}", "error")
        
        self.log_message(f"批量标签应用完成: 成功 {success_count}, 失败 {error_count}", "success")
    
    def rename_selected(self):
        """重命名选中的文件"""
        if not self.current_file:
            messagebox.showwarning("警告", "请先选择一个文件")
            return
        
        try:
            metadata = AudioFileProcessor.get_metadata(self.current_file)
            title = metadata.get("title", "")
            
            if not title:
                title = self.title_entry.get().strip()
                if not title:
                    self.log_message("文件没有标题信息，无法重命名", "warning")
                    return
            
            clean_title = FileUtils.sanitize_filename(title)
            if not clean_title:
                self.log_message("标题无效，无法重命名", "warning")
                return
            
            artist = metadata.get("artist", "")
            if artist:
                clean_artist = FileUtils.sanitize_filename(artist)
                if clean_artist:
                    clean_title = f"{clean_artist} - {clean_title}"
            
            dir_name = os.path.dirname(self.current_file)
            ext = os.path.splitext(self.current_file)[1]
            new_name = f"{clean_title}{ext}"
            new_path = os.path.join(dir_name, new_name)
            
            # 避免重名
            counter = 1
            while os.path.exists(new_path):
                new_name = f"{clean_title}_{counter}{ext}"
                new_path = os.path.join(dir_name, new_name)
                counter += 1
            
            os.rename(self.current_file, new_path)
            self.current_file = new_path
            self.log_message(f"重命名成功: {new_name}", "success")
            
            # 刷新列表
            self.scan_folder()
            
        except Exception as e:
            self.log_message(f"重命名失败: {str(e)}", "error")
    
    def rename_all(self):
        """重命名所有文件"""
        if not self.current_folder:
            messagebox.showwarning("警告", "请先选择文件夹")
            return
        
        files = FileUtils.get_files_by_criteria(self.current_folder, SUPPORTED_FORMATS, recursive=True)
        
        if not files:
            self.log_message("没有找到可处理的音频文件", "warning")
            return
        
        success_count = 0
        error_count = 0
        
        for file_path in files:
            try:
                metadata = AudioFileProcessor.get_metadata(file_path)
                title = metadata.get("title", "")
                
                if not title:
                    error_count += 1
                    continue
                
                clean_title = FileUtils.sanitize_filename(title)
                if not clean_title:
                    error_count += 1
                    continue
                
                artist = metadata.get("artist", "")
                if artist:
                    clean_artist = FileUtils.sanitize_filename(artist)
                    if clean_artist:
                        clean_title = f"{clean_artist} - {clean_title}"
                
                dir_name = os.path.dirname(file_path)
                ext = os.path.splitext(file_path)[1]
                new_name = f"{clean_title}{ext}"
                new_path = os.path.join(dir_name, new_name)
                
                # 避免重名
                counter = 1
                while os.path.exists(new_path) and new_path != file_path:
                    new_name = f"{clean_title}_{counter}{ext}"
                    new_path = os.path.join(dir_name, new_name)
                    counter += 1
                
                os.rename(file_path, new_path)
                success_count += 1
                
            except Exception:
                error_count += 1
        
        self.log_message(f"重命名完成: 成功 {success_count}, 失败 {error_count}", "success")
        self.scan_folder()
    
    def select_cover(self):
        """选择封面图片"""
        file_path = filedialog.askopenfilename(
            title="选择封面图片",
            filetypes=[("图片文件", "*.jpg;*.jpeg;*.png;*.bmp;*.gif")]
        )
        
        if file_path:
            self.selected_cover = file_path
            try:
                # 预览封面
                image = Image.open(file_path)
                image.thumbnail(DEFAULT_COVER_SIZE)
                photo = ImageTk.PhotoImage(image)
                self.cover_label.config(image=photo)
                self.cover_label.image = photo
                self.log_message(f"已选择封面: {os.path.basename(file_path)}")
            except Exception as e:
                self.log_message(f"加载封面失败: {str(e)}", "error")
    
    def optimize_cover(self, cover_data):
        """优化封面图片"""
        try:
            img = Image.open(io.BytesIO(cover_data))
            
            # 调整大小
            if max(img.size) > COVER_MAX_SIZE:
                img.thumbnail((COVER_MAX_SIZE, COVER_MAX_SIZE), Image.LANCZOS)
            
            # 保存为JPEG格式以兼容性更好
            output = io.BytesIO()
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(output, format='JPEG', quality=85, optimize=True)
            
            return output.getvalue(), "image/jpeg"
        except Exception:
            return cover_data, "image/jpeg"
    
    def apply_cover_selected(self):
        """应用封面到选中的文件"""
        if not self.selected_cover:
            messagebox.showwarning("警告", "请先选择封面图片")
            return
        
        if not self.current_file:
            messagebox.showwarning("警告", "请先选择一个音频文件")
            return
        
        try:
            with open(self.selected_cover, 'rb') as f:
                cover_data = f.read()
            
            # 优化封面
            cover_data, mime_type = self.optimize_cover(cover_data)
            
            # 应用封面
            AudioFileProcessor.apply_cover(self.current_file, cover_data, mime_type)
            self.log_message(f"封面应用成功: {os.path.basename(self.current_file)}", "success")
            
            # 刷新显示
            self.display_cover(self.current_file)
            
        except Exception as e:
            self.log_message(f"应用封面失败: {str(e)}", "error")
    
    def apply_cover_all(self):
        """应用封面到所有文件"""
        if not self.selected_cover:
            messagebox.showwarning("警告", "请先选择封面图片")
            return
        
        if not self.current_folder:
            messagebox.showwarning("警告", "请先选择文件夹")
            return
        
        files = FileUtils.get_files_by_criteria(self.current_folder, SUPPORTED_FORMATS, recursive=True)
        
        if not files:
            self.log_message("没有找到可处理的音频文件", "warning")
            return
        
        try:
            with open(self.selected_cover, 'rb') as f:
                cover_data = f.read()
            
            cover_data, mime_type = self.optimize_cover(cover_data)
            
            success_count = 0
            error_count = 0
            
            for file_path in files:
                try:
                    AudioFileProcessor.apply_cover(file_path, cover_data, mime_type)
                    success_count += 1
                except Exception:
                    error_count += 1
            
            self.log_message(f"封面应用完成: 成功 {success_count}, 失败 {error_count}", "success")
            
        except Exception as e:
            self.log_message(f"应用封面失败: {str(e)}", "error")
    
    def remove_cover_selected(self):
        """删除选中文件的封面"""
        if not self.current_file:
            messagebox.showwarning("警告", "请先选择一个音频文件")
            return
        
        try:
            AudioFileProcessor.remove_cover(self.current_file)
            self.log_message(f"封面删除成功: {os.path.basename(self.current_file)}", "success")
            self.display_cover(self.current_file)
        except Exception as e:
            self.log_message(f"删除封面失败: {str(e)}", "error")
    
    def remove_cover_all(self):
        """删除所有文件的封面"""
        if not self.current_folder:
            messagebox.showwarning("警告", "请先选择文件夹")
            return
        
        files = FileUtils.get_files_by_criteria(self.current_folder, SUPPORTED_FORMATS, recursive=True)
        
        if not files:
            self.log_message("没有找到可处理的音频文件", "warning")
            return
        
        success_count = 0
        error_count = 0
        
        for file_path in files:
            try:
                AudioFileProcessor.remove_cover(file_path)
                success_count += 1
            except Exception:
                error_count += 1
        
        self.log_message(f"封面删除完成: 成功 {success_count}, 失败 {error_count}", "success")


class FileSorterTab:
    """文件排序重命名标签页"""
    
    def __init__(self, parent):
        self.parent = parent
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        main_frame = ttk.Frame(self.parent, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="文件批量重命名工具").pack(pady=(0, 20))
        
        folder_frame = ttk.LabelFrame(main_frame, text="目标文件夹", padding=15)
        folder_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(folder_frame, text="文件夹路径:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.folder_entry = ttk.Entry(folder_frame, width=50)
        self.folder_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(folder_frame, text="浏览", command=self.browse_folder, width=8).grid(row=0, column=2, padx=2)
        
        naming_frame = ttk.LabelFrame(main_frame, text="命名设置", padding=15)
        naming_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(naming_frame, text="命名格式:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_format = ttk.Entry(naming_frame, width=50)
        self.name_format.grid(row=0, column=1, padx=5, pady=5)
        self.name_format.insert(0, "文件_{index:03d}")
        
        ttk.Label(naming_frame, text="示例: 文件_001.jpg, 文件_002.jpg").grid(row=1, column=1, sticky=tk.W, padx=5)
        
        sort_frame = ttk.LabelFrame(main_frame, text="排序设置", padding=15)
        sort_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.sort_method = tk.StringVar(value="name")
        
        ttk.Radiobutton(sort_frame, text="按文件名排序", variable=self.sort_method, value="name").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(sort_frame, text="按修改时间排序", variable=self.sort_method, value="modification").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(sort_frame, text="按创建时间排序", variable=self.sort_method, value="creation").pack(anchor=tk.W, pady=2)
        
        filter_frame = ttk.LabelFrame(main_frame, text="文件过滤", padding=15)
        filter_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(filter_frame, text="文件扩展名 (用逗号分隔):").pack(anchor=tk.W, pady=2)
        self.ext_filter = ttk.Entry(filter_frame, width=50)
        self.ext_filter.pack(fill=tk.X, pady=5)
        self.ext_filter.insert(0, "jpg,png,gif,bmp,mp3,mp4,txt,pdf")
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(0, 20))
        
        ttk.Button(button_frame, text="预览重命名", command=self.preview_rename, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="执行重命名", command=self.execute_rename, width=15).pack(side=tk.LEFT, padx=5)
        
        status_frame = ttk.LabelFrame(main_frame, text="操作日志", padding=15)
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=10, wrap=tk.WORD)
        self.status_text.pack(fill=tk.BOTH, expand=True)
        self.log_message("就绪")
    
    def log_message(self, message, level="info"):
        """记录日志消息"""
        self.status_text.config(state=tk.NORMAL)
        
        if level == "error":
            tag = "error"
        elif level == "warning":
            tag = "warning"
        elif level == "success":
            tag = "success"
        else:
            tag = "info"
        
        self.status_text.insert(tk.END, f"{message}\n", tag)
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        
        self.status_text.tag_config("error", foreground="red")
        self.status_text.tag_config("warning", foreground="orange")
        self.status_text.tag_config("success", foreground="green")
        self.status_text.tag_config("info", foreground="#333333")
    
    def browse_folder(self):
        """浏览文件夹"""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
    
    def get_file_list(self):
        """获取文件列表"""
        folder = self.folder_entry.get().strip()
        if not folder:
            messagebox.showwarning("警告", "请先选择文件夹")
            return []
        
        if not os.path.exists(folder):
            self.log_message(f"文件夹不存在: {folder}", "error")
            return []
        
        ext_text = self.ext_filter.get().strip()
        if ext_text:
            extensions = [ext.strip().lower() for ext in ext_text.split(',')]
            extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]
        else:
            extensions = []
        
        files = FileUtils.get_files_by_criteria(folder, extensions, recursive=False)
        
        sort_method = self.sort_method.get()
        if sort_method == "modification":
            files.sort(key=lambda x: os.path.getmtime(x))
        elif sort_method == "creation":
            files.sort(key=lambda x: os.path.getctime(x))
        else:
            files.sort(key=lambda x: os.path.basename(x).lower())
        
        return files
    
    def preview_rename(self):
        """预览重命名结果"""
        files = self.get_file_list()
        if not files:
            return
        
        name_format = self.name_format.get().strip()
        if not name_format:
            messagebox.showwarning("警告", "请输入命名格式")
            return
        
        self.log_message("=" * 50)
        self.log_message("重命名预览:")
        self.log_message("=" * 50)
        
        for idx, file_path in enumerate(files, 1):
            old_name = os.path.basename(file_path)
            ext = os.path.splitext(file_path)[1]
            
            try:
                new_name = name_format.format(index=idx) + ext
                self.log_message(f"{old_name}  ->  {new_name}")
            except Exception as e:
                self.log_message(f"生成新文件名失败: {old_name} - {str(e)}", "error")
        
        self.log_message("=" * 50)
        self.log_message(f"总计 {len(files)} 个文件")
    
    def execute_rename(self):
        """执行重命名操作"""
        files = self.get_file_list()
        if not files:
            return
        
        name_format = self.name_format.get().strip()
        if not name_format:
            messagebox.showwarning("警告", "请输入命名格式")
            return
        
        if not messagebox.askyesno("确认", f"确定要对 {len(files)} 个文件执行重命名吗？"):
            return
        
        success_count = 0
        error_count = 0
        
        for idx, file_path in enumerate(files, 1):
            try:
                dir_name = os.path.dirname(file_path)
                old_name = os.path.basename(file_path)
                ext = os.path.splitext(file_path)[1]
                
                new_name = name_format.format(index=idx) + ext
                new_path = os.path.join(dir_name, new_name)
                
                counter = 1
                while os.path.exists(new_path):
                    new_name = f"{name_format.format(index=idx)}_{counter}{ext}"
                    new_path = os.path.join(dir_name, new_name)
                    counter += 1
                
                os.rename(file_path, new_path)
                success_count += 1
                self.log_message(f"成功: {old_name} -> {new_name}", "success")
                
            except Exception as e:
                error_count += 1
                self.log_message(f"失败: {old_name} - {str(e)}", "error")
        
        self.log_message("=" * 50)
        self.log_message(f"操作完成: 成功 {success_count}, 失败 {error_count}", "success" if error_count == 0 else "warning")

# ==================== 主应用程序 ====================
class MediaToolsApp:
    """主应用程序"""
    
    def __init__(self, root):
            self.root = root
            self.root.title("媒体文件管理工具")

            # 自适应窗口大小，避免在小屏幕上被截断
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            w = min(1200, max(900, sw - 80))
            h = min(800, max(650, sh - 80))
            w = min(w, sw)
            h = min(h, sh)
            self.root.geometry(f"{w}x{h}")
            self.root.minsize(min(900, w), min(650, h))

            # 使用尽量原生的 ttk 主题
            self.setup_styles()
            self.setup_icon()
            self.setup_notebook()
            self.setup_menu()
            self.setup_statusbar()

    def setup_styles(self):
            """尽量使用系统原生主题（更“原生/好看”）"""
            style = ttk.Style(self.root)

            # 选择更接近系统原生的主题
            names = set(style.theme_names())
            if sys.platform.startswith("win"):
                preferred = ["vista", "xpnative"]
            elif sys.platform == "darwin":
                preferred = ["aqua"]
            else:
                preferred = ["clam", "alt", "default"]

            for theme in preferred:
                if theme in names:
                    try:
                        style.theme_use(theme)
                    except Exception:
                        pass
                    break

    def setup_icon(self):
        """设置窗口图标"""
        try:
            # 尝试加载图标
            icon_path = "media_icon.ico"
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            else:
                # 如果没有图标文件，使用默认图标
                pass
        except Exception:
            pass
    
    def setup_notebook(self):
        """设置标签页"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tag_editor_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.tag_editor_tab, text="音乐标签编辑器")
        self.tag_editor = TagEditorTab(self.tag_editor_tab)
        
        self.file_sorter_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.file_sorter_tab, text="文件批量重命名")
        self.file_sorter = FileSorterTab(self.file_sorter_tab)
    
    def setup_menu(self):
            """设置菜单栏"""
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)

            file_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="文件", menu=file_menu)
            file_menu.add_command(label="退出", command=self.root.quit)

            help_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="帮助", menu=help_menu)
            help_menu.add_command(label="关于", command=self.show_about)

    def setup_statusbar(self):
            """设置状态栏"""
            self.statusbar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
            self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

    def show_about(self):
        """显示关于对话框"""
        about_text = """媒体文件管理工具 v2.0
        
功能特性：
1. 音乐标签编辑（MP3, FLAC, OGG, M4A, WAV, OPUS）
2. 批量文件重命名
3. 封面图片管理
4. 文件排序和组织

技术支持：Python + Tkinter + Mutagen + Pillow
"""
        messagebox.showinfo("关于", about_text)

# ==================== 应用程序入口 ====================
def check_dependencies():
    """检查依赖库是否安装"""
    try:
        import mutagen
        from PIL import Image
        return True
    except ImportError as e:
        print("错误: 缺少必要的依赖库")
        print("请使用以下命令安装:")
        print("pip install mutagen pillow")
        return False

def main():
    """主函数"""
    if not check_dependencies():
        return
    
    root = tk.Tk()
    
    app = MediaToolsApp(root)
    
    # 居中显示窗口
    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = root.winfo_width()
    window_height = root.winfo_height()
    x = max(0, (screen_width - window_width) // 2)
    y = max(0, (screen_height - window_height) // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()

if __name__ == "__main__":
    main()