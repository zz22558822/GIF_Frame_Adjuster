import subprocess
import re
import os
import shutil
import requests
from alive_progress import alive_bar # 確保已安裝: pip install alive-progress requests

# --- FFmpeg 和 7-Zip 自動安裝相關函式 ---

# 下載檔案 (包含進度條)
def download_file_with_progress(url, local_filename):
    print(f"開始下載 {os.path.basename(local_filename)}...")
    os.makedirs(os.path.dirname(local_filename), exist_ok=True) # 確保目錄存在
    try:
        with requests.get(url, stream=True) as r, open(local_filename, 'wb') as f:
            r.raise_for_status() # 檢查 HTTP 請求是否成功
            file_size = int(r.headers.get('content-length', 0))
            chunk_size = 8192
            
            bar_length = file_size // chunk_size if file_size > chunk_size else 1 # 避免為0
            if file_size == 0:
                print("警告: 檔案大小未知，可能無法顯示精確進度條。")
                bar_length = 100 # 提供一個預設值，讓進度條仍能動

            with alive_bar(bar_length, bar='smooth', spinner='dots_waves', length=40, enrich_print=False) as bar:
                bar.text(f'下載 {os.path.basename(local_filename)} 進度')
                for chunk in r.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
                    bar() # 更新進度條
                bar(bar_length) # 手動設置進度條到 100%

        print(f"成功下載 {os.path.basename(local_filename)} 到 {local_filename}")
        return local_filename
    except requests.exceptions.RequestException as e:
        print(f"下載失敗：{e}")
        return None
    except Exception as e:
        print(f"下載時發生未知錯誤：{e}")
        return None

# 解壓縮並重新命名 (使用指定的 7za.exe 路徑)
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
        # 資料夾通常以壓縮檔名或 'ffmpeg-' 開頭
        if 'ffmpeg.7z' in archive_path: # 處理 ffmpeg 的特殊命名
            for folder_name in extracted_dirs:
                if folder_name.startswith('ffmpeg-'):
                    old_folder_path = os.path.join(target_directory, folder_name)
                    break
        elif '7z2301-src.7z' in archive_path: # 處理 7-Zip 源碼壓縮包的解壓結果
            for folder_name in extracted_dirs:
                if folder_name.startswith('7z'): # 通常解壓後會有 '7z2301' 這樣的資料夾
                    old_folder_path = os.path.join(target_directory, folder_name)
                    break
        else: # 默認情況，假設解壓後只有一個資料夾或者與壓縮檔同名
             # 如果解壓縮的檔案名就是資料夾名，就用這個邏輯
            if len(extracted_dirs) == 1:
                old_folder_path = os.path.join(target_directory, extracted_dirs[0])
            else: # 如果有多個，或者沒有符合預期的，可能需要手動指定
                print("警告：解壓縮後找到多個資料夾，或未能識別主資料夾。")
                # 這裡可以根據實際情況調整選擇邏輯，例如選擇最新的資料夾
                # 為了避免複雜，我們假設只有一個主資料夾
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

