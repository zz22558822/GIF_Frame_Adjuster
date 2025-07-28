import sys
import subprocess
import re
import os
import shutil
import requests
import base64
from alive_progress import alive_bar

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QTextEdit, QMessageBox, QFrame, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDesktopServices, QIntValidator, QCursor, QIcon, QPixmap

# --- 嵌入式圖示資料 ---
LOGO_ICON_BASE64 = """
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ZbqzUNQc8Ag+VLN2QZXuIEREo8VHADF2ZNWi3UYgeQmAh3VnoTETiPxQkLaMF38icjq2ANiofHPVBwXyUwD5urPQiJ1QSu49snrhn3QHISKKBrYA2OjImvlPmB6Zo5Q8pjsLRUwAPCxIu4gXfyJyE7YAaFK+pXKNCB4EUKw7C12IOioK9x9bPX+H7iRERNHGFgBNjqxesNkIJF8EUd8B4Nedh/5Kryh8ObnPuIgXfyJyK7YAxIEZW6vLPGbomwKs150lwYlS8j9+0/vF+rXzTusOQ0QUSywA4sjwVMLyHUAt0p0lAe00RH3+8Nr5e3QHISKyAwuAeCOiyrZUrlPA11kI2OINgfz7sTULn9MdhIjITiwA4tVGMcouqbodwL8qoFx3HLdRCntFqa8eXTV/k+4sREQ6sACIdxvFKLukcq0S9fdQuEZ3HKcTyKsAvn1s9YI/QCnRnYeISBcWAA5Stnn/exTU5wDcCK4vMBKDAH5jmvL92nULuVIjERFYADhS6abqIq8K3a2A+wDM0J0njh0S4FEj5P/5keuWtekOQ0QUT1gAOJmIKt9aebWIuhfA9QCydEeKA+0Afg+RXxxdu/AN3WGIiOIVCwCXKN1el+r19bzfUFgvom4CkKk7k426lJLnTMGTKX3e56s3zOPESkREFlgAuNCC5/dnDATVNUrJKgFWK6gS3ZmiTlCjgC2mUluB1J3H1swc0h2JiMhJWAAkgJl/qJojhvkBQK1QwHIA43VnGoUmQL0CwU6PEdxas3pxve5AREROxgIgAc3etK88ZBjLIXgvRC2CknkAMnTnOkc3oKoEsk8JdoVMzyvHr5vXqDsUEZGbsACgs3MNHJimFBZCzDmAmq6UTBNTlUJhKmIz5NAPqAZA6gHUCXBciaoOwlNVt3ZuQwx+HhERnYMFAIV11fbt3hP+wolG0CgAzHEwzEIlqsBUyDQEuQAgUKmApJ3ztgEFDEEgpkIXlPTCNNo8ymyDMtokGGo/sndhMzYqU9NhERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERHROZTuAERECSwXQBmAYgBTARQB8ALIPvt6P4BBAN0ABgDUATh29r9Ddocld2EBQERkn9kAVgN4D4ClAGaM8nNMALUAdpzdtgFoGXs8IiIiipaFAP4LwxdsidHmB/BbDBcVREREpEkKgPsB7EHsLvrn2/7JjoMjIiKiv5YM4C7E9m4/3HZ57A+RiIiIzrUawHHoufALAB+GWx6IIuLVHYCIEsIcAEJBcD4AABQuSURBVOsAzAMwHsA4AK0Y7ri2G8AWDPdsd6IJAH4IYIPmHG+CIwOIiGxnAMg7u00BMP3sNvWcP0/Slk4PA8CdAGoQ2R3sDgCX6Qg6BpcDOAl9d/3nbt+I8bGSy3AYIFF4XgAlGB6rPRPDF/eJACad/W/O2S1rBJ/ZB6Adw3e/bef8/3Xv2nxROQI9LgLwm7P/HakHAXwGQCCqiaLvMwC+g/gp7FYD2Ko7BBGRE+UBuBbAFwH8GsABDDep6rqjawDwHIbv7NZj9GPG7XYTgF6M7dj/BCDV7uAj8DXov+M/dwtiuBAlIqIIFGG4ifohDF/sQ9B/IrfamgFUAPg0hp+nx5trMXznHo1j/ZXN2SP1Dej/Hrx72xPTIyYicjgDwBUA/hPAPgzPpqb7xD3WrRbADwBcdfb4dJoNoAvRPb71th6Bte9D/9/5+bYfxPKgiYicyABwNYafK5+G/hN1LLd6AF/H8LzyOmyzyDea7TDiZ7TS30P/3/GFtptjeNxERI4yG8A3ATRC/8nZ7s0P4JcYnpTGLh+IwXG8s62z8Tgu5DLo7Q8SbjMxPLSSiChhGQCuA/AC3NG8P5ataoy/y5HaHMXs795+YuNxnM9UAGeg/+/0Qtuh2B06EVF8ywTweSTm3f6Fts+N6Tc6MpkYXrLWjRc4A8DLF8gVL9vDMTt6IqI4lQfgqxgeR6/7JBxPWwDDIxzsckOMjuOdrc++Q/kbnwyTK162O2N29EREcSYdwAMAOqH/5BuP26bR/2pH5XNRzH6hLcO2o/mLSXDGd6w0RsdPLhcv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
"""



# --- FFmpeg 及 7-Zip 自動安裝相關函式 ---

