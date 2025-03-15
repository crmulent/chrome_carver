import json, os, sys, ctypes, subprocess, argparse 
import pandas as pd 
from datetime import datetime, timedelta, timezone 
 
# Function to check if the script is running as administrator 
def is_admin(): 
    try: 
        return ctypes.windll.shell32.IsUserAnAdmin() 
    except: 
        return False 
 
# Function to relaunch the script as administrator 
def run_as_admin(): 
    if not is_admin(): 
        print("Relaunching script with administrator privileges...") 
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1) 
        sys.exit() 
 
# Function to run EVTXECmd.exe for specific log types 
def run_evtxecmd(evtxecmd_path, evtx_files_path, output_json_folder, log_types): 
    # Create the output folder if it doesn't exist 
    if not os.path.exists(output_json_folder): 
        os.makedirs(output_json_folder) 
 
    for log_type in log_types: 
        log_file = os.path.join(evtx_files_path, f"{log_type}.evtx") 
        if not os.path.exists(log_file): 
            print(f"Warning: {log_file} not found. Skipping...") 
            continue 
 
        # Run EVTXECmd for the specific log type 
        command = [ 
            evtxecmd_path, 
            "-f", log_file, 
            "--json", output_json_folder, 
            "--jsonf", (log_type + ".json") 
        ] 
 
        try: 
            print(f"Running EVTXECmd for {log_type} logs...") 
            subprocess.run(command, check=True) 
            print(f"Processed {log_type} logs successfully.") 
        except subprocess.CalledProcessError as e: 
            print(f"Error running EVTXECmd for {log_type}: {e}") 
            continue 
 
# Function to combine JSONL files into a single JSONL file 
def combine_jsonl_files(output_json_folder, output_jsonl_path, log_types): 
    combined_logs = [] 
 
    for log_type in log_types: 
        jsonl_file = os.path.join(output_json_folder, f"{log_type}.json") 
        if not os.path.exists(jsonl_file): 
            print(f"Warning: {jsonl_file} not found. Skipping...") 
            continue 
 
        try: 
            # Read JSONL file line by line 
            with open(jsonl_file, "r", encoding="utf-8-sig") as f: 
                for line in f: 
                    try: 
                        log = json.loads(line.strip()) 
                        combined_logs.append(log) 
                    except json.JSONDecodeError as e: 
                        print(f"Error decoding JSON in {jsonl_file}: {e}") 
                        continue 
        except Exception as e: 
            print(f"Error reading {jsonl_file}: {e}") 
            continue 
 
    # Save combined logs to a single JSONL file 
    try: 
        with open(output_jsonl_path, "w", encoding="utf-8") as f: 
            for log in combined_logs: 
                f.write(json.dumps(log) + "\n") 
        print(f"Combined logs saved to {output_jsonl_path}") 
    except Exception as e: 
        print(f"Error saving combined logs: {e}") 
        exit(1) 
 
# Function to filter logs for Chrome-related entries 
def filter_chrome_logs(output_jsonl_path, output_filtered_jsonl_path): 
    # Load the combined logs file 
    try: 
        print(f"Loading logs from {output_jsonl_path}...") 
        chrome_logs = [] 
        with open(output_jsonl_path, "r", encoding="utf-8-sig") as f: 
            for line in f: 
                try: 
                    log = json.loads(line.strip()) 
                    # Define keywords to search for Chrome-related entries 
                    chrome_keywords = ["chrome.exe", "google", "chrome"] 
                    # Check if any keyword is present in the log (case-insensitive) 
                    if any(keyword.lower() in str(log).lower() for keyword in chrome_keywords): 
                        chrome_logs.append(log) 
                except json.JSONDecodeError as e: 
                    print(f"Error decoding JSON in {output_jsonl_path}: {e}") 
                    continue 
    except Exception as e: 
        print(f"Error loading {output_jsonl_path}: {e}") 
        exit(1) 
 
    # Save the filtered logs to a JSONL file 
    try: 
        with open(output_filtered_jsonl_path, "w", encoding="utf-8") as f: 
            for log in chrome_logs: 
                f.write(json.dumps(log) + "\n") 
        print(f"Filtered logs saved to {output_filtered_jsonl_path}") 
    except Exception as e: 
        print(f"Error saving filtered logs: {e}") 
        exit(1) 
 
# Function to run hindsight.exe 
def run_hindsight(hindsight_exe_path, chrome_user_data_path, output_file_name): 
    command = [ 
        hindsight_exe_path, 
        "-i", chrome_user_data_path, 
        "-o", output_file_name, 
        "-b", "Chrome", 
        "-f", "jsonl" 
    ] 
    try: 
        result = subprocess.run(command, check=True, text=True, capture_output=True) 
        print("hindsight.exe executed successfully!") 
        print("Output:", result.stdout) 
    except subprocess.CalledProcessError as e: 
        print("Error occurred while running hindsight.exe:") 
        print("Return code:", e.returncode) 
        print("Error output:", e.stderr) 
        raise  # Re-raise the exception to stop further execution 
 