def check_and_install_7z():
    """
    檢查 7z 解壓縮工具是否存在，如果不存在則自動下載並配置。
    返回 7za.exe 的執行檔路徑。
    """
    seven_zip_dir = os.path.join('.', 'driver', '7z')
    seven_zip_exec_path = os.path.join(seven_zip_dir, '7za.exe')

    if os.path.exists(seven_zip_exec_path):
        print("7-Zip (7za.exe) 已存在。")
        return seven_zip_exec_path

    print("\n偵測到 7-Zip (7za.exe) 不存在，將嘗試自動安裝...")
    
    # 7-Zip Command Line Version 下載 URL (Windows 64-bit)
    # 請定期檢查這個 URL 是否仍然有效
    # 我們下載一個較小的 standalone 版本，只包含 7za.exe
    seven_zip_download_url = 'https://www.7-zip.org/a/7za920.zip' # 這是 7za.exe 的直接壓縮檔
    seven_zip_archive_path = os.path.join(seven_zip_dir, '7za920.zip')

    # 確保 7z 目錄存在
    os.makedirs(seven_zip_dir, exist_ok=True)

    # 下載 7z 壓縮檔
    if not download_file_with_progress(seven_zip_download_url, seven_zip_archive_path):
        print("7-Zip 壓縮檔下載失敗，無法繼續安裝。")
        return None
    
    # Python 的 zipfile 模組可以處理 .zip 檔案，無需 7za.exe 自身解壓縮
    try:
        import zipfile
        with zipfile.ZipFile(seven_zip_archive_path, 'r') as zf:
            zf.extractall(seven_zip_dir)
        print(f"成功解壓縮 {os.path.basename(seven_zip_archive_path)}")
        
        # 7za920.zip 通常只包含 7za.exe 和 7z.dll 等，直接提取到指定目錄即可
        # 確保 7za.exe 就在 seven_zip_dir 下
        if os.path.exists(seven_zip_exec_path):
            print("7-Zip (7za.exe) 安裝完成。")
            return seven_zip_exec_path
        else:
            # 如果解壓出來的檔案不在根目錄，可能需要找一下
            # 遍歷 seven_zip_dir 尋找 7za.exe
            for root, _, files in os.walk(seven_zip_dir):
                if '7za.exe' in files:
                    found_7za_path = os.path.join(root, '7za.exe')
                    if found_7za_path != seven_zip_exec_path:
                        shutil.move(found_7za_path, seven_zip_exec_path)
                        print(f"已將 7za.exe 移動到正確位置：{seven_zip_exec_path}")
                    return seven_zip_exec_path
            print("錯誤：解壓縮後未能找到 7za.exe。")
            return None

    except zipfile.BadZipFile:
        print(f"錯誤：下載的 7-Zip 檔案 '{seven_zip_archive_path}' 不是有效的 ZIP 檔案。")
        return None
    except Exception as e:
        print(f"7-Zip 解壓縮時發生錯誤：{e}")
        return None
    finally:
        # 清理：刪除 7z 壓縮檔
        if os.path.exists(seven_zip_archive_path):
            try:
                os.remove(seven_zip_archive_path)
                print(f"已刪除下載的 7-Zip 壓縮檔：{seven_zip_archive_path}")
            except Exception as e:
                print(f"刪除 7-Zip 壓縮檔失敗：{e}")


def check_and_install_ffmpeg(seven_zip_exec_path):
    """
    檢查 FFmpeg 是否存在，如果不存在則自動下載並配置。
    返回 FFmpeg 和 FFprobe 的執行檔路徑。
    """
    ffmpeg_exec_path = os.path.join('.', 'driver', 'ffmpeg', 'bin', 'ffmpeg.exe')
    ffprobe_exec_path = os.path.join('.', 'driver', 'ffmpeg', 'bin', 'ffprobe.exe')

    if os.path.exists(ffmpeg_exec_path) and os.path.exists(ffprobe_exec_path):
        print("FFmpeg 和 FFprobe 已存在。")
        return ffmpeg_exec_path, ffprobe_exec_path

    print("\n偵測到 FFmpeg 或 FFprobe 不存在，將嘗試自動安裝...")
    
    driver_dir = './driver/'
    ffmpeg_archive_path = os.path.join(driver_dir, 'ffmpeg.7z')
    
    # FFmpeg 下載 URL (Windows 64-bit full build)
    ffmpeg_download_url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z'

    if not download_file_with_progress(ffmpeg_download_url, ffmpeg_archive_path):
        print("FFmpeg 壓縮檔下載失敗，無法繼續安裝。")
        return None, None
    
    # 使用傳入的 7za.exe 路徑來解壓縮 FFmpeg
    if not extract_and_rename_archive(ffmpeg_archive_path, driver_dir, 'ffmpeg', seven_zip_exec_path):
        print("FFmpeg 解壓縮或重命名失敗，無法繼續安裝。")
        return None, None

    if os.path.exists(ffmpeg_archive_path):
        try:
            os.remove(ffmpeg_archive_path)
            print(f"已刪除下載的壓縮檔：{ffmpeg_archive_path}")
        except Exception as e:
            print(f"刪除壓縮檔失敗：{e}")

    if os.path.exists(ffmpeg_exec_path) and os.path.exists(ffprobe_exec_path):
        print("FFmpeg 和 FFprobe 安裝完成。")
        return ffmpeg_exec_path, ffprobe_exec_path
    else:
        print("FFmpeg 和 FFprobe 安裝失敗，執行檔未找到。")
        return None, None