def download_file_with_progress(url, local_filename):
    print(f"開始下載 {os.path.basename(local_filename)}...")
    os.makedirs(os.path.dirname(local_filename), exist_ok=True)
    try:
        with requests.get(url, stream=True) as r, open(local_filename, 'wb') as f:
            r.raise_for_status()
            file_size = int(r.headers.get('content-length', 0))
            chunk_size = 8192
            bar_length = file_size // chunk_size if file_size > chunk_size else 1
            if file_size == 0:
                print("警告: 檔案大小未知，可能無法顯示精確進度條。")
                bar_length = 100

            with alive_bar(bar_length, bar='smooth', spinner='dots_waves', length=40, enrich_print=False) as bar:
                bar.text(f'下載 {os.path.basename(local_filename)} 進度')
                for chunk in r.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
                    bar()
                bar(bar_length)

        print(f"成功下載 {os.path.basename(local_filename)} 到 {local_filename}")
        return local_filename
    except requests.exceptions.RequestException as e:
        print(f"下載失敗：{e}")
        return None
    except Exception as e:
        print(f"下載時發生未知錯誤：{e}")
        return None

def extract_and_rename_archive(archive_path, target_directory, new_foldername, seven_zip_exec_path):
    print(f"正在解壓縮 {os.path.basename(archive_path)}...")
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)
    
    if not os.path.exists(seven_zip_exec_path):
        print(f"錯誤：解壓縮工具 '{seven_zip_exec_path}' 不存在。無法進行解壓縮。")
        return None

    try:
        subprocess.run([seven_zip_exec_path, 'x', archive_path, f'-o{target_directory}', '-y'], check=True, capture_output=True, text=True)
        print(f"成功解壓縮 {os.path.basename(archive_path)}")
        
        extracted_items = os.listdir(target_directory)
        extracted_dirs = [item for item in extracted_items if os.path.isdir(os.path.join(target_directory, item))]
        
        old_folder_path = None
        if 'ffmpeg.7z' in archive_path:
            for folder_name in extracted_dirs:
                if folder_name.startswith('ffmpeg-'):
                    old_folder_path = os.path.join(target_directory, folder_name)
                    break
        elif '7za920.zip' in archive_path:
            found_7za = False
            for root, _, files in os.walk(target_directory):
                if '7za.exe' in files:
                    old_folder_path = root
                    found_7za = True
                    break
            if not found_7za:
                raise FileNotFoundError("未找到解壓後 7za.exe 所在資料夾。")
        else:
            if len(extracted_dirs) == 1:
                old_folder_path = os.path.join(target_directory, extracted_dirs[0])
            else:
                if extracted_dirs:
                    old_folder_path = os.path.join(target_directory, extracted_dirs[0])
                else:
                    raise FileNotFoundError("未找到解壓後的文件夾")


        if not old_folder_path:
            raise FileNotFoundError("未找到解壓後的文件夾，無法進行重命名。")
        
        new_folder_path = os.path.join(target_directory, new_foldername)
        
        if os.path.exists(new_folder_path):
            print(f"刪除舊的 '{new_foldername}' 資料夾...")
            shutil.rmtree(new_folder_path)
        
        if new_foldername == '7z' and old_folder_path == target_directory:
            pass # 如果 7za.exe 直接位於 target_directory 中，則不需重新命名
        else:
            os.rename(old_folder_path, new_folder_path)
            print(f"已將解壓縮的資料夾重命名為 '{new_foldername}'。")
        
        return new_folder_path

    except subprocess.CalledProcessError as e:
        print(f"解壓縮失敗，錯誤代碼 {e.returncode}：{e.stderr}")
        print(f"FFmpeg stderr: {e.stderr}")
        return None
    except FileNotFoundError as e:
        print(f"解壓縮失敗：{e}")
        return None
    except Exception as e:
        print(f"解壓縮時發生未知錯誤：{e}")
        return None

def get_gif_info_backend(ffprobe_path, input_gif_path):
    """
    使用指定的 ffprobe 路徑獲取 GIF 的平均幀率、總時長和計算總幀數。
    同時獲取檔案大小。
    返回一個字典
    """
    info = {
        "avg_fps": None,
        "duration": None,
        "total_frames": None,
        "file_size_mib": None,
        "error": None
    }

    try:
        # 1. 獲取幀率和時長
        command_info = [
            ffprobe_path,
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=avg_frame_rate,duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            input_gif_path
        ]
        result_info = subprocess.run(command_info, capture_output=True, text=True, check=True, encoding='utf-8')
        output_lines = result_info.stdout.strip().split('\n')

        if len(output_lines) >= 2:
            avg_frame_rate_str = output_lines[0]
            duration_str = output_lines[1]

            match = re.match(r'(\d+)/(\d+)', avg_frame_rate_str)
            if match:
                numerator = int(match.group(1))
                denominator = int(match.group(2))
                info["avg_fps"] = numerator / denominator if denominator != 0 else 0
            else:
                info["error"] = f"警告: 無法解析平均幀率: {avg_frame_rate_str}"
            
            info["duration"] = float(duration_str)
        else:
            info["error"] = f"警告: 無法完全解析 ffprobe 基本資訊輸出。\n{result_info.stdout}"

    except subprocess.CalledProcessError as e:
        info["error"] = f"執行 {ffprobe_path} 獲取基本資訊時發生錯誤：{e.stderr}"
    except ValueError as e:
        info["error"] = f"解析 {ffprobe_path} 輸出時發生錯誤：{e}"
    except Exception as e:
        info["error"] = f"獲取 GIF 資訊時發生未知錯誤：{e}"

    # 2. 獲取檔案大小
    try:
        file_size_bytes = os.path.getsize(input_gif_path)
        info["file_size_mib"] = file_size_bytes / (1024 * 1024)
    except Exception as e:
        info["error"] = (info["error"] + "\n" if info["error"] else "") + f"警告: 無法獲取檔案大小: {e}"

    if info["avg_fps"] is not None and info["duration"] is not None:
        info["total_frames"] = round(info["avg_fps"] * info["duration"])

    return info