# Function to extract target paths from JSONL file 
def extract_target_paths(jsonl_file): 
    target_paths = [] 
    with open(jsonl_file, 'r', encoding='utf-8') as f: 
        for line in f: 
            try: 
                data = json.loads(line) 
                if 'target_path' in data: 
                    target_paths.append(data['target_path']) 
            except json.JSONDecodeError as e: 
                print(f"Error decoding JSON: {e}") 
                continue 
    return target_paths 
 
# Function to run exiftool 
def run_exiftool(file_path, exiftool_path): 
    try: 
        result = subprocess.run([exiftool_path, file_path], capture_output=True, text=True, check=True) 
        return result.stdout 
    except subprocess.CalledProcessError as e: 
        print(f"Error running exiftool on {file_path}: {e}") 
        return None 
 
# Function to parse exiftool output 
def parse_exiftool_output(output): 
    metadata = {} 
    for line in output.splitlines(): 
        if ':' in line: 
            key, value = line.split(':', 1) 
            metadata[key.strip()] = value.strip() 
    return metadata 
 
# Time parsing functions 
def parse_hindsight_time(time_str): 
    return datetime.fromisoformat(time_str.replace('Z', '+00:00')) 
 
def parse_exiftool_time(time_str): 
    dt_str, tz_str = time_str.split('+') 
    dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S") 
     
    # Handle timezone offset manually 
    hours, minutes = map(int, tz_str.split(':')) 
    offset = timedelta(hours=hours, minutes=minutes) 
    tz = timezone(offset) 
     
    return dt.replace(tzinfo=tz) 
 
def parse_evtx_time(time_str): 
    # Remove fractional seconds if present and truncate to 6 digits 
    parts = time_str.split('.') 
    if len(parts) > 1: 
        fractional_part = parts[1].split('+')[0] 
        if len(fractional_part) > 6: 
            fractional_part = fractional_part[:6] 
        iso_str = parts[0] + '.' + fractional_part + '+00:00' 
    else: 
        iso_str = parts[0] + '+00:00' 
     
    return datetime.fromisoformat(iso_str) 
 
def normalize_to_utc(dt): 
    return dt.astimezone(timezone.utc) 
 
def process_hindsight_line(line): 
    data = json.loads(line) 
    dt = parse_hindsight_time(data['datetime']) 
    return [{ 
        "Specific_Time_Line_Point": normalize_to_utc(dt).isoformat().replace('+00:00', 'Z'), 
        "Original_Tool_Used": "Hindsight", 
        **{k:v for k,v in data.items() if k != 'datetime'} 
    }] 
 
def process_exiftool_line(line): 
    data = json.loads(line) 
    entries = [] 
    for field in ["File Modification Date/Time", "File Access Date/Time", "File Creation Date/Time"]: 
        if field in data: 
            dt = parse_exiftool_time(data[field]) 
            entry = { 
                "Specific_Time_Line_Point": normalize_to_utc(dt).isoformat().replace('+00:00', 'Z'), 
                "Original_Tool_Used": "exiftool", 
                **{k:v for k,v in data.items() if k != field} 
            } 
            entries.append(entry) 
    return entries 
 
def process_evtx_line(line): 
    data = json.loads(line) 
    dt = parse_evtx_time(data['TimeCreated']) 
    return [{ 
        "Specific_Time_Line_Point": normalize_to_utc(dt).isoformat().replace('+00:00', 'Z'), 
        "Original_Tool_Used": "evtxecmd", 
        **{k:v for k,v in data.items() if k != 'TimeCreated'} 
    }] 
 
def jsonl_to_dataframe(jsonl_file): 
    data = [] 
    with open(jsonl_file, 'r', encoding='utf-8') as f: 
        for line in f: 
            try: 
                data.append(json.loads(line)) 
            except json.JSONDecodeError as e: 
                print(f"Error decoding JSON: {e}") 
                continue 
    return pd.DataFrame(data) 
 
