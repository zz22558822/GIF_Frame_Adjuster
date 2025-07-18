import sys
import subprocess
import re
import os
import shutil
import requests
from alive_progress import alive_bar # 確保已安裝: pip install alive-progress requests

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QTextEdit, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDesktopServices, QIntValidator, QCursor

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
            pass # No rename needed if 7za.exe is directly in target_directory
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

def process_gif_backend(ffmpeg_path, input_gif_path, output_gif_path, target_fps, progress_callback=None):
    """
    根據目標幀數計算 FPS，並執行 FFmpeg 命令。
    現在接受進度回調。
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
                if progress_callback:
                    # You might add more sophisticated parsing here for actual percentage
                    progress_callback(output_line.strip(), -1) # -1 indicates unknown percentage

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
    progress_signal = pyqtSignal(str, float) # log message, percentage
    completion_signal = pyqtSignal(bool, str, list) # success, message, ffmpeg_log
    info_signal = pyqtSignal(dict) # (Optional: For sending extra info back to GUI if needed)

    # 確保 __init__ 接收 original_gif_info 參數
    def __init__(self, ffmpeg_path, ffprobe_path, input_gif_path, output_gif_path, target_frame_count, original_gif_info, parent=None):
        super().__init__(parent)
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.input_gif_path = input_gif_path
        self.output_gif_path = output_gif_path
        self.target_frame_count = target_frame_count
        self.original_gif_info = original_gif_info # 儲存從主執行緒傳入的原始 GIF 資訊
        self.ffmpeg_log = [] # Collect FFmpeg output here

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
            progress_callback=lambda msg, pct: self.progress_signal.emit(msg, pct) 
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

        # 建立 GIFProcessorThread 時傳遞原始 GIF 資訊
        self.processor_thread = GIFProcessorThread(
            self.ffmpeg_path,
            self.ffprobe_path,
            self.current_gif_path,
            output_gif_path,
            target_frames,
            self.current_gif_info # 傳遞儲存的原始 GIF 資訊
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
        self.log_output.append(log_message)
        # 如果需要進度條，可以在這裡更新 QProgressBar

    def on_gif_processing_complete(self, success, message, ffmpeg_log):
        self.process_button.setEnabled(True)
        self.open_output_folder_button.setEnabled(True)
        self.log_output.append("\n--- 處理結果 ---")
        if success:
            self.log_output.append(f"✅ {message}")
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
            QMessageBox.information(self, "處理完成", message)
        else:
            self.log_output.append(f"❌ 處理失敗：{message}")
            QMessageBox.critical(self, "處理失敗", message)

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