def process_gif_backend(ffmpeg_path, input_gif_path, output_gif_path, target_fps, progress_callback=None, show_progress_messages=True):
    """
    根據目標幀數計算 FPS，並執行 FFmpeg 命令。
    現在接受進度回調，並可選擇是否顯示詳細進度訊息。
    """
    ffmpeg_command = [
        ffmpeg_path,
        '-y', # 自動覆蓋輸出檔案
        '-i', input_gif_path,
        '-vf', f"fps={target_fps:.15f},split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
        output_gif_path
    ]

    ffmpeg_output_log = []
    try:
        process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        
        while True:
            output_line = process.stderr.readline()
            if output_line == '' and process.poll() is not None:
                break
            if output_line:
                ffmpeg_output_log.append(output_line.strip())
                # 僅當 show_progress_messages 為 True 時才將 FFmpeg 輸出發送給 GUI
                if progress_callback and show_progress_messages: # <--- 這裡新增了條件判斷
                    progress_callback(output_line.strip(), -1) # -1 表示未知百分比

        return_code = process.poll()
        if return_code == 0:
            return True, "FFmpeg 處理完成！", ffmpeg_output_log
        else:
            error_message = f"FFmpeg 執行失敗，返回碼：{return_code}\n{''.join(ffmpeg_output_log[-10:])}"
            return False, error_message, ffmpeg_output_log

    except FileNotFoundError:
        return False, "錯誤：找不到 'ffmpeg' 命令。請確認 FFmpeg 已安裝並在 PATH 中。", ffmpeg_output_log
    except Exception as e:
        return False, f"執行 FFmpeg 時發生未知錯誤：{e}", ffmpeg_output_log

# --- FFmpeg/7z 安裝及處理的 QThread 執行器 ---

