import os
import sys
import ctypes
import winreg
from datetime import datetime
import re
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import webbrowser
import traceback

class RegistryManager:
    """注册表管理类"""
    @staticmethod
    def read_value():
        """读取注册表值"""
        try:
            key_path = r"SYSTEM\CurrentControlSet\Control\PriorityControl"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            value, _ = winreg.QueryValueEx(key, "Win32PrioritySeparation")
            winreg.CloseKey(key)
            return value
        except Exception as e:
            print(f"读取注册表失败: {e}")
            return None
    
    @staticmethod
    def write_value(value):
        """写入注册表值"""
        try:
            key_path = r"SYSTEM\CurrentControlSet\Control\PriorityControl"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "Win32PrioritySeparation", 0, winreg.REG_DWORD, value)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"写入注册表失败: {e}")
            return False
    
    @staticmethod
    def backup_value(value, backup_dir):
        """备份注册表值到文件"""
        try:
            os.makedirs(backup_dir, exist_ok=True)
            
            # 生成简单的文件名格式：年月日_时分秒_十进制值.reg
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            hex_str = f"{value:08X}"
            filename = f"{timestamp}_{value}_0x{hex_str}.reg"
            filepath = os.path.join(backup_dir, filename)
            
            reg_content = f"""Windows Registry Editor Version 5.00

[HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\PriorityControl]
"Win32PrioritySeparation"=dword:{hex_str}
"""
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(reg_content)
            
            return filename, filepath
        except Exception as e:
            print(f"备份失败: {e}")
            return None, None

class AdminChecker:
    """管理员权限检查器"""
    @staticmethod
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    @staticmethod
    def restart_as_admin():
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            return True
        except Exception as e:
            print(f"重新启动失败: {e}")
            return False

class BackupManager:
    """备份管理器"""
    def __init__(self, backup_dir):
        self.backup_dir = backup_dir
        # 简单的正则表达式，匹配：timestamp_decimal_0xhex.reg
        self.pattern = re.compile(r'(\d{8}_\d{6})_(\d+)_0x([0-9A-F]{8})\.reg')
    
    def list_backups(self):
        """列出所有备份文件"""
        if not os.path.exists(self.backup_dir):
            return []
        
        backups = []
        try:
            for filename in os.listdir(self.backup_dir):
                if filename.lower().endswith('.reg'):
                    filepath = os.path.join(self.backup_dir, filename)
                    
                    # 尝试解析文件名
                    match = self.pattern.match(filename)
                    if match:
                        timestamp_str, decimal_str, hex_str = match.groups()
                        try:
                            decimal = int(decimal_str)
                            
                            # 解析时间戳
                            year = int(timestamp_str[0:4])
                            month = int(timestamp_str[4:6])
                            day = int(timestamp_str[6:8])
                            hour = int(timestamp_str[9:11])
                            minute = int(timestamp_str[11:13])
                            second = int(timestamp_str[13:15])
                            
                            date_str = f"{year:04d}-{month:02d}-{day:02d}"
                            time_str = f"{hour:02d}:{minute:02d}:{second:02d}"
                            
                            mtime = os.path.getmtime(filepath)
                            backups.append({
                                'filename': filename,
                                'filepath': filepath,
                                'date': date_str,
                                'time': time_str,
                                'decimal': decimal,
                                'hex': f"0x{hex_str}",
                                'mtime': mtime
                            })
                        except ValueError:
                            # 如果无法解析，尝试使用文件修改时间
                            self._add_backup_using_mtime(backups, filename, filepath)
                    else:
                        # 如果正则不匹配，尝试使用文件修改时间
                        self._add_backup_using_mtime(backups, filename, filepath)
            
            # 按修改时间倒序排序
            backups.sort(key=lambda x: x['mtime'], reverse=True)
            return backups
        except Exception as e:
            print(f"列出备份失败: {e}")
            traceback.print_exc()
            return []
    
    def _add_backup_using_mtime(self, backups, filename, filepath):
        """使用文件修改时间添加备份"""
        try:
            mtime = os.path.getmtime(filepath)
            dt = datetime.fromtimestamp(mtime)
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M:%S")
            
            # 尝试从文件名中提取数值
            decimal = 0
            hex_str = "00000000"
            
            # 简单的模式匹配
            for part in filename.split('_'):
                if part.isdigit():
                    decimal = int(part)
                    break
            
            backups.append({
                'filename': filename,
                'filepath': filepath,
                'date': date_str,
                'time': time_str,
                'decimal': decimal,
                'hex': f"0x{hex_str:>08}",
                'mtime': mtime
            })
        except Exception as e:
            print(f"添加备份失败 {filename}: {e}")
    
    def clean_old_backups(self, keep=20):
        """清理旧备份"""
        backups = self.list_backups()
        if len(backups) <= keep:
            return
        
        for backup in backups[keep:]:
            try:
                os.remove(backup['filepath'])
            except Exception as e:
                print(f"删除备份失败 {backup['filename']}: {e}")

