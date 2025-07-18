import subprocess
import re
import os

def get_gif_info(input_gif_path):
    """
    使用 ffprobe 獲取 GIF 的平均幀率、總時長和計算總幀數。
    同時獲取檔案大小。
    """
    avg_frame_rate, duration = None, None
    file_size_mib = None

    # 1. 獲取幀率和時長
    command_info = [
        'ffprobe',
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

    except FileNotFoundError:
        print(f"錯誤：找不到 'ffprobe' 命令。請確認 FFmpeg/FFprobe 已安裝並在 PATH 中。")
        return None, None, None, None
    except subprocess.CalledProcessError as e:
        print(f"執行 ffprobe 獲取基本資訊時發生錯誤：{e.stderr}")
        return None, None, None, None
    except ValueError as e:
        print(f"解析 ffprobe 輸出時發生錯誤：{e}")
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
        file_size_mib = None # 如果無法獲取，則設為 None

    total_frames = None
    if avg_frame_rate is not None and duration is not None:
        total_frames = round(avg_frame_rate * duration)

    return avg_frame_rate, duration, total_frames, file_size_mib

def process_gif(input_gif_path, output_gif_path, target_frame_count):
    """
    根據目標幀數計算 FPS，並執行 FFmpeg 命令。
    """
    print("\n--- 步驟 2: 取得 GIF 資訊 ---")
    avg_fps, duration, original_frame_count, file_size_mib = get_gif_info(input_gif_path)

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

    print("\n--- 步驟 3: 輸入目標總幀數 ---")
    # 這裡直接使用傳入的 target_frame_count，符合流程圖的步驟3。
    print(f"您設定的目標總幀數為: {target_frame_count} 幀")
    
    if target_frame_count > original_frame_count:
        print(f"警告：目標幀數 ({target_frame_count}) 大於原始幀數 ({original_frame_count})。這會增加幀數，可能不會讓檔案變小。")
    elif target_frame_count == original_frame_count:
        print(f"提示：目標幀數與原始幀數相同。將進行調色盤優化但不改變幀數。")

    # 計算新的 FPS
    new_fps = target_frame_count / duration

    print("\n--- 步驟 4: 計算並輸出 (執行 FFmpeg) ---")
    print(f"  計算後的新 FPS 參數: {new_fps:.15f}") # 顯示足夠的小數位確保精確度

    ffmpeg_command = [
        'ffmpeg',
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
            
            # 再次檢驗輸出 GIF 的資訊
            print(f"\n--- 檢驗輸出 GIF 檔案資訊 ---")
            out_avg_fps, out_duration, final_frame_count, out_file_size_mib = get_gif_info(output_gif_path)
            
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
    print("--- GIF 幀數調整與檔案優化工具 ---")
    
    # 步驟 1: 讓使用者先帶入來源的 GIF
    input_file = input("請輸入原始 GIF 檔案名稱 (例如: input.gif): ").strip()
    
    if not os.path.exists(input_file):
        print(f"錯誤：檔案 '{input_file}' 不存在。請檢查路徑和檔名。")
    else:
        try:
            # 讓使用者輸入希望修改的總幀數
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
                process_gif(input_file, output_file, target_frames)

    print("\n--- 程式結束 ---")