# --- 原始 GIF 處理應用程式邏輯 (無變動，除了函式調用傳參) ---

def get_gif_info(ffmpeg_path, ffprobe_path, input_gif_path):
    """
    使用指定的 ffprobe 路徑獲取 GIF 的平均幀率、總時長和計算總幀數。
    同時獲取檔案大小。
    """
    avg_frame_rate, duration = None, None
    file_size_mib = None

    # 1. 獲取幀率和時長
    command_info = [
        ffprobe_path, # 使用傳入的 ffprobe 路徑
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=avg_frame_rate,duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        input_gif_path
    ]

    try:
        result_info = subprocess.run(command_info, capture_output=True, text=True, check=True)
        output_lines = result_info.stdout.strip().split('\n')

        if len(output_lines) >= 2: # 有時 duration 可能有多餘的換行
            avg_frame_rate_str = output_lines[0]
            duration_str = output_lines[1]

            match = re.match(r'(\d+)/(\d+)', avg_frame_rate_str)
            if match:
                numerator = int(match.group(1))
                denominator = int(match.group(2))
                avg_frame_rate = numerator / denominator if denominator != 0 else 0
            
            duration = float(duration_str)
        else:
            print(f"警告: 無法完全解析 ffprobe 基本資訊輸出。\n{result_info.stdout}")

    except subprocess.CalledProcessError as e:
        print(f"執行 {ffprobe_path} 獲取基本資訊時發生錯誤：{e.stderr}")
        return None, None, None, None
    except ValueError as e:
        print(f"解析 {ffprobe_path} 輸出時發生錯誤：{e}")
        return None, None, None, None
    except Exception as e:
        print(f"發生未知錯誤：{e}")
        return None, None, None, None

    # 2. 獲取檔案大小
    try:
        file_size_bytes = os.path.getsize(input_gif_path)
        file_size_mib = file_size_bytes / (1024 * 1024) # 轉換為 MiB
    except Exception as e:
        print(f"警告: 無法獲取檔案大小: {e}")
        file_size_mib = None

    total_frames = None
    if avg_frame_rate is not None and duration is not None:
        total_frames = round(avg_frame_rate * duration)

    return avg_frame_rate, duration, total_frames, file_size_mib

