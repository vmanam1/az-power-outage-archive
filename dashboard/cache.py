import os
import threading

class ThreadSafeCache:
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()

    def get(self, file_path):
        """
        Retrieves cached data if the file exists and has not been modified.
        If the file has been modified or doesn't exist, returns None.
        """
        with self._lock:
            if not os.path.exists(file_path):
                self._cache.pop(file_path, None)
                return None
            
            try:
                mtime = os.path.getmtime(file_path)
            except OSError:
                return None
                
            cached_item = self._cache.get(file_path)
            if cached_item and cached_item["mtime"] == mtime:
                return cached_item["data"]
            return None

    def set(self, file_path, data):
        """
        Caches the parsed data for the given file_path, storing the current mtime.
        """
        with self._lock:
            if os.path.exists(file_path):
                try:
                    mtime = os.path.getmtime(file_path)
                    self._cache[file_path] = {
                        "mtime": mtime,
                        "data": data
                    }
                except OSError:
                    pass

    def clear(self):
        """
        Clears all cached entries.
        """
        with self._lock:
            self._cache.clear()

global_cache = ThreadSafeCache()
