import os
import sys
import shutil
import ctypes
import winreg
import time
import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path

APP_NAME = "Offline Face Photo Organizer"
APP_DIR_NAME = "Offline Face Photo Organizer"
APP_VERSION = "1.0.0"
PUBLISHER = "AI Photo Organizer Studio"
EXE_NAME = "OfflineFacePhotoOrganizer.exe"
REG_KEY_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\OfflineFacePhotoOrganizer"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def run_as_admin():
    if not is_admin():
        try:
            params = " ".join([f'"{a}"' for a in sys.argv[1:]])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        except Exception as e:
            print(f"Elevation error: {e}")
        sys.exit(0)

def create_shortcut(target_path, shortcut_path, description="", args=""):
    try:
        ps_cmd = (
            f"$s=(New-Object -COM WScript.Shell).CreateShortcut('{shortcut_path}'); "
            f"$s.TargetPath='{target_path}'; "
            f"$s.WorkingDirectory='{Path(target_path).parent}'; "
            f"$s.Arguments='{args}'; "
            f"$s.Description='{description}'; "
            f"$s.Save()"
        )
        subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
    except Exception as e:
        print(f"Error creating shortcut: {e}")

def register_in_control_panel(install_dir, uninstall_exe):
    try:
        key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, REG_KEY_PATH, 0, winreg.KEY_ALL_ACCESS | winreg.KEY_WOW64_64KEY)
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_dir))
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstall_exe}" --uninstall')
        winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, f'"{uninstall_exe}" --uninstall --quiet')
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f'"{install_dir}\\{EXE_NAME}"')
        winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, 200000)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Registry registration error: {e}")

def unregister_from_control_panel():
    try:
        winreg.DeleteKeyEx(winreg.HKEY_LOCAL_MACHINE, REG_KEY_PATH, winreg.KEY_WOW64_64KEY, 0)
    except Exception as e:
        print(f"Registry unregistration error: {e}")

def run_uninstaller():
    args = [a.lower() for a in sys.argv]
    is_quiet = "--quiet" in args
    is_temp_execution = "--running-from-temp" in args

    target_install_dir = None
    if is_temp_execution:
        for i, arg in enumerate(sys.argv):
            if arg.lower() == "--running-from-temp" and i + 1 < len(sys.argv):
                target_install_dir = sys.argv[i + 1]
                break

    if not target_install_dir:
        target_install_dir = str(Path(sys.executable).parent)

    # Step A: If launched from the installation folder, copy self to TEMP and re-launch
    if not is_temp_execution:
        run_as_admin()

        if not is_quiet:
            root = tk.Tk()
            root.withdraw()
            ans = messagebox.askyesno(
                "Uninstall Offline Face Photo Organizer",
                f"Are you sure you want to completely remove {APP_NAME} and all of its components?"
            )
            root.destroy()
            if not ans:
                sys.exit(0)

        temp_dir = Path(os.environ.get("TEMP", r"C:\Windows\Temp"))
        temp_uninstaller = temp_dir / "OfflineFacePhotoOrganizer_uninstaller.exe"
        try:
            shutil.copy2(sys.executable, temp_uninstaller)
            cmd = f'"{temp_uninstaller}" --uninstall --running-from-temp "{target_install_dir}"'
            if is_quiet:
                cmd += " --quiet"
            subprocess.Popen(cmd, shell=True)
        except Exception as e:
            print(f"Error launching temp uninstaller: {e}")
        sys.exit(0)

    # Step B: Executing from TEMP with full permissions to remove app files & registry
    run_as_admin()

    # 1. Terminate running app instances
    try:
        subprocess.run(["taskkill", "/F", "/IM", EXE_NAME, "/T"], capture_output=True)
    except Exception:
        pass

    time.sleep(1)

    # 2. Remove Shortcuts
    desktop_shortcut = Path(os.path.expanduser("~/Desktop")) / f"{APP_NAME}.lnk"
    start_menu_app = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"{APP_NAME}.lnk"
    start_menu_uninst = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"Uninstall {APP_NAME}.lnk"

    for sc in [desktop_shortcut, start_menu_app, start_menu_uninst]:
        try:
            if sc.exists():
                sc.unlink()
        except Exception as e:
            print(f"Error removing shortcut {sc}: {e}")

    # 3. Unregister from Windows Registry (Control Panel Add/Remove Programs)
    unregister_from_control_panel()

    # 4. Remove Target Program Files Installation Directory
    install_path = Path(target_install_dir)
    if install_path.exists():
        try:
            shutil.rmtree(install_path, ignore_errors=True)
        except Exception as e:
            print(f"shutil.rmtree error: {e}")

        if install_path.exists():
            subprocess.run(f'cmd /c "rmdir /s /q \"{install_path}\""', shell=True, capture_output=True)

    if not is_quiet:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "Uninstall Complete",
            f"{APP_NAME} has been successfully removed from your computer."
        )
        root.destroy()

    sys.exit(0)

class InstallerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION} Setup")
        self.root.geometry("520x360")
        self.root.resizable(False, False)

        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        self.install_dir = tk.StringVar(value=os.path.join(program_files, APP_DIR_NAME))
        self.create_desktop = tk.BooleanVar(value=True)
        self.create_start_menu = tk.BooleanVar(value=True)

        self.build_ui()

    def build_ui(self):
        header = tk.Frame(self.root, bg="#0f172a", height=70)
        header.pack(fill="x")
        title_lbl = tk.Label(header, text=f"Install {APP_NAME}", font=("Segoe UI", 14, "bold"), fg="#ffffff", bg="#0f172a")
        title_lbl.pack(anchor="w", padx=20, pady=(15, 0))
        sub_lbl = tk.Label(header, text="Offline AI Face Recognition & Photo Organizer Engine", font=("Segoe UI", 9), fg="#94a3b8", bg="#0f172a")
        sub_lbl.pack(anchor="w", padx=20)

        body = tk.Frame(self.root, padx=20, pady=20)
        body.pack(fill="both", expand=True)

        dir_lbl = tk.Label(body, text="Destination Folder (Installs to Windows Program Files):", font=("Segoe UI", 9, "bold"))
        dir_lbl.pack(anchor="w", pady=(0, 5))

        entry_frame = tk.Frame(body)
        entry_frame.pack(fill="x", pady=(0, 15))

        dir_entry = tk.Entry(entry_frame, textvariable=self.install_dir, font=("Consolas", 9))
        dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        browse_btn = tk.Button(entry_frame, text="Browse...", command=self.browse_dir)
        browse_btn.pack(side="right")

        chk1 = tk.Checkbutton(body, text="Create Desktop Shortcut", variable=self.create_desktop, font=("Segoe UI", 9))
        chk1.pack(anchor="w", pady=2)

        chk2 = tk.Checkbutton(body, text="Create Start Menu Shortcuts (App & Uninstaller)", variable=self.create_start_menu, font=("Segoe UI", 9))
        chk2.pack(anchor="w", pady=2)

        info_lbl = tk.Label(body, text="The application will be registered in Windows Control Panel (Add/Remove Programs).", font=("Segoe UI", 8), fg="#64748b", justify="left")
        info_lbl.pack(anchor="w", pady=(15, 0))

        footer = tk.Frame(self.root, bg="#f1f5f9", height=50)
        footer.pack(fill="x", side="bottom")

        cancel_btn = tk.Button(footer, text="Cancel", width=10, command=self.root.quit)
        cancel_btn.pack(side="right", padx=15, pady=10)

        install_btn = tk.Button(footer, text="Install Now", width=12, bg="#0284c7", fg="white", font=("Segoe UI", 9, "bold"), command=self.perform_installation)
        install_btn.pack(side="right", padx=(0, 5), pady=10)

    def browse_dir(self):
        d = filedialog.askdirectory(title="Select Destination Folder")
        if d:
            self.install_dir.set(d)

    def perform_installation(self):
        target_path = Path(self.install_dir.get().strip())

        try:
            target_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            messagebox.showerror("Permission Error", "Administrator rights required to install to Program Files. Please run installer as Administrator.")
            return

        if getattr(sys, 'frozen', False):
            payload_dir = Path(getattr(sys, '_MEIPASS', '.')) / "payload"
        else:
            payload_dir = Path(__file__).parent / "dist" / "OfflineFacePhotoOrganizer"

        if not payload_dir.exists():
            messagebox.showerror("Error", f"Installation payload not found at {payload_dir}")
            return

        try:
            for item in payload_dir.iterdir():
                dest = target_path / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
        except Exception as e:
            messagebox.showerror("Installation Failed", f"Error copying files: {e}")
            return

        target_exe = target_path / EXE_NAME
        uninstall_exe = target_path / "uninstall.exe"

        if getattr(sys, 'frozen', False):
            try:
                shutil.copy2(sys.executable, uninstall_exe)
            except Exception as e:
                print(f"Error creating uninstaller binary: {e}")

        if self.create_desktop.get():
            desktop_path = Path(os.path.expanduser("~/Desktop")) / f"{APP_NAME}.lnk"
            create_shortcut(str(target_exe), str(desktop_path), APP_NAME)

        if self.create_start_menu.get():
            start_menu_app = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"{APP_NAME}.lnk"
            start_menu_uninst = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"Uninstall {APP_NAME}.lnk"
            create_shortcut(str(target_exe), str(start_menu_app), APP_NAME)
            create_shortcut(str(uninstall_exe), str(start_menu_uninst), f"Uninstall {APP_NAME}", args="--uninstall")

        register_in_control_panel(target_path, uninstall_exe)

        messagebox.showinfo("Installation Complete", f"{APP_NAME} has been successfully installed in:\n{target_path}\n\nIt is now registered in Windows Control Panel.")
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    exe_name = Path(sys.executable).name.lower()
    args = [a.lower() for a in sys.argv]

    is_uninstall = (
        "uninstall" in exe_name or
        "--uninstall" in args or
        "-uninstall" in args or
        "/uninstall" in args
    )

    if is_uninstall:
        run_uninstaller()
    else:
        run_as_admin()
        gui = InstallerGUI()
        gui.run()