def process_gif(ffmpeg_path, ffprobe_path, input_gif_path, output_gif_path, target_frame_count):
    """
    根據目標幀數計算 FPS，並執行 FFmpeg 命令。
    """
    print("\n--- 步驟 2: 取得 GIF 資訊並顯示 ---")
    avg_fps, duration, original_frame_count, file_size_mib = get_gif_info(ffmpeg_path, ffprobe_path, input_gif_path)

    if avg_fps is None or duration is None or original_frame_count is None:
        print("無法獲取原始 GIF 資訊，請檢查檔案路徑或 FFmpeg/FFprobe 安裝。")
        return False

    print(f"原始 GIF 資訊：")
    print(f"  檔案名稱: {os.path.basename(input_gif_path)}")
    print(f"  檔案大小: {file_size_mib:.2f} MiB" if file_size_mib is not None else "  檔案大小: 未知")
    print(f"  平均幀率 (FPS): {avg_fps:.2f}")
    print(f"  總時長 (秒): {duration:.2f}")
    print(f"  推算原始總幀數: {original_frame_count} 幀")

    if original_frame_count == 0 or duration == 0:
        print("錯誤：原始 GIF 似乎沒有有效的幀數或時長，無法處理。")
        return False

    print("\n--- 步驟 3: 輸入希望修改的總幀數 ---")
    print(f"您設定的目標總幀數為: {target_frame_count} 幀")
    
    if target_frame_count > original_frame_count:
        print(f"警告：目標幀數 ({target_frame_count}) 大於原始幀數 ({original_frame_count})。這會增加幀數，可能不會讓檔案變小。")
    elif target_frame_count == original_frame_count:
        print(f"提示：目標幀數與原始幀數相同。將進行調色盤優化但不改變幀數。")

    new_fps = target_frame_count / duration

    print("\n--- 步驟 4: 計算並輸出 (執行 FFmpeg) ---")
    print(f"  計算後的新 FPS 參數: {new_fps:.15f}")

    ffmpeg_command = [
        ffmpeg_path,
        '-i', input_gif_path,
        '-vf', f"fps={new_fps:.15f},split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
        output_gif_path
    ]

    print(f"\n正在執行 FFmpeg 命令...")
    print(f"命令: {' '.join(ffmpeg_command)}")

    try:
        process = subprocess.run(ffmpeg_command, capture_output=True, text=True, check=False)

        print("\n--- FFmpeg 輸出 ---")
        if process.stdout:
            print(process.stdout)
        if process.stderr:
            print(process.stderr)
        print("-------------------\n")

        if process.returncode == 0:
            print(f"✅ FFmpeg 處理完成！新的 GIF 已儲存至：{output_gif_path}")
            
            print(f"\n--- 檢驗輸出 GIF 檔案資訊 ---")
            out_avg_fps, out_duration, final_frame_count, out_file_size_mib = get_gif_info(ffmpeg_path, ffprobe_path, output_gif_path)
            
            if out_avg_fps is not None and out_duration is not None and final_frame_count is not None:
                print(f"輸出 GIF 實際資訊：")
                print(f"  檔案名稱: {os.path.basename(output_gif_path)}")
                print(f"  檔案大小: {out_file_size_mib:.2f} MiB" if out_file_size_mib is not None else "  檔案大小: 未知")
                print(f"  實際幀率 (FPS): {out_avg_fps:.2f}")
                print(f"  實際總時長 (秒): {out_duration:.2f}")
                print(f"  實際總幀數: {final_frame_count} 幀")
                print(f"  目標總幀數: {target_frame_count} 幀")
                
                if final_frame_count == target_frame_count:
                    print("👍 成功達到目標幀數！")
                elif abs(final_frame_count - target_frame_count) <= 1:
                     print("👍 實際幀數非常接近目標幀數 (僅有微小誤差)。")
                else:
                    print("⚠️ 實際幀數與目標幀數存在較大差異。FFmpeg 可能已將 FPS 四捨五入。")
                return True
            else:
                print("無法獲取輸出 GIF 資訊進行驗證。")
                return False
        else:
            print(f"❌ FFmpeg 執行失敗，返回碼：{process.returncode}")
            print(f"詳細錯誤訊息請參考上方 '--- FFmpeg 輸出 ---'")
            return False

    except FileNotFoundError:
        print(f"錯誤：找不到 'ffmpeg' 命令。請確認 FFmpeg 已安裝並在 PATH 中。")
        return False
    except Exception as e:
        print(f"執行 FFmpeg 時發生未知錯誤：{e}")
        return False

if __name__ == "__main__":
    print("--- GIF 幀數調整與檔案優化工具 (FFmpeg 及 7-Zip 自動安裝) ---")

    # 首先，檢查並安裝 7-Zip 解壓縮工具
    seven_zip_path = check_and_install_7z()

    if seven_zip_path is None:
        print("\n7-Zip (7za.exe) 未成功配置，程式無法繼續執行。")
    else:
        # 然後，檢查並安裝 FFmpeg，並將 7-Zip 的路徑傳遞給它
        ffmpeg_exec, ffprobe_exec = check_and_install_ffmpeg(seven_zip_path)

        if ffmpeg_exec is None or ffprobe_exec is None:
            print("\nFFmpeg/FFprobe 未成功配置，程式無法繼續執行。")
        else:
            input_file = input("請輸入原始 GIF 檔案名稱 (例如: input.gif): ").strip()
            
            if not os.path.exists(input_file):
                print(f"錯誤：檔案 '{input_file}' 不存在。請檢查路徑和檔名。")
            else:
                try:
                    target_frames_str = input("請輸入您希望修改的總幀數 (例如: 250): ").strip()
                    target_frames = int(target_frames_str)
                    if target_frames <= 0:
                        raise ValueError("目標幀數必須是正整數。")
                except ValueError as e:
                    print(f"輸入錯誤：{e}")
                else:
                    output_file = input("請輸入輸出 GIF 檔案名稱 (例如: output_250_frames.gif): ").strip()
                    if not output_file:
                        print("錯誤：輸出檔案名稱不能為空。")
                    else:
                        process_gif(ffmpeg_exec, ffprobe_exec, input_file, output_file, target_frames)

    print("\n--- 程式結束 ---")