class InstallerThread(QThread):
    progress_signal = pyqtSignal(str, bool) 
    completion_signal = pyqtSignal(bool, str, str, str)

    def run(self):
        self.progress_signal.emit("正在檢查並安裝 7-Zip (7za.exe) 依賴項目...", False)
        seven_zip_path = self._check_and_install_7z_internal()
        if seven_zip_path is None:
            self.completion_signal.emit(False, "7-Zip (7za.exe) 未成功配置，程式無法繼續執行。", "", "")
            return

        # 在 7-Zip 步驟完成後加入分隔
        self.progress_signal.emit("", False) # 加入空行作為分隔
        
        self.progress_signal.emit("正在檢查並安裝 FFmpeg 和 FFprobe 依賴項目...", False)
        ffmpeg_exec, ffprobe_exec = self._check_and_install_ffmpeg_internal(seven_zip_path)

        if ffmpeg_exec is None or ffprobe_exec is None:
            self.completion_signal.emit(False, "FFmpeg/FFprobe 未成功配置，程式無法繼續執行。", "", "")
        else:
            # 在 FFmpeg 步驟完成後加入分隔
            self.progress_signal.emit("", False) # 加入空行作為分隔
            self.completion_signal.emit(True, "✔️ 依賴項目檢測正常", ffmpeg_exec, ffprobe_exec)

    def _download_file_with_progress_internal(self, url, local_filename):
        self.progress_signal.emit(f"開始下載 {os.path.basename(local_filename)}...", False)
        os.makedirs(os.path.dirname(local_filename), exist_ok=True)
        try:
            with requests.get(url, stream=True) as r, open(local_filename, 'wb') as f:
                r.raise_for_status()
                file_size = int(r.headers.get('content-length', 0))
                downloaded_size = 0
                chunk_size = 8192

                for chunk in r.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    if file_size > 0:
                        self.progress_signal.emit(
                            f"下載 {os.path.basename(local_filename)} 進度: {downloaded_size / (1024*1024):.2f}/{file_size / (1024*1024):.2f} MiB",
                            True
                        )
                    else:
                        self.progress_signal.emit(
                            f"下載 {os.path.basename(local_filename)} 進度: {downloaded_size / (1024*1024):.2f} MiB",
                            True
                        )

            self.progress_signal.emit(f"成功下載 {os.path.basename(local_filename)}。", False)
            return local_filename
        except requests.exceptions.RequestException as e:
            self.progress_signal.emit(f"下載失敗：{os.path.basename(local_filename)} - {e}", False)
            return None
        except Exception as e:
            self.progress_signal.emit(f"下載 {os.path.basename(local_filename)} 時發生未知錯誤：{e}", False)
            return None

    def _extract_and_rename_archive_internal(self, archive_path, target_directory, new_foldername, seven_zip_exec_path):
        self.progress_signal.emit(f"正在解壓縮 {os.path.basename(archive_path)}...", False)
        if not os.path.exists(target_directory):
            os.makedirs(target_directory)
        
        if not os.path.exists(seven_zip_exec_path):
            self.progress_signal.emit(f"錯誤：解壓縮工具 '{seven_zip_exec_path}' 不存在。", False)
            return None

        try:
            subprocess.run([seven_zip_exec_path, 'x', archive_path, f'-o{target_directory}', '-y'], check=True, capture_output=True, text=True)
            self.progress_signal.emit(f"成功解壓縮 {os.path.basename(archive_path)}。", False)
            
            extracted_items = os.listdir(target_directory)
            extracted_dirs = [item for item in extracted_items if os.path.isdir(os.path.join(target_directory, item))]
            
            old_folder_path = None
            if 'ffmpeg.7z' in archive_path:
                for folder_name in extracted_dirs:
                    if folder_name.startswith('ffmpeg-'):
                        old_folder_path = os.path.join(target_directory, folder_name)
                        break
            elif '7za920.zip' in archive_path:
                found_7za = False
                for root, _, files in os.walk(target_directory):
                    if '7za.exe' in files:
                        old_folder_path = root
                        found_7za = True
                        break
                if not found_7za:
                    raise FileNotFoundError("未找到解壓後 7za.exe 所在資料夾。")
            else:
                if len(extracted_dirs) == 1:
                    old_folder_path = os.path.join(target_directory, extracted_dirs[0])
                else:
                    if extracted_dirs:
                        old_folder_path = os.path.join(target_directory, extracted_dirs[0])
                    else:
                        raise FileNotFoundError("未找到解壓後的文件夾")


            if not old_folder_path:
                raise FileNotFoundError("未找到解壓後的文件夾，無法進行重命名。")
            
            new_folder_path = os.path.join(target_directory, new_foldername)
            
            if os.path.exists(new_folder_path):
                self.progress_signal.emit(f"刪除舊的 '{new_foldername}' 資料夾...", False)
                shutil.rmtree(new_folder_path)
            
            if new_foldername == '7z' and old_folder_path == target_directory:
                pass
            else:
                os.rename(old_folder_path, new_folder_path)
                self.progress_signal.emit(f"已將解壓縮的資料夾重命名為 '{new_foldername}'。", False)
            
            return new_folder_path

        except subprocess.CalledProcessError as e:
            self.progress_signal.emit(f"解壓縮失敗，錯誤代碼 {e.returncode}：{e.stderr}", False)
            return None
        except FileNotFoundError as e:
            self.progress_signal.emit(f"解壓縮失敗：{e}", False)
            return None
        except Exception as e:
            self.progress_signal.emit(f"解壓縮時發生未知錯誤：{e}", False)
            return None

    def _check_and_install_7z_internal(self):
        seven_zip_dir = os.path.join('.', 'driver', '7z')
        seven_zip_exec_path = os.path.join(seven_zip_dir, '7za.exe')

        if os.path.exists(seven_zip_exec_path):
            # self.progress_signal.emit("7-Zip (7za.exe) 已存在。", False)
            return seven_zip_exec_path

        self.progress_signal.emit("偵測到 7-Zip (7za.exe) 不存在，將嘗試自動安裝...", False)
        
        seven_zip_download_url = 'https://www.7-zip.org/a/7za920.zip'
        seven_zip_archive_path = os.path.join(seven_zip_dir, '7za920.zip')

        os.makedirs(seven_zip_dir, exist_ok=True)

        if not self._download_file_with_progress_internal(seven_zip_download_url, seven_zip_archive_path):
            self.progress_signal.emit("7-Zip 壓縮檔下載失敗，無法繼續安裝。", False)
            return None
        
        try:
            import zipfile
            with zipfile.ZipFile(seven_zip_archive_path, 'r') as zf:
                zf.extractall(seven_zip_dir)
            self.progress_signal.emit(f"成功解壓縮 {os.path.basename(seven_zip_archive_path)}。", False)
            
            if os.path.exists(seven_zip_exec_path):
                self.progress_signal.emit("7-Zip (7za.exe) 安裝完成。", False)
                # 這裡加入一個分隔符
                self.progress_signal.emit("", False)
                return seven_zip_exec_path
            else:
                for root, _, files in os.walk(seven_zip_dir):
                    if '7za.exe' in files:
                        found_7za_path = os.path.join(root, '7za.exe')
                        if found_7za_path != seven_zip_exec_path:
                            shutil.move(found_7za_path, seven_zip_exec_path)
                            self.progress_signal.emit(f"已將 7za.exe 移動到正確位置。", False)
                        self.progress_signal.emit("", False) # 也在此處加入分隔符
                        return seven_zip_exec_path
                self.progress_signal.emit("錯誤：解壓縮後未能找到 7za.exe。", False)
                return None

        except zipfile.BadZipFile:
            self.progress_signal.emit(f"錯誤：下載的 7-Zip 檔案不是有效的 ZIP 檔案。", False)
            return None
        except Exception as e:
            self.progress_signal.emit(f"7-Zip 解壓縮時發生錯誤：{e}", False)
            return None
        finally:
            if os.path.exists(seven_zip_archive_path):
                try:
                    os.remove(seven_zip_archive_path)
                    # self.progress_signal.emit(f"已刪除下載的 7-Zip 壓縮檔。", False)
                except Exception as e:
                    self.progress_signal.emit(f"刪除 7-Zip 壓縮檔失敗：{e}", False)

    def _check_and_install_ffmpeg_internal(self, seven_zip_exec_path):
        ffmpeg_exec_path = os.path.join('.', 'driver', 'ffmpeg', 'bin', 'ffmpeg.exe')
        ffprobe_exec_path = os.path.join('.', 'driver', 'ffmpeg', 'bin', 'ffprobe.exe')

        if os.path.exists(ffmpeg_exec_path) and os.path.exists(ffprobe_exec_path):
            # self.progress_signal.emit("FFmpeg 和 FFprobe 已存在。", False)
            return ffmpeg_exec_path, ffprobe_exec_path

        self.progress_signal.emit("偵測到 FFmpeg 或 FFprobe 不存在，將嘗試自動安裝...", False)
        
        driver_dir = './driver/'
        ffmpeg_archive_path = os.path.join(driver_dir, 'ffmpeg.7z')
        
        ffmpeg_download_url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z'

        if not self._download_file_with_progress_internal(ffmpeg_download_url, ffmpeg_archive_path):
            self.progress_signal.emit("FFmpeg 壓縮檔下載失敗，無法繼續安裝。", False)
            return None, None
        
        if not self._extract_and_rename_archive_internal(ffmpeg_archive_path, driver_dir, 'ffmpeg', seven_zip_exec_path):
            self.progress_signal.emit("FFmpeg 解壓縮或重命名失敗，無法繼續安裝。", False)
            return None, None

        if os.path.exists(ffmpeg_archive_path):
            try:
                os.remove(ffmpeg_archive_path)
                # self.progress_signal.emit(f"已刪除下載的 FFmpeg 壓縮檔。", False)
            except Exception as e:
                self.progress_signal.emit(f"刪除 FFmpeg 壓縮檔失敗：{e}", False)

        if os.path.exists(ffmpeg_exec_path) and os.path.exists(ffprobe_exec_path):
            self.progress_signal.emit("FFmpeg 和 FFprobe 安裝完成。", False)
            return ffmpeg_exec_path, ffprobe_exec_path
        else:
            self.progress_signal.emit("FFmpeg 和 FFprobe 安裝失敗，請檢查日誌。", False)
            return None, None