def main(): 
    # Set up argument parser 
    parser = argparse.ArgumentParser(description="Process EVTX logs and Chrome user data.") 
    parser.add_argument("-ud", "--user_data", required=True, help="Path to Chrome user data directory.") 
    parser.add_argument("-evtx", "--evtx_path", required=True, help="Path to EVTX files directory.") 
    args = parser.parse_args() 
 
    # Get the directory where the script is located 
    script_dir = os.path.dirname(os.path.abspath(__file__)) 
 
    # Define paths relative to the script directory 
    evtx_files_path = args.evtx_path  # Path to EVTX files (from command-line argument) 
    evtxecmd_path = os.path.join(script_dir, "EvtxeCmd", "EvtxECmd.exe")  # Path to EVTXECmd.exe 
    output_json_folder = os.path.join(script_dir, "AllLogs")  # Folder created by EVTXECmd 
    output_jsonl_path = os.path.join(script_dir, "CombinedLogs.jsonl")  # Combined logs file in JSONL format 
    output_filtered_jsonl_path = os.path.join(script_dir, "ChromeLogs.jsonl")  # Filtered logs file 
 
    hindsight_exe_path = os.path.join(script_dir, "hindsight.exe")  # Path to hindsight.exe 
    exiftool_path = os.path.join(script_dir, "exiftool", "exiftool.exe")  # Path to exiftool.exe 
    #lack of .jsonl due to how hindisght.exe works with -jsonf 
    hindsight_output_jsonl_file = os.path.join(script_dir, "hindsight_output")  # Output JSONL file from hindsight.exe 
    exiftool_output_jsonl_file = os.path.join(script_dir, "exiftool_output.jsonl")  # Output JSONL file for exiftool results 
 
    chrome_user_data_path = args.user_data  # Path to Chrome user data (from command-line argument) 
 
    # Define specific log types to process 
    log_types = ["Security", "Application", "System"] 
 
    # Ensure the script is running as administrator 
    run_as_admin() 
 
    # Step 1: Run EVTXECmd to generate logs for specific log types 
    run_evtxecmd(evtxecmd_path, evtx_files_path, output_json_folder, log_types) 
 
    # Step 2: Combine JSONL files into a single JSONL file 
    combine_jsonl_files(output_json_folder, output_jsonl_path, log_types) 
 
    # Step 3: Filter logs for Chrome-related entries 
    filter_chrome_logs(output_jsonl_path, output_filtered_jsonl_path) 
 
    # Step 4: Run hindsight.exe to generate the JSONL file 
    run_hindsight(hindsight_exe_path, chrome_user_data_path, hindsight_output_jsonl_file) 
 
    # Step 5: Extract target paths from the JSONL file 
    hindsight_output_jsonl_file = hindsight_output_jsonl_file + ".jsonl" 
    target_paths = extract_target_paths(hindsight_output_jsonl_file) 
 
    # Step 6: Process each target path with exiftool 
    with open(exiftool_output_jsonl_file, 'w', encoding='utf-8') as f: 
        for file_path in target_paths: 
            if os.path.exists(file_path): 
                output = run_exiftool(file_path, exiftool_path) 
                if output: 
                    metadata = parse_exiftool_output(output) 
                    json.dump(metadata, f) 
                    f.write('\n') 
            else: 
                print(f"File not found: {file_path}") 
 
    # Step 7: Combine all logs into a unified timeline 
    all_entries = [] 
 
    # Process Hindsight data 
    with open(hindsight_output_jsonl_file, 'r') as f: 
        for line in f: 
            all_entries.extend(process_hindsight_line(line)) 
 
    # Process exiftool data 
    with open(exiftool_output_jsonl_file, 'r') as f: 
        for line in f: 
            all_entries.extend(process_exiftool_line(line)) 
 
    # Process evtxecmd data 
    with open(output_filtered_jsonl_path, 'r') as f: 
        for line in f: 
            all_entries.extend(process_evtx_line(line)) 
 
    # Sort chronologically 
    all_entries.sort(key=lambda x: datetime.fromisoformat(x['Specific_Time_Line_Point'].replace('Z', '+00:00'))) 
 
    # Write output 
    with open('unified_timeline.jsonl', 'w') as f: 
        for entry in all_entries: 
            f.write(json.dumps(entry) + '\n') 
             
    unified_output_jsonl_file = os.path.join(script_dir, "unified_timeline.jsonl") 
 
    # Convert JSONL files to Excel sheets 
    with pd.ExcelWriter('logs_summary.xlsx') as writer: 
        jsonl_to_dataframe(unified_output_jsonl_file).to_excel(writer, sheet_name='Unified Timeline', index=False) 
        jsonl_to_dataframe(hindsight_output_jsonl_file).to_excel(writer, sheet_name='Hindsight Output', index=False) 
        jsonl_to_dataframe(exiftool_output_jsonl_file).to_excel(writer, sheet_name='Exiftool Output', index=False) 
        jsonl_to_dataframe(output_filtered_jsonl_path).to_excel(writer, sheet_name='EvtxECmd Filtered', index=False) 
        jsonl_to_dataframe(output_jsonl_path).to_excel(writer, sheet_name='EvtxECmd Full', index=False) 
 
if __name__ == "__main__": 
    main()