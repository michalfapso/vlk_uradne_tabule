import os
import json
import re
import sys
from datetime import datetime

_REDACT_PATTERN = re.compile(r'(?i)([\?&]key=)[A-Za-z0-9_\-]{20,}')

def log_status(status_filepath: str, level: str, msg: str):
    """Logs a message to stderr and appends it to a JSON status file."""
    # Ensure msg is a string, handle potential complex exception objects
    if not isinstance(msg, str):
        msg = str(msg)

    print(f"[{level.upper()}]: {msg}", file=sys.stderr)

    if not status_filepath: # Cannot log to file if path is not provided
        return

    current_date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {"date": current_date_str, "type": level, "text": msg}
    
    data = []
    if os.path.exists(status_filepath):
        try:
            with open(status_filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip(): # Check if file is not empty
                    data = json.loads(content)
                    if not isinstance(data, list):
                        print(f"[WARNING] Status file {status_filepath} contained non-list JSON. It will be overwritten.", file=sys.stderr)
                        data = []
        except (json.JSONDecodeError, FileNotFoundError, Exception) as e: # Catch more errors during read
            print(f"[WARNING] Could not read or parse status file {status_filepath} (Error: {e}). It will be overwritten.", file=sys.stderr)
            data = []

    data.append(log_entry)

    try:
        # Ensure the directory for the status file exists
        status_dir = os.path.dirname(status_filepath)
        if status_dir: # Check if dirname is not empty (e.g. for status.json in current dir)
            os.makedirs(status_dir, exist_ok=True)

        with open(status_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[CRITICAL]: Failed to write to status file {status_filepath}: {e}", file=sys.stderr)

class Tee:
    def __init__(self, original_stream, log_file):
        self.original_stream = original_stream
        self.log_file = log_file

    def write(self, data):
        self.original_stream.write(data)
        if self.log_file and not self.log_file.closed:
            self.log_file.write(_REDACT_PATTERN.sub(r'\1***', data))

    def flush(self):
        self.original_stream.flush()
        if self.log_file and not self.log_file.closed:
            self.log_file.flush()

    def __getattr__(self, attr):
        return getattr(self.original_stream, attr)