# --- GIF 處理的 QThread 執行器 ---

class GIFProcessorThread(QThread):
    progress_signal = pyqtSignal(str, float) # 日誌訊息, 百分比進度
    completion_signal = pyqtSignal(bool, str, list) # 成功狀態, 訊息, FFmpeg 日誌列表
    info_signal = pyqtSignal(dict) # (可選: 用於將額外資訊傳回 GUI)

    # 確保 __init__ 接收 original_gif_info 參數
    def __init__(self, ffmpeg_path, ffprobe_path, input_gif_path, output_gif_path, target_frame_count, original_gif_info, show_ffmpeg_output, parent=None):
        super().__init__(parent)
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.input_gif_path = input_gif_path
        self.output_gif_path = output_gif_path
        self.target_frame_count = target_frame_count
        self.original_gif_info = original_gif_info # 儲存從主執行緒傳入的原始 GIF 資訊
        self.show_ffmpeg_output = show_ffmpeg_output # 新增這行：儲存是否顯示 FFmpeg 輸出的狀態
        self.ffmpeg_log = [] # 存放 FFmpeg 輸出訊息

    def run(self):
        try:
            success, message = self.process_gif_internal(
                self.ffmpeg_path,
                self.input_gif_path,
                self.output_gif_path,
                self.target_frame_count
            )
            self.completion_signal.emit(success, message, self.ffmpeg_log)
        except Exception as e:
            self.ffmpeg_log.append(f"線程內部錯誤: {str(e)}")
            self.completion_signal.emit(False, f"處理過程中發生意外錯誤: {str(e)}", self.ffmpeg_log)

    def process_gif_internal(self, ffmpeg_path, input_gif_path, output_gif_path, target_frame_count):
        self.ffmpeg_log = []
        
        # 從儲存的 original_gif_info 中獲取資訊
        avg_fps = self.original_gif_info.get("avg_fps")
        original_total_frames = self.original_gif_info.get("total_frames")

        # 新增檢查，以防資訊獲取失敗
        if avg_fps is None or original_total_frames is None or original_total_frames == 0:
            self.completion_signal.emit(False, "無法獲取原始 GIF 資訊，處理失敗。", self.ffmpeg_log)
            return False, "無法獲取原始 GIF 資訊，處理失敗。"

        # 計算新的 FPS
        if original_total_frames > 0:
            target_fps = (target_frame_count / original_total_frames) * avg_fps
        else:
            target_fps = avg_fps # 如果原始幀數為0，則使用原始FPS (這情況應該很罕見)
        
        # 進行 FFmpeg 處理
        success, message, ffmpeg_log_output = process_gif_backend(
            ffmpeg_path,
            input_gif_path,
            output_gif_path,
            target_fps=target_fps,
            progress_callback=lambda msg, pct: self.progress_signal.emit(msg, pct),
            show_progress_messages=self.show_ffmpeg_output # 傳遞是否顯示 FFmpeg 輸出的狀態
        )
        self.ffmpeg_log.extend(ffmpeg_log_output)
        return success, message


# --- GUI 主應用程式 ---

