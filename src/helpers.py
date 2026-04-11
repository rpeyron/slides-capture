
import os
import re
import sys
import unicodedata


LOCAL_PATH = "."
try:
    LOCAL_PATH = sys._MEIPASS
except Exception:
    pass

def sanitize_text(text):
    normalized = unicodedata.normalize('NFKD', text or '')
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    clean = re.sub(r"[^A-Za-z0-9 ._\-]", " ", ascii_text)
    return re.sub(r"\s+", " ", clean).strip()


def clean_text(text):
    return re.sub(r"\s+", " ", (text or "")).strip()

def local_file(file):
    if os.path.isabs(file):
        return file
    return os.path.join(LOCAL_PATH, file)