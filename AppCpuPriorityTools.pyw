import sys
import os
import winreg
import ctypes
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from tkinter import font as tkfont
import threading

def is_admin():
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """以管理员权限重新运行程序"""
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)

class AppCpuPriorityToolsTkinter:
    def __init__(self, root):
        self.root = root
        self.root.title("AppCpuPriorityTools - 应用程序优先级管理工具")
        self.root.geometry("1000x750")  # 稍微增大窗口尺寸
        
        # 应用列表数据
        self.applications = []
        
        # 设置窗口图标（可选）
        try:
            self.root.iconbitmap(default='icon.ico')
        except:
            pass
        
        # 使窗口居中显示
        self.center_window(1000, 750)
        
        # 设置窗口最小尺寸
        self.root.minsize(900, 600)
        
        # 创建界面
        self.setup_ui()
        
        # 加载现有应用
        self.load_applications()
        
    def center_window(self, width, height):
        """将窗口居中显示"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def setup_ui(self):
        """设置用户界面"""
        # 使用PanedWindow实现可调整的分割布局
        main_paned = tk.PanedWindow(self.root, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=5)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标题区域
        title_frame = tk.Frame(main_paned, bg='#f0f0f0')
        title_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        title_label = tk.Label(title_frame, text="应用程序 CPU/I/O 优先级设置工具", 
                               font=("微软雅黑", 16, "bold"), bg='#f0f0f0')
        title_label.pack(pady=(5, 0))
        
        subtitle_label = tk.Label(title_frame, text="通过Windows注册表永久设置应用程序优先级", 
                                  font=("微软雅黑", 10), bg='#f0f0f0')
        subtitle_label.pack(pady=(0, 5))
        
        # 控制按钮区域
        control_frame = tk.Frame(main_paned, bg='#f0f0f0')
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 使用ttk按钮获得更好的视觉效果
        button_style = ttk.Style()
        button_style.configure('Accent.TButton', font=('微软雅黑', 10))
        
        self.add_button = ttk.Button(control_frame, text="添加新应用", 
                                    command=self.add_application, width=15, style='Accent.TButton')
        self.add_button.grid(row=0, column=0, padx=2, pady=5)
        
        self.edit_button = ttk.Button(control_frame, text="编辑选中项", 
                                     command=self.edit_application, width=15, state=tk.DISABLED)
        self.edit_button.grid(row=0, column=1, padx=2, pady=5)
        
        self.remove_button = ttk.Button(control_frame, text="删除选中项", 
                                       command=self.remove_application, width=15, state=tk.DISABLED)
        self.remove_button.grid(row=0, column=2, padx=2, pady=5)
        
        self.refresh_button = ttk.Button(control_frame, text="刷新列表", 
                                        command=self.load_applications, width=15)
        self.refresh_button.grid(row=0, column=3, padx=2, pady=5)
        
        tk.Frame(control_frame, width=20).grid(row=0, column=4)  # 间距
        
        self.export_button = ttk.Button(control_frame, text="导出配置", 
                                       command=self.export_configuration, width=15)
        self.export_button.grid(row=0, column=5, padx=2, pady=5)
        
        self.import_button = ttk.Button(control_frame, text="导入配置", 
                                       command=self.import_configuration, width=15)
        self.import_button.grid(row=0, column=6, padx=2, pady=5)
        
        # 主要区域 - 使用PanedWindow分割应用列表和详情
        content_paned = tk.PanedWindow(main_paned, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=5)
        
        # 应用列表区域
        list_frame = tk.LabelFrame(content_paned, text="已配置的应用程序", 
                                  font=("微软雅黑", 10, "bold"), padx=10, pady=5)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建树形视图 - 使用更好的样式
        style = ttk.Style()
        style.configure("Treeview", font=('微软雅黑', 10), rowheight=25)
        style.configure("Treeview.Heading", font=('微软雅黑', 10, 'bold'))
        
        columns = ("应用名称", "CPU优先级", "I/O优先级")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        # 设置列标题和宽度
        self.tree.heading("应用名称", text="应用名称", anchor=tk.W)
        self.tree.heading("CPU优先级", text="CPU优先级", anchor=tk.CENTER)
        self.tree.heading("I/O优先级", text="I/O优先级", anchor=tk.CENTER)
        
        self.tree.column("应用名称", width=400, minwidth=200, anchor=tk.W)
        self.tree.column("CPU优先级", width=200, minwidth=150, anchor=tk.CENTER)
        self.tree.column("I/O优先级", width=200, minwidth=150, anchor=tk.CENTER)
        
        # 使用标签交替颜色
        self.tree.tag_configure('oddrow', background='#f9f9f9')
        self.tree.tag_configure('evenrow', background='#ffffff')
        
        # 添加滚动条
        scrollbar_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # 网格布局
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        scrollbar_x.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 详情面板区域
        detail_frame = tk.LabelFrame(content_paned, text="应用详情", 
                                    font=("微软雅黑", 10, "bold"), padx=10, pady=5)
        detail_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))
        
        # 创建带滚动条的文本区域
        detail_container = tk.Frame(detail_frame)
        detail_container.pack(fill=tk.BOTH, expand=True)
        
        self.detail_text = tk.Text(detail_container, height=6, width=80, 
                                  font=("微软雅黑", 10), wrap=tk.WORD, 
                                  relief=tk.FLAT, bg='#f9f9f9')
        
        detail_scrollbar = ttk.Scrollbar(detail_container, command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=detail_scrollbar.set)
        
        self.detail_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        detail_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        detail_container.grid_rowconfigure(0, weight=1)
        detail_container.grid_columnconfigure(0, weight=1)
        
        self.detail_text.config(state=tk.DISABLED)
        
        # 添加到可调整的分割窗口
        content_paned.add(list_frame, height=400)  # 给列表区域更多空间
        content_paned.add(detail_frame, height=150)  # 固定详情区域高度
        
        # 将内容区域添加到主分割窗口
        main_paned.add(title_frame)
        main_paned.add(control_frame)
        main_paned.add(content_paned)
        
        # 绑定选择事件
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)
        self.tree.bind("<Double-1>", self.on_item_double_click)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = tk.Label(self.root, textvariable=self.status_var, 
                             bd=1, relief=tk.SUNKEN, anchor=tk.W,
                             font=("微软雅黑", 9), bg='#f0f0f0')
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 使窗口内容能够随窗口调整大小
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
    def on_item_select(self, event):
        """选中项目时更新按钮状态"""
        selected = self.tree.selection()
        if selected:
            self.edit_button.config(state=tk.NORMAL)
            self.remove_button.config(state=tk.NORMAL)
            self.update_detail_panel()
        else:
            self.edit_button.config(state=tk.DISABLED)
            self.remove_button.config(state=tk.DISABLED)
            
    def on_item_double_click(self, event):
        """双击项目编辑"""
        self.edit_application()
        
    def update_detail_panel(self):
        """更新详情面板"""
        selected = self.tree.selection()
        if not selected:
            return
            
        item = self.tree.item(selected[0])
        app_info = item['values']
        
        cpu_mapping = {
            "1": "空闲",
            "2": "正常", 
            "3": "高",
            "4": "实时",
            "5": "低于正常",
            "6": "高于正常"
        }
        
        io_mapping = {
            "0": "非常低",
            "1": "低",
            "2": "正常",
            "3": "高"
        }
        
        # 创建格式化的详情信息
        details = "══════════════════ 应用详细信息 ══════════════════\n\n"
        details += f"📁 应用名称: {app_info[0]}\n\n"
        details += f"⚡ CPU优先级: {cpu_mapping.get(app_info[1], '未知')} (注册表值: {app_info[1]})\n\n"
        details += f"📊 I/O优先级: {io_mapping.get(app_info[2], '未设置')} "
        if app_info[2] != '未设置':
            details += f"(注册表值: {app_info[2]})"
        details += "\n\n"
        details += "══════════════════════════════════════════════════"
        
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(1.0, details)
        self.detail_text.config(state=tk.DISABLED)
        
    def load_applications(self):
        """加载应用程序列表"""
        self.status_var.set("正在加载应用列表...")
        
        # 在新线程中加载
        thread = threading.Thread(target=self._load_applications_thread)
        thread.daemon = True
        thread.start()
        
    def _load_applications_thread(self):
        """后台加载应用列表"""
        try:
            apps = []
            base_path = "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Image File Execution Options"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_path) as key:
                count = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, count)
                        count += 1
                        
                        # 检查是否包含PerfOptions
                        try:
                            with winreg.OpenKey(key, f"{subkey_name}\\PerfOptions") as _:
                                try:
                                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                                       f"{base_path}\\{subkey_name}\\PerfOptions") as perf_key:
                                        try:
                                            cpu_val, _ = winreg.QueryValueEx(perf_key, "CpuPriorityClass")
                                            has_io = True
                                            try:
                                                io_val, _ = winreg.QueryValueEx(perf_key, "IoPriority")
                                            except FileNotFoundError:
                                                has_io = False
                                                io_val = None
                                        except FileNotFoundError:
                                            cpu_val = None
                                            has_io = False
                                            io_val = None
                                except:
                                    cpu_val = None
                                    has_io = False
                                    io_val = None
                                
                                apps.append({
                                    'name': subkey_name,
                                    'cpu_value': cpu_val,
                                    'has_io': has_io,
                                    'io_value': io_val if has_io else None
                                })
                        except FileNotFoundError:
                            continue
                    except OSError:
                        break
            
            # 更新UI
            self.root.after(0, self._update_app_list, apps)
            
        except Exception as e:
            self.root.after(0, self._load_error, str(e))
            
    def _update_app_list(self, apps):
        """更新应用列表"""
        self.applications = apps
        
        # 清空现有列表
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 添加新项目
        cpu_mapping = {
            1: "空闲",
            2: "正常",
            3: "高", 
            4: "实时",
            5: "低于正常",
            6: "高于正常"
        }
        
        io_mapping = {
            0: "非常低",
            1: "低",
            2: "正常",
            3: "高"
        }
        
        for i, app in enumerate(apps):
            cpu_text = cpu_mapping.get(app.get('cpu_value', 2), "未知")
            io_text = "未设置"
            if app.get('has_io'):
                io_text = io_mapping.get(app.get('io_value', 2), "未知")
            
            # 使用交替行颜色
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            
            self.tree.insert("", tk.END, values=(
                app['name'],
                cpu_text,
                io_text
            ), tags=(tag,))
        
        self.status_var.set(f"成功加载 {len(apps)} 个应用")
        
    def _load_error(self, error_msg):
        """加载错误处理"""
        self.status_var.set("加载失败")
        messagebox.showerror("错误", f"加载失败: {error_msg}")
        
    def add_application(self):
        """添加新应用"""
        dialog = AddPriorityDialogTkinter(self.root)
        self.root.wait_window(dialog.top)
        
        if dialog.result:
            app_name, cpu_value, io_value = dialog.result
            
            try:
                base_path = "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Image File Execution Options"
                
                # 创建注册表项
                app_key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, f"{base_path}\\{app_name}")
                winreg.CloseKey(app_key)
                
                # 创建PerfOptions子键
                perf_key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, f"{base_path}\\{app_name}\\PerfOptions")
                
                # 设置CPU优先级值
                winreg.SetValueEx(perf_key, "CpuPriorityClass", 0, winreg.REG_DWORD, cpu_value)
                
                # 设置IO优先级值（如果存在）
                if io_value is not None:
                    winreg.SetValueEx(perf_key, "IoPriority", 0, winreg.REG_DWORD, io_value)
                
                winreg.CloseKey(perf_key)
                
                self.status_var.set(f"成功为 {app_name} 添加优先级设置")
                self.load_applications()
                
            except Exception as e:
                messagebox.showerror("错误", f"添加失败: {str(e)}")
                
    def edit_application(self):
        """编辑应用"""
        selected = self.tree.selection()
        if not selected:
            return
            
        item = self.tree.item(selected[0])
        app_name = item['values'][0]
        
        # 查找应用信息
        app_info = None
        for app in self.applications:
            if app['name'] == app_name:
                app_info = app
                break
                
        if not app_info:
            return
            
        dialog = AddPriorityDialogTkinter(self.root, app_name, app_info)
        self.root.wait_window(dialog.top)
        
        if dialog.result:
            _, cpu_value, io_value = dialog.result
            
            try:
                base_path = "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Image File Execution Options"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                  f"{base_path}\\{app_name}\\PerfOptions",
                                  0, winreg.KEY_WRITE) as perf_key:
                    
                    # 更新CPU优先级值
                    winreg.SetValueEx(perf_key, "CpuPriorityClass", 0, winreg.REG_DWORD, cpu_value)
                    
                    # 更新或添加IO优先级值
                    if io_value is not None:
                        winreg.SetValueEx(perf_key, "IoPriority", 0, winreg.REG_DWORD, io_value)
                    else:
                        try:
                            winreg.DeleteValue(perf_key, "IoPriority")
                        except FileNotFoundError:
                            pass
                
                self.status_var.set(f"成功更新 {app_name} 的优先级设置")
                self.load_applications()
                
            except Exception as e:
                messagebox.showerror("错误", f"更新失败: {str(e)}")
                
    def remove_application(self):
        """删除应用"""
        selected = self.tree.selection()
        if not selected:
            return
            
        item = self.tree.item(selected[0])
        app_name = item['values'][0]
        
        result = messagebox.askyesno("确认删除", 
                                   f"确定要删除 {app_name} 的所有优先级设置吗?\n\n"
                                   "此操作将从注册表中删除相关设置，但不会删除应用程序本身。")
        
        if result:
            try:
                base_path = "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Image File Execution Options"
                winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, f"{base_path}\\{app_name}\\PerfOptions")
                winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, f"{base_path}\\{app_name}")
                
                self.status_var.set(f"已删除 {app_name} 的优先级设置")
                self.load_applications()
                
            except Exception as e:
                messagebox.showerror("错误", f"删除失败: {str(e)}")
                
    def export_configuration(self):
        """导出配置"""
        if not self.applications:
            messagebox.showinfo("提示", "没有可导出的配置")
            return
            
        filename = filedialog.asksaveasfilename(
            title="导出配置",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.applications, f, indent=2, ensure_ascii=False)
                    
                self.status_var.set(f"配置已导出到: {filename}")
                messagebox.showinfo("成功", "配置导出成功!")
                
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")
                
    def import_configuration(self):
        """导入配置"""
        filename = filedialog.askopenfilename(
            title="导入配置",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    configs = json.load(f)
                    
                result = messagebox.askyesno("确认导入",
                                           f"将导入 {len(configs)} 个应用程序配置。\n"
                                           "这将覆盖现有的同名配置，是否继续?")
                                           
                if result:
                    success_count = 0
                    for config in configs:
                        try:
                            app_name = config.get('name')
                            cpu_value = config.get('cpu_value', 2)
                            io_value = config.get('io_value') if config.get('has_io') else None
                            
                            if app_name:
                                base_path = "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Image File Execution Options"
                                perf_key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, f"{base_path}\\{app_name}\\PerfOptions")
                                winreg.SetValueEx(perf_key, "CpuPriorityClass", 0, winreg.REG_DWORD, cpu_value)
                                if io_value is not None:
                                    winreg.SetValueEx(perf_key, "IoPriority", 0, winreg.REG_DWORD, io_value)
                                winreg.CloseKey(perf_key)
                                success_count += 1
                        except:
                            continue
                    
                    self.status_var.set(f"成功导入 {success_count}/{len(configs)} 个配置")
                    self.load_applications()
                    
                    messagebox.showinfo("导入完成", 
                                      f"成功导入 {success_count} 个配置\n"
                                      f"失败: {len(configs) - success_count} 个")
                                      
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {str(e)}")

class AddPriorityDialogTkinter:
    def __init__(self, parent, app_name=None, app_info=None):
        self.top = tk.Toplevel(parent)
        self.top.title("修改优先级设置" if app_name else "添加新应用优先级")
        self.top.geometry("500x450")
        self.top.transient(parent)
        self.top.grab_set()
        
        # 使对话框居中
        self.center_dialog(parent, 500, 450)
        
        self.result = None
        self.app_name = app_name
        self.app_info = app_info
        
        # 设置字体
        default_font = ("微软雅黑", 10)
        
        # 主框架
        main_frame = tk.Frame(self.top, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 应用名称
        tk.Label(main_frame, text="应用名称 (exe):", font=default_font).grid(
            row=0, column=0, padx=5, pady=10, sticky=tk.W)
        
        self.app_name_var = tk.StringVar(value=app_name if app_name else "")
        app_entry = tk.Entry(main_frame, textvariable=self.app_name_var, width=40, font=default_font)
        app_entry.grid(row=0, column=1, padx=5, pady=10, sticky=tk.W)
        
        if app_name:
            app_entry.config(state=tk.DISABLED)
            
        # 自动添加.exe
        self.auto_exe_var = tk.BooleanVar(value=True)
        tk.Checkbutton(main_frame, text="自动添加.exe扩展名", variable=self.auto_exe_var,
                      font=default_font).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 分隔线
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(
            row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=20)
            
        # CPU优先级
        tk.Label(main_frame, text="CPU 优先级:", font=default_font).grid(
            row=3, column=0, padx=5, pady=10, sticky=tk.W)
        
        self.cpu_var = tk.StringVar()
        cpu_combo = ttk.Combobox(main_frame, textvariable=self.cpu_var, state="readonly", width=30, font=default_font)
        cpu_combo.grid(row=3, column=1, padx=5, pady=10, sticky=tk.W)
        
        cpu_options = [
            ("空闲 (1) - 最低优先级", 1),
            ("正常 (2) - 默认优先级", 2),
            ("高 (3) - 推荐用于游戏", 3),
            ("实时 (4) - 谨慎使用", 4),
            ("低于正常 (5)", 5),
            ("高于正常 (6)", 6)
        ]
        
        cpu_combo['values'] = [opt[0] for opt in cpu_options]
        self.cpu_values = {opt[0]: opt[1] for opt in cpu_options}
        cpu_combo.current(1)  # 默认选择正常
        
        # 分隔线
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(
            row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=20)
            
        # I/O优先级
        self.io_enabled_var = tk.BooleanVar(value=False)
        io_check = tk.Checkbutton(main_frame, text="启用 I/O 优先级设置", 
                                 variable=self.io_enabled_var, font=default_font)
        io_check.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)
        
        tk.Label(main_frame, text="I/O 优先级:", font=default_font).grid(
            row=6, column=0, padx=5, pady=10, sticky=tk.W)
        
        self.io_var = tk.StringVar()
        io_combo = ttk.Combobox(main_frame, textvariable=self.io_var, state="readonly", width=30, font=default_font)
        io_combo.grid(row=6, column=1, padx=5, pady=10, sticky=tk.W)
        
        io_options = [
            ("非常低 (0) - 后台任务", 0),
            ("低 (1)", 1),
            ("正常 (2) - 默认", 2),
            ("高 (3) - 推荐用于游戏", 3)
        ]
        
        io_combo['values'] = [opt[0] for opt in io_options]
        self.io_values = {opt[0]: opt[1] for opt in io_options}
        io_combo.current(2)  # 默认选择正常
        io_combo.config(state=tk.DISABLED)
        
        # 绑定I/O启用状态
        def toggle_io_state():
            io_combo.config(state=tk.NORMAL if self.io_enabled_var.get() else tk.DISABLED)
            
        self.io_enabled_var.trace('w', lambda *args: toggle_io_state())
        
        # 如果编辑已有设置，加载值
        if app_name and app_info:
            self.load_existing_values(app_info)
        
        # 按钮区域
        button_frame = tk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=30)
        
        tk.Button(button_frame, text="确定", width=10, font=default_font,
                 command=self.on_ok, bg='#4CAF50', fg='white').pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="取消", width=10, font=default_font,
                 command=self.on_cancel, bg='#f44336', fg='white').pack(side=tk.LEFT, padx=10)
                 
    def center_dialog(self, parent, width, height):
        """将对话框居中显示"""
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        
        self.top.geometry(f'{width}x{height}+{x}+{y}')
        
    def load_existing_values(self, app_info):
        """加载已有值"""
        cpu_value = app_info.get('cpu_value', 2)
        has_io = app_info.get('has_io', False)
        io_value = app_info.get('io_value', 2)
        
        # 设置CPU优先级
        for text, value in self.cpu_values.items():
            if value == cpu_value:
                self.cpu_var.set(text)
                break
                
        # 设置IO优先级
        if has_io:
            self.io_enabled_var.set(True)
            for text, value in self.io_values.items():
                if value == io_value:
                    self.io_var.set(text)
                    break
                    
    def on_ok(self):
        """确定按钮"""
        app_name = self.app_name_var.get().strip()
        
        if not app_name:
            messagebox.showwarning("警告", "应用名称不能为空!")
            return
            
        # 自动添加.exe扩展名
        if self.auto_exe_var.get() and not app_name.lower().endswith('.exe'):
            app_name += '.exe'
            
        # 验证应用名称格式
        if not app_name.lower().endswith('.exe'):
            result = messagebox.askyesno("确认", 
                                       "应用名称没有包含.exe扩展名，确认继续吗?\n"
                                       "建议添加.exe扩展名以确保正确识别。")
            if not result:
                return
                
        # 获取CPU值
        cpu_text = self.cpu_var.get()
        cpu_value = self.cpu_values.get(cpu_text, 2)
        
        # 获取IO值
        io_value = None
        if self.io_enabled_var.get():
            io_text = self.io_var.get()
            io_value = self.io_values.get(io_text, 2)
            
        self.result = (app_name, cpu_value, io_value)
        self.top.destroy()
        
    def on_cancel(self):
        """取消按钮"""
        self.top.destroy()

if __name__ == "__main__":
    # 检查管理员权限
    if not is_admin():
        run_as_admin()
        sys.exit(0)
    
    # 创建主窗口
    root = tk.Tk()
    app = AppCpuPriorityToolsTkinter(root)
    
    # 运行主循环
    root.mainloop()