class ClickableFrame(QFrame):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class GIFConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.ffmpeg_path = None
        self.ffprobe_path = None
        self.current_gif_path = None
        self.current_gif_info = {} # 新增這行：用於儲存原始 GIF 資訊
        
        self.setAcceptDrops(True)
        
        self.init_ui()
        self.load_nord_theme()
        self.start_installer_thread()

        # 設定視窗圖示
        # 從 Base64 字串載入圖示
        if LOGO_ICON_BASE64.strip(): # 檢查 Base64 字串是否為空
            try:
                icon_data = base64.b64decode(LOGO_ICON_BASE64.strip())
                pixmap = QPixmap()
                pixmap.loadFromData(icon_data)
                icon = QIcon(pixmap)
                self.setWindowIcon(icon)
            except Exception as e:
                print(f"無法從 Base64 資料載入圖示: {e}")
        else:
            print("警告：LOGO_ICON_BASE64 為空，將不顯示應用程式圖示。")

    def init_ui(self):
        self.setWindowTitle("GIF 幀數調整工具")
        # self.setGeometry(100, 100, 600, 700)
        self.setFixedSize(500, 700) # 固定視窗大小

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.status_label = QLabel("正在檢查並安裝 FFmpeg/7-Zip...")
        self.status_label.setObjectName("statusLabel")
        main_layout.addWidget(self.status_label)
        main_layout.addSpacing(10)

        self.drag_drop_frame = ClickableFrame()
        self.drag_drop_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.drag_drop_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.drag_drop_frame.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.drag_drop_frame.setLineWidth(2)
        self.drag_drop_frame.setMidLineWidth(1)
        self.drag_drop_frame.setAcceptDrops(True)
        self.drag_drop_frame.setObjectName("dragDropFrame")
        self.drag_drop_frame.setLayout(QVBoxLayout())
        
        self.drag_drop_frame.clicked.connect(self.open_file_dialog)

        self.drag_drop_label = QLabel("將 GIF 檔案拖曳到此處，或點擊選擇檔案")
        self.drag_drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drag_drop_label.setWordWrap(True)
        self.drag_drop_label.setObjectName("dragDropLabel")
        self.drag_drop_frame.layout().addWidget(self.drag_drop_label)
        
        main_layout.addWidget(self.drag_drop_frame)
        main_layout.addSpacing(10)

        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.Shape.StyledPanel)
        info_frame.setObjectName("infoFrame")
        info_layout = QVBoxLayout()
        info_frame.setLayout(info_layout)

        self.input_path_label = QLabel("原始檔案路徑: 無")
        self.input_path_label.setObjectName("infoLabel")
        info_layout.addWidget(self.input_path_label)

        self.original_info_label = QLabel("原始 GIF 資訊:\n")
        self.original_info_label.setObjectName("infoLabel")
        info_layout.addWidget(self.original_info_label)

        main_layout.addWidget(info_frame)
        main_layout.addSpacing(10)

        target_layout = QHBoxLayout()
        self.target_frames_label = QLabel("目標總幀數:")
        self.target_frames_label.setObjectName("label")
        self.target_frames_input = QLineEdit("250")
        self.target_frames_input.setPlaceholderText("輸入目標幀數")
        self.target_frames_input.setValidator(QIntValidator(1, 99999))
        target_layout.addWidget(self.target_frames_label)
        target_layout.addWidget(self.target_frames_input)
        main_layout.addLayout(target_layout)
        main_layout.addSpacing(10)

        output_name_layout = QHBoxLayout()
        self.output_name_label = QLabel("輸出檔案名稱:")
        self.output_name_label.setObjectName("label")
        self.output_name_input = QLineEdit("output_250.gif")
        self.output_name_input.setPlaceholderText("例如: output.gif")
        output_name_layout.addWidget(self.output_name_label)
        output_name_layout.addWidget(self.output_name_input)
        main_layout.addLayout(output_name_layout)
        main_layout.addSpacing(10)

        button_layout = QHBoxLayout()
        self.process_button = QPushButton("開始處理 GIF")
        self.process_button.clicked.connect(self.start_gif_processing)
        self.process_button.setEnabled(False)
        self.process_button.setObjectName("primaryButton")

        self.open_output_folder_button = QPushButton("開啟輸出資料夾")
        self.open_output_folder_button.clicked.connect(self.open_output_folder)
        self.open_output_folder_button.setEnabled(False)
        self.open_output_folder_button.setObjectName("secondaryButton")

        button_layout.addWidget(self.process_button)
        button_layout.addWidget(self.open_output_folder_button)
        main_layout.addLayout(button_layout)
        main_layout.addSpacing(10)

        # 新增勾選框
        self.show_ffmpeg_output_checkbox = QCheckBox("顯示詳細輸出日誌")
        self.show_ffmpeg_output_checkbox.setChecked(True) # 預設為勾選
        self.show_ffmpeg_output_checkbox.setObjectName("label")
        main_layout.addWidget(self.show_ffmpeg_output_checkbox)
        main_layout.addSpacing(5)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("logOutput")
        main_layout.addWidget(self.log_output)

        self.setLayout(main_layout)

    def load_nord_theme(self):
        nord0 = "#2E3440"
        nord1 = "#3B4252"
        nord2 = "#434C5E"
        nord3 = "#4C566A"

        nord4 = "#D8DEE9"
        nord5 = "#E5E9F0"
        nord6 = "#ECEFF4"

        nord7 = "#8FBCBB"
        nord8 = "#88C0D0"
        nord9 = "#81A1C1"
        nord10 = "#5E81AC"

        nord11 = "#BF616A"
        nord12 = "#D08770"
        nord13 = "#EBCB8B"
        nord14 = "#A3BE8C"
        nord15 = "#B48EAD"

        qss = f"""
        QWidget {{
            background-color: {nord0};
            color: {nord4};
            font-family: Arial, sans-serif;
            font-size: 14px;
        }}
        QLabel {{
            color: {nord4};
            padding: 2px;
        }}
        QLabel#statusLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {nord8};
            padding: 5px;
            border-bottom: 1px solid {nord1};
        }}
        QLabel#dragDropLabel {{
            background-color: {nord1};
            border: 2px dashed {nord3};
            border-radius: 8px;
            min-height: 100px;
            color: {nord5};
            font-size: 16px;
            font-weight: bold;
            qproperty-alignment: 'AlignCenter';
        }}
        QLineEdit {{
            background-color: {nord1};
            border: 1px solid {nord3};
            border-radius: 5px;
            padding: 5px;
            color: {nord6};
            selection-background-color: {nord10};
        }}
        QPushButton {{
            background-color: {nord9};
            color: {nord6};
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {nord10};
        }}
        QPushButton:pressed {{
            background-color: {nord5};
            color: {nord0};
        }}
        QPushButton:disabled {{
            background-color: {nord2};
            color: {nord3};
        }}
        QPushButton#primaryButton {{
            background-color: {nord10};
            color: {nord6};
        }}
        QPushButton#primaryButton:hover {{
            background-color: {nord9};
        }}
        QPushButton#secondaryButton {{
            background-color: {nord3};
            color: {nord6};
        }}
        QPushButton#secondaryButton:hover {{
            background-color: {nord2};
        }}
        QFrame#dragDropFrame {{
            background-color: {nord1};
            border: 2px dashed {nord3};
            border-radius: 8px;
        }}
        QFrame#infoFrame {{
            background-color: {nord2};
            border: 1px solid {nord3};
            border-radius: 5px;
            padding: 5px;
        }}
        QLabel#infoLabel {{
            color: {nord5};
            font-size: 13px;
        }}
        QTextEdit#logOutput {{
            background-color: {nord1};
            border: 1px solid {nord3};
            border-radius: 5px;
            padding: 5px;
            color: {nord6};
        }}
        QCheckBox {{
            color: {nord4};
            spacing: 5px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {nord3};
            border-radius: 3px;
            background-color: {nord1};
        }}
        QCheckBox::indicator:checked {{
            background-color: {nord9};
            border: 1px solid {nord10};
            /* 內嵌 SVG 勾選圖標，顏色為 nord6 */
            image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgdmlld0JveD0iMCAwIDI0IDI0Ij48cGF0aCBmaWxsPSJub25lIiBzdHJva2U9IiNFQ0VGRjQiIHN0cm9rZS13aWR0aD0iMiIgZD0iTTIgMTJWMTJDMy44MiAxMiAxMiAyMiAxMiAyMkMxMiAyMiAxNy40NiAxNi4zMiAyMiAxMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZxq=);
        }}
        """
        self.setStyleSheet(qss)

    def start_installer_thread(self):
        self.installer_thread = InstallerThread()
        self.installer_thread.progress_signal.connect(self.update_status_label)
        self.installer_thread.completion_signal.connect(self.on_installer_complete)
        self.installer_thread.start()
        self.process_button.setEnabled(False)
        self.drag_drop_frame_enabled(False)

    def on_installer_complete(self, success, message, ffmpeg_path, ffprobe_path):
        self.status_label.setText(message)
        if success:
            self.ffmpeg_path = ffmpeg_path
            self.ffprobe_path = ffprobe_path
            self.process_button.setEnabled(True)
            self.drag_drop_frame_enabled(True)
            self.drag_drop_label.setText("將 GIF 檔案拖曳到此處，或點擊選擇檔案")
            self.log_output.append("FFmpeg 及 7-Zip 已準備就緒。請拖曳 GIF 檔案。")
        else:
            QMessageBox.critical(self, "安裝失敗", message)
            self.log_output.append(f"安裝失敗：{message}")
            self.status_label.setText("FFmpeg/7-Zip 安裝失敗。請檢查日誌。")
            self.process_button.setEnabled(False)
            self.drag_drop_frame_enabled(False)

    def drag_drop_frame_enabled(self, enabled):
        if self.drag_drop_frame:
            self.drag_drop_frame.setAcceptDrops(enabled)
            if enabled:
                self.drag_drop_frame.setStyleSheet("QFrame#dragDropFrame { border: 2px dashed #4C566A; }")
                self.drag_drop_frame.setEnabled(True)
            else:
                self.drag_drop_frame.setStyleSheet("QFrame#dragDropFrame { border: 2px dashed #2E3440; background-color: #3B4252; }")
                self.drag_drop_frame.setEnabled(False)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if self.ffmpeg_path is None or self.ffprobe_path is None:
            event.ignore()
            return

        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith('.gif'):
                    event.acceptProposedAction()
                    self.drag_drop_label.setText("將 GIF 檔案拖曳到此處，或點擊選擇檔案")
                    return
        self.drag_drop_label.setText("僅支援 GIF 檔案")
        event.ignore()

    def dragLeaveEvent(self, event):
        if self.ffmpeg_path is not None and self.ffprobe_path is not None:
            self.drag_drop_label.setText("將 GIF 檔案拖曳到此處，或點擊選擇檔案")
        else:
            self.drag_drop_label.setText("FFmpeg/7-Zip 安裝中...")
        event.accept()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith('.gif'):
                    self.current_gif_path = url.toLocalFile()
                    self.input_path_label.setText(f"原始檔案路徑: {os.path.basename(self.current_gif_path)}")
                    self.log_output.clear()
                    self.log_output.append(f"已載入檔案：{self.current_gif_path}")
                    self.get_and_display_gif_info()
                    event.acceptProposedAction()
                    return
        self.drag_drop_label.setText("僅支援 GIF 檔案")
        event.ignore()

    def get_and_display_gif_info(self):
        if not self.current_gif_path or not os.path.exists(self.current_gif_path):
            self.original_info_label.setText("原始 GIF 資訊:\n檔案無效。")
            self.current_gif_info = {} # 清空資訊
            return

        self.log_output.append("\n正在獲取 GIF 資訊...")
        info = get_gif_info_backend(self.ffprobe_path, self.current_gif_path)
        self.current_gif_info = info # 將獲取的資訊儲存到實例變數中
        
        if info["error"]:
            self.original_info_label.setText(f"原始 GIF 資訊:\n錯誤: {info['error']}")
            self.log_output.append(f"錯誤: {info['error']}")
        else:
            self.original_info_label.setText(
                f"原始 GIF 資訊:\n"
                f"  檔案大小: {info['file_size_mib']:.2f} MiB\n"
                f"  平均幀率 (FPS): {info['avg_fps']:.2f}\n"
                f"  總時長 (秒): {info['duration']:.2f}\n"
                f"  推算原始總幀數: {info['total_frames']} 幀"
            )
            self.log_output.append("GIF 資訊載入成功。")
            
            if info['total_frames'] is not None and info['total_frames'] > 0:
                if info['total_frames'] < 250 and info['total_frames'] > 0:
                     self.target_frames_input.setText(str(info['total_frames']))
                else:
                    self.target_frames_input.setText("250")
                
                base_name = os.path.splitext(os.path.basename(self.current_gif_path))[0]
                # 帶入檔案的預設名稱規則
                self.output_name_input.setText(f"{base_name}_{self.target_frames_input.text()}.gif") # 新檔案名稱

    def open_file_dialog(self):
        if self.ffmpeg_path is None or self.ffprobe_path is None:
            QMessageBox.warning(self, "未準備好", "FFmpeg/7-Zip 正在安裝中，請稍候。")
            return

        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("選擇 GIF 檔案")
        file_dialog.setNameFilter("GIF 檔案 (*.gif)")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.current_gif_path = selected_files[0]
                self.input_path_label.setText(f"原始檔案路徑: {os.path.basename(self.current_gif_path)}")
                self.log_output.clear()
                self.log_output.append(f"已載入檔案：{self.current_gif_path}")
                self.get_and_display_gif_info()
                self.drag_drop_label.setText("將 GIF 檔案拖曳到此處，或點擊選擇檔案")

    def start_gif_processing(self):
        if not self.ffmpeg_path or not self.ffprobe_path:
            QMessageBox.warning(self, "錯誤", "FFmpeg/FFprobe 尚未準備好，請等待安裝完成。")
            return
        if not self.current_gif_path:
            QMessageBox.warning(self, "錯誤", "請先拖曳或選擇一個 GIF 檔案。")
            return
        # 確保在啟動處理前已經有原始 GIF 資訊
        if not self.current_gif_info or self.current_gif_info.get("error"):
            QMessageBox.warning(self, "錯誤", "無法獲取原始 GIF 資訊，請重新載入檔案。")
            return

        try:
            target_frames = int(self.target_frames_input.text())
            if target_frames <= 0:
                raise ValueError("目標幀數必須是正整數。")
        except ValueError:
            QMessageBox.warning(self, "輸入錯誤", "請輸入有效的目標幀數 (正整數)。")
            return
        
        output_file_name = self.output_name_input.text().strip()
        if not output_file_name:
            QMessageBox.warning(self, "輸入錯誤", "請輸入有效的輸出檔案名稱。")
            return
        if not output_file_name.lower().endswith('.gif'):
            output_file_name += '.gif'

        output_gif_path = os.path.join(os.path.dirname(self.current_gif_path), output_file_name)

        self.log_output.clear()
        self.log_output.append("開始處理 GIF...")
        self.process_button.setEnabled(False)

        show_ffmpeg_output = self.show_ffmpeg_output_checkbox.isChecked() # 獲取勾選框狀態

        # 建立 GIFProcessorThread 時傳遞原始 GIF 資訊
        self.processor_thread = GIFProcessorThread(
            self.ffmpeg_path,
            self.ffprobe_path,
            self.current_gif_path,
            output_gif_path,
            target_frames,
            self.current_gif_info, # 傳遞儲存的原始 GIF 資訊
            show_ffmpeg_output # 傳遞勾選框狀態
        )
        self.processor_thread.info_signal.connect(self.update_original_info_from_thread)
        self.processor_thread.progress_signal.connect(self.update_processing_progress)
        self.processor_thread.completion_signal.connect(self.on_gif_processing_complete)
        self.processor_thread.start()

    def update_original_info_from_thread(self, info):
        # 此處可以選擇性地移除或修改其功能，它主要是在 info_signal 發出時被觸發
        # 目前保持，但不做任何處理，或僅用於進一步的日誌記錄
        pass

    def update_status_label(self, message, is_verbose_update):
        # 總是更新狀態標籤 (上方進度)
        self.status_label.setText(message)
        
        # 只有當 is_verbose_update 為 False (即非實時、簡潔的訊息) 時才追加到日誌 (下方詳細)
        if not is_verbose_update:
            self.log_output.append(message)

    def update_processing_progress(self, log_message, percentage):
        # 這裡的 log_message 只有在 "顯示 FFmpeg 詳細輸出日誌" 勾選時才會有內容
        self.log_output.append(log_message)
        # 如果需要進度條，可以在這裡更新 QProgressBar

    def on_gif_processing_complete(self, success, message, ffmpeg_log):
        self.process_button.setEnabled(True)
        self.open_output_folder_button.setEnabled(True)
        # --- 處理結果 (始終顯示) ---
        self.log_output.append("\n--- 處理結果 ---")
        if success:
            self.log_output.append(f"✅ {message}")
            # QMessageBox.information(self, "處理完成", message) # 處理完成的彈出訊息
        else:
            self.log_output.append(f"❌ 處理失敗：{message}")
            QMessageBox.critical(self, "處理失敗", message) # 處理失敗的彈出訊息
        # --- 檢驗輸出 GIF (始終顯示) ---
        self.log_output.append("\n--- 檢驗輸出 GIF ---")
        output_gif_path = os.path.join(os.path.dirname(self.current_gif_path), self.output_name_input.text())
        info = get_gif_info_backend(self.ffprobe_path, output_gif_path)
        
        if info["error"]:
            self.log_output.append(f"錯誤: 無法檢驗輸出 GIF 資訊: {info['error']}")
        else:
            self.log_output.append(
                f"  檔案名稱: {os.path.basename(output_gif_path)}\n"
                f"  檔案大小: {info['file_size_mib']:.2f} MiB\n"
                f"  實際幀率 (FPS): {info['avg_fps']:.2f}\n"
                f"  實際總時長 (秒): {info['duration']:.2f}\n"
                f"  實際總幀數: {info['total_frames']} 幀\n"
                f"  目標總幀數: {self.target_frames_input.text()} 幀"
            )
            target_frames = int(self.target_frames_input.text())
            if info['total_frames'] == target_frames:
                self.log_output.append("👍 成功達到目標幀數！")
            elif abs(info['total_frames'] - target_frames) <= 1:
                    self.log_output.append("👍 實際幀數非常接近目標幀數 (僅有微小誤差)。")
            else:
                self.log_output.append("⚠️ 實際幀數與目標幀數存在較大差異。FFmpeg 可能已將 FPS 四捨五入。")

        # 僅當勾選框被選中時，才顯示 FFmpeg 完整日誌
        if self.show_ffmpeg_output_checkbox.isChecked():
            self.log_output.append("\n--- FFmpeg 完整日誌 ---\n")
            self.log_output.append("\n".join(ffmpeg_log))

    def open_output_folder(self):
        if self.current_gif_path:
            output_dir = os.path.dirname(self.current_gif_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir))
        else:
            QMessageBox.warning(self, "警告", "請先處理一個 GIF 檔案以生成輸出資料夾。")

    def closeEvent(self, event):
        # 終止並等待 InstallerThread
        if hasattr(self, 'installer_thread') and self.installer_thread.isRunning():
            self.log_output.append("正在等待安裝執行緒終止...")
            self.installer_thread.quit()
            self.installer_thread.wait()
            self.log_output.append("安裝執行緒已終止。")

        # 終止並等待 GIFProcessorThread
        if hasattr(self, 'processor_thread') and self.processor_thread.isRunning():
            self.log_output.append("正在等待 GIF 處理執行緒終止...")
            self.processor_thread.quit()
            self.processor_thread.wait()
            self.log_output.append("GIF 處理執行緒已終止。")
            
        event.accept() # 允許視窗關閉

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GIFConverterApp()
    window.show()
    sys.exit(app.exec())