class ValueFormatter:
    """数值格式化器"""
    @staticmethod
    def format_value(value):
        if value is None:
            return {
                'decimal': 'N/A',
                'hex': '0x00000000',
                'binary': '00000000 00000000 00000000 00000000'
            }
        
        return {
            'decimal': str(value),
            'hex': f"0x{value:08X}",
            'binary': ' '.join([f"{value:032b}"[i:i+8] for i in range(0, 32, 8)])
        }
    
    @staticmethod
    def parse_input(input_str):
        """解析用户输入"""
        if not input_str:
            return None
        
        input_str = input_str.strip().lower()
        
        # 移除可能的0x或h后缀
        if input_str.startswith('0x'):
            input_str = input_str[2:]
        if input_str.endswith('h'):
            input_str = input_str[:-1]
        
        try:
            # 尝试解析为十进制
            return int(input_str)
        except ValueError:
            try:
                # 尝试解析为十六进制
                return int(input_str, 16)
            except ValueError:
                return None

class SimpleMessageBox:
    """简单消息框"""
    @staticmethod
    def show(parent, title, message, type='info'):
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.transient(parent)
        dialog.grab_set()
        
        # 设置大小和位置
        dialog.geometry('400x200')
        dialog.update_idletasks()
        
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (400 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (200 // 2)
        dialog.geometry(f'400x200+{x}+{y}')
        
        # 图标和颜色
        icons = {
            'info': ('ℹ️', '#3498db'),
            'warning': ('⚠️', '#f39c12'),
            'error': ('❌', '#e74c3c'),
            'success': ('✅', '#2ecc71')
        }
        icon, color = icons.get(type, ('ℹ️', '#3498db'))
        
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill='both', expand=True)
        
        # 图标
        ttk.Label(frame, text=icon, font=('Arial', 24),
                 foreground=color).pack(pady=(0, 10))
        
        # 消息
        ttk.Label(frame, text=message, wraplength=350,
                 justify='center').pack(pady=(0, 20), fill='x')
        
        # 按钮
        ttk.Button(frame, text='确定', command=dialog.destroy,
                  width=15).pack()
        
        return dialog
    
    @staticmethod
    def ask_yes_no(parent, title, message):
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.transient(parent)
        dialog.grab_set()
        
        dialog.geometry('450x200')
        dialog.update_idletasks()
        
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (450 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (200 // 2)
        dialog.geometry(f'450x200+{x}+{y}')
        
        result = {'value': False}
        
        def set_result(value):
            result['value'] = value
            dialog.destroy()
        
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill='both', expand=True)
        
        ttk.Label(frame, text=message, wraplength=400,
                 justify='center').pack(pady=(0, 20), fill='x')
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack()
        
        ttk.Button(btn_frame, text='是', command=lambda: set_result(True),
                  width=10).pack(side='left', padx=10)
        ttk.Button(btn_frame, text='否', command=lambda: set_result(False),
                  width=10).pack(side='left', padx=10)
        
        dialog.wait_window()
        return result['value']

class PrioritySeparationTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Win32 PrioritySeparation 工具")
        
        # 设置默认大小
        self.root.geometry("900x650")
        self.root.minsize(800, 550)
        
        # 初始化组件
        self.backup_dir = os.path.join(os.getcwd(), 'backups')
        self.registry_manager = RegistryManager()
        self.backup_manager = BackupManager(self.backup_dir)
        self.value_formatter = ValueFormatter()
        
        # 当前选中备份
        self.selected_backup = None
        
        # 创建界面
        self.create_widgets()
        
        # 加载数据
        self.refresh_data()
        
        # 居中显示
        self.center_window()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def center_window(self):
        """居中窗口"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_container = ttk.Frame(self.root)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 标题
        title_frame = ttk.Frame(main_container)
        title_frame.pack(fill='x', pady=(0, 15))
        
        ttk.Label(title_frame, text="Win32 PrioritySeparation 工具",
                 font=('Arial', 16, 'bold')).pack(side='left')
        
        ttk.Button(title_frame, text="刷新", command=self.refresh_data,
                  width=8).pack(side='right', padx=(0, 5))
        
        ttk.Button(title_frame, text="关于", command=self.show_about,
                  width=8).pack(side='right')
        
        # 分割为左右两部分
        paned_window = ttk.PanedWindow(main_container, orient='horizontal')
        paned_window.pack(fill='both', expand=True, pady=10)
        
        # 左侧面板 - 设置
        left_frame = ttk.Frame(paned_window, width=350)
        paned_window.add(left_frame, weight=1)
        
        self.create_left_panel(left_frame)
        
        # 右侧面板 - 备份
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=2)
        
        self.create_right_panel(right_frame)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_container, textvariable=self.status_var,
                              relief='sunken', anchor='w', padding=(5, 2))
        status_bar.pack(side='bottom', fill='x')
    
    def create_left_panel(self, parent):
        """创建左侧面板"""
        # 当前值显示
        current_frame = ttk.LabelFrame(parent, text="当前值", padding=15)
        current_frame.pack(fill='x', pady=(0, 15))
        
        # 十进制值
        dec_frame = ttk.Frame(current_frame)
        dec_frame.pack(fill='x', pady=5)
        ttk.Label(dec_frame, text="十进制:", width=10).pack(side='left')
        self.dec_var = tk.StringVar(value="读取中...")
        ttk.Label(dec_frame, textvariable=self.dec_var, font=('Consolas', 10)).pack(side='left')
        
        # 十六进制值
        hex_frame = ttk.Frame(current_frame)
        hex_frame.pack(fill='x', pady=5)
        ttk.Label(hex_frame, text="十六进制:", width=10).pack(side='left')
        self.hex_var = tk.StringVar(value="0x00000000")
        ttk.Label(hex_frame, textvariable=self.hex_var, font=('Consolas', 10)).pack(side='left')
        
        # 二进制值
        bin_frame = ttk.Frame(current_frame)
        bin_frame.pack(fill='x', pady=5)
        ttk.Label(bin_frame, text="二进制:", width=10).pack(side='left')
        self.bin_var = tk.StringVar(value="00000000 00000000 00000000 00000000")
        bin_label = ttk.Label(bin_frame, textvariable=self.bin_var, font=('Consolas', 9))
        bin_label.pack(side='left')
        
        # 刷新按钮
        ttk.Button(current_frame, text="刷新当前值", command=self.refresh_current_value,
                  width=15).pack(pady=(10, 0))
        
        # 预设值设置
        preset_frame = ttk.LabelFrame(parent, text="快速设置", padding=15)
        preset_frame.pack(fill='x', pady=(0, 15))
        
        presets = [
            ("游戏模式 (26)", 26, "前台程序获得更多CPU时间"),
            ("平衡模式 (24)", 24, "Windows推荐值"),
            ("后台服务 (2)", 2, "优化后台服务性能"),
            ("前台优化 (38)", 38, "最大化前台响应"),
            ("标准模式 (0)", 0, "Windows默认设置")
        ]
        
        for i, (name, value, tip) in enumerate(presets):
            btn = ttk.Button(preset_frame, text=name,
                           command=lambda v=value, n=name: self.apply_preset(v, n),
                           width=20)
            btn.pack(pady=3)
        
        # 自定义设置
        custom_frame = ttk.LabelFrame(parent, text="自定义设置", padding=15)
        custom_frame.pack(fill='x')
        
        ttk.Label(custom_frame, text="输入新值:").pack(anchor='w', pady=(0, 5))
        
        input_frame = ttk.Frame(custom_frame)
        input_frame.pack(fill='x', pady=5)
        
        self.custom_entry = ttk.Entry(input_frame)
        self.custom_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.custom_entry.bind('<Return>', lambda e: self.apply_custom_value())
        
        ttk.Button(input_frame, text="应用", command=self.apply_custom_value,
                  width=8).pack(side='right')
        
        ttk.Label(custom_frame, text="(十进制或十六进制，如: 26 或 0x1A)",
                 font=('Arial', 8), foreground='gray').pack(anchor='w', pady=(5, 0))
    
    def create_right_panel(self, parent):
        """创建右侧面板"""
        # 备份管理标题栏
        backup_title = ttk.Frame(parent)
        backup_title.pack(fill='x', pady=(0, 10))
        
        ttk.Label(backup_title, text="备份管理",
                 font=('Arial', 12, 'bold')).pack(side='left')
        
        btn_frame = ttk.Frame(backup_title)
        btn_frame.pack(side='right')
        
        ttk.Button(btn_frame, text="创建备份", command=self.create_backup,
                  width=10).pack(side='left', padx=2)
        
        ttk.Button(btn_frame, text="打开目录", command=self.open_backup_dir,
                  width=10).pack(side='left', padx=2)
        
        # 备份列表
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill='both', expand=True)
        
        # 创建Treeview
        columns = ('date', 'time', 'value_dec', 'value_hex', 'filename')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', selectmode='browse')
        
        # 设置列
        self.tree.heading('date', text='日期')
        self.tree.heading('time', text='时间')
        self.tree.heading('value_dec', text='十进制')
        self.tree.heading('value_hex', text='十六进制')
        self.tree.heading('filename', text='文件名')
        
        self.tree.column('date', width=100)
        self.tree.column('time', width=80)
        self.tree.column('value_dec', width=80, anchor='center')
        self.tree.column('value_hex', width=90, anchor='center')
        self.tree.column('filename', width=200)
        
        # 滚动条
        vsb = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # 布局
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 绑定选择事件
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        
        # 操作按钮
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill='x', pady=(10, 0))
        
        self.restore_btn = ttk.Button(action_frame, text="恢复选中备份",
                                     command=self.restore_backup,
                                     state='disabled', width=15)
        self.restore_btn.pack(side='left', padx=(0, 10))
        
        self.delete_btn = ttk.Button(action_frame, text="删除选中备份",
                                    command=self.delete_backup,
                                    state='disabled', width=15)
        self.delete_btn.pack(side='left')
        
        # 备份计数
        self.count_var = tk.StringVar(value="无备份")
        ttk.Label(action_frame, textvariable=self.count_var,
                 font=('Arial', 9)).pack(side='right')
    
    def refresh_data(self):
        """刷新所有数据"""
        self.refresh_current_value()
        self.refresh_backup_list()
    
    def refresh_current_value(self):
        """刷新当前值显示"""
        try:
            value = self.registry_manager.read_value()
            if value is not None:
                formatted = self.value_formatter.format_value(value)
                self.dec_var.set(formatted['decimal'])
                self.hex_var.set(formatted['hex'])
                self.bin_var.set(formatted['binary'])
                self.status_var.set(f"当前值: {formatted['decimal']} ({formatted['hex']})")
            else:
                self.dec_var.set("读取失败")
                self.hex_var.set("0x00000000")
                self.bin_var.set("00000000 00000000 00000000 00000000")
                self.status_var.set("读取注册表失败")
        except Exception as e:
            self.dec_var.set("错误")
            self.hex_var.set("0x00000000")
            self.status_var.set(f"刷新失败: {str(e)}")
    
    def refresh_backup_list(self):
        """刷新备份列表"""
        try:
            # 清空当前列表
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            backups = self.backup_manager.list_backups()
            
            for backup in backups:
                self.tree.insert('', 'end', values=(
                    backup['date'],
                    backup['time'],
                    backup['decimal'],
                    backup['hex'],
                    backup['filename']
                ))
            
            count = len(backups)
            self.count_var.set(f"共 {count} 个备份")
            
            if count > 0:
                self.status_var.set(f"已加载 {count} 个备份")
            else:
                self.status_var.set("无备份文件")
                
        except Exception as e:
            self.status_var.set(f"加载备份失败: {str(e)}")
            traceback.print_exc()
    
    def on_tree_select(self, event):
        """树形列表选择事件"""
        selection = self.tree.selection()
        if selection:
            self.selected_backup = selection[0]
            self.restore_btn.config(state='normal')
            self.delete_btn.config(state='normal')
        else:
            self.selected_backup = None
            self.restore_btn.config(state='disabled')
            self.delete_btn.config(state='disabled')
    
    def apply_preset(self, value, name):
        """应用预设值"""
        formatted = self.value_formatter.format_value(value)
        
        confirm = SimpleMessageBox.ask_yes_no(
            self.root,
            "确认设置",
            f"确定要将 Win32PrioritySeparation 设置为:\n\n"
            f"预设: {name}\n"
            f"十进制: {formatted['decimal']}\n"
            f"十六进制: {formatted['hex']}\n\n"
            f"建议先备份当前值。"
        )
        
        if confirm:
            # 备份当前值
            current = self.registry_manager.read_value()
            if current is not None:
                self.create_backup_silent(current)
            
            # 应用新值
            if self.registry_manager.write_value(value):
                self.refresh_current_value()
                SimpleMessageBox.show(
                    self.root,
                    "设置成功",
                    f"已成功设置为 {name}\n"
                    f"({formatted['decimal']} / {formatted['hex']})",
                    'success'
                )
            else:
                SimpleMessageBox.show(
                    self.root,
                    "设置失败",
                    "无法修改注册表值，请检查权限",
                    'error'
                )
    
    def apply_custom_value(self):
        """应用自定义值"""
        input_str = self.custom_entry.get()
        value = self.value_formatter.parse_input(input_str)
        
        if value is None:
            SimpleMessageBox.show(
                self.root,
                "输入错误",
                "请输入有效的数值\n(十进制或十六进制，如: 26 或 0x1A)",
                'error'
            )
            self.custom_entry.select_range(0, 'end')
            return
        
        # 验证范围
        if value < 0 or value > 255:
            SimpleMessageBox.show(
                self.root,
                "输入错误",
                "数值必须在 0-255 范围内",
                'error'
            )
            return
        
        formatted = self.value_formatter.format_value(value)
        
        confirm = SimpleMessageBox.ask_yes_no(
            self.root,
            "确认设置",
            f"确定要将 Win32PrioritySeparation 设置为:\n\n"
            f"十进制: {formatted['decimal']}\n"
            f"十六进制: {formatted['hex']}"
        )
        
        if confirm:
            # 备份当前值
            current = self.registry_manager.read_value()
            if current is not None:
                self.create_backup_silent(current)
            
            # 应用新值
            if self.registry_manager.write_value(value):
                self.refresh_current_value()
                self.custom_entry.delete(0, 'end')
                SimpleMessageBox.show(
                    self.root,
                    "设置成功",
                    f"已成功设置为:\n"
                    f"十进制: {formatted['decimal']}\n"
                    f"十六进制: {formatted['hex']}",
                    'success'
                )
            else:
                SimpleMessageBox.show(
                    self.root,
                    "设置失败",
                    "无法修改注册表值",
                    'error'
                )
    
    def create_backup(self):
        """创建备份"""
        current = self.registry_manager.read_value()
        if current is None:
            SimpleMessageBox.show(
                self.root,
                "备份失败",
                "无法读取当前注册表值",
                'error'
            )
            return
        
        filename, filepath = self.registry_manager.backup_value(current, self.backup_dir)
        
        if filename:
            self.refresh_backup_list()
            self.backup_manager.clean_old_backups(20)
            
            formatted = self.value_formatter.format_value(current)
            SimpleMessageBox.show(
                self.root,
                "备份成功",
                f"已创建备份文件:\n{filename}\n\n"
                f"当前值: {formatted['decimal']} ({formatted['hex']})",
                'success'
            )
            self.status_var.set(f"备份创建成功: {filename}")
        else:
            SimpleMessageBox.show(
                self.root,
                "备份失败",
                "无法创建备份文件",
                'error'
            )
    
    def create_backup_silent(self, value):
        """静默创建备份"""
        try:
            filename, _ = self.registry_manager.backup_value(value, self.backup_dir)
            if filename:
                self.refresh_backup_list()
                self.backup_manager.clean_old_backups(20)
                return True
        except:
            pass
        return False
    
    def restore_backup(self):
        """恢复备份"""
        if not self.selected_backup:
            return
        
        item = self.tree.item(self.selected_backup)
        values = item['values']
        
        decimal_value = values[2]
        hex_value = values[3]
        filename = values[4]
        
        confirm = SimpleMessageBox.ask_yes_no(
            self.root,
            "确认恢复",
            f"确定要恢复备份吗？\n\n"
            f"备份文件: {filename}\n"
            f"值: {decimal_value} ({hex_value})"
        )
        
        if confirm:
            # 备份当前值
            current = self.registry_manager.read_value()
            if current is not None:
                self.create_backup_silent(current)
            
            # 恢复备份值
            if self.registry_manager.write_value(decimal_value):
                self.refresh_current_value()
                SimpleMessageBox.show(
                    self.root,
                    "恢复成功",
                    f"已成功恢复备份\n{filename}",
                    'success'
                )
            else:
                SimpleMessageBox.show(
                    self.root,
                    "恢复失败",
                    "无法修改注册表值",
                    'error'
                )
    
    def delete_backup(self):
        """删除备份"""
        if not self.selected_backup:
            return
        
        item = self.tree.item(self.selected_backup)
        filename = values[4]
        
        confirm = SimpleMessageBox.ask_yes_no(
            self.root,
            "确认删除",
            f"确定要删除备份文件吗？\n\n{filename}"
        )
        
        if confirm:
            try:
                filepath = os.path.join(self.backup_dir, filename)
                os.remove(filepath)
                self.refresh_backup_list()
                SimpleMessageBox.show(
                    self.root,
                    "删除成功",
                    f"已删除备份文件\n{filename}",
                    'success'
                )
            except Exception as e:
                SimpleMessageBox.show(
                    self.root,
                    "删除失败",
                    f"无法删除文件:\n{str(e)}",
                    'error'
                )
    
    def open_backup_dir(self):
        """打开备份目录"""
        try:
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)
            
            os.startfile(self.backup_dir)
            self.status_var.set("已打开备份目录")
        except Exception as e:
            SimpleMessageBox.show(
                self.root,
                "错误",
                f"无法打开目录:\n{str(e)}",
                'error'
            )
    
    def show_about(self):
        """显示关于信息"""
        about_text = """Win32 PrioritySeparation 工具

版本: 2.1
作者: Y0USA

功能:
• 读取和修改 Win32PrioritySeparation 注册表值
• 预设值快速设置
• 自定义值设置
• 备份和恢复管理

联系方式:
B站: https://space.bilibili.com/353017137
GitHub: https://github.com/YOU5A
邮箱: pfmaxlnx@gmail.com

© 2019-2026 保留所有权利"""
        
        dialog = tk.Toplevel(self.root)
        dialog.title("关于")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        
        # 设置大小和位置
        dialog.geometry('450x400')
        dialog.update_idletasks()
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (450 // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (400 // 2)
        dialog.geometry(f'450x400+{x}+{y}')
        
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill='both', expand=True)
        
        # 标题
        ttk.Label(frame, text="Win32 PrioritySeparation 工具",
                 font=('Arial', 14, 'bold')).pack(pady=(0, 10))
        
        # 文本内容
        text = scrolledtext.ScrolledText(frame, wrap='word',
                                        width=50, height=15,
                                        font=('Arial', 10))
        text.pack(fill='both', expand=True, pady=(0, 15))
        text.insert('1.0', about_text)
        text.config(state='disabled')
        
        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.pack()
        
        def open_url(url):
            try:
                webbrowser.open(url)
            except:
                pass
        
        ttk.Button(btn_frame, text="访问B站",
                  command=lambda: open_url("https://space.bilibili.com/353017137"),
                  width=12).pack(side='left', padx=5)
        
        ttk.Button(btn_frame, text="访问GitHub",
                  command=lambda: open_url("https://github.com/YOU5A"),
                  width=12).pack(side='left', padx=5)
        
        ttk.Button(btn_frame, text="关闭",
                  command=dialog.destroy,
                  width=12).pack(side='left', padx=5)
    
    def on_closing(self):
        """窗口关闭事件"""
        if SimpleMessageBox.ask_yes_no(self.root, "确认退出", "确定要退出程序吗？"):
            self.root.destroy()

def run_application():
    """运行应用程序"""
    try:
        # 检查管理员权限
        if not AdminChecker.is_admin():
            print("需要管理员权限，正在重新启动...")
            if AdminChecker.restart_as_admin():
                sys.exit()
            else:
                messagebox.showerror("错误", "需要管理员权限运行此程序")
                return
        
        # 创建主窗口
        root = tk.Tk()
        
        # 设置DPI感知
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
        
        # 创建应用实例
        app = PrioritySeparationTool(root)
        
        # 运行主循环
        root.mainloop()
        
    except Exception as e:
        error_msg = f"程序启动失败:\n\n{str(e)}\n\n{traceback.format_exc()}"
        messagebox.showerror("启动错误", error_msg)

if __name__ == "__main__":
    run_application()