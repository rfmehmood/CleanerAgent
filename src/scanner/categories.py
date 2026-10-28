class ScanCategory:
    TEMP_FILES = "Temporary Files"
    APP_CACHE = "Application Caches"
    BROWSER_CACHE = "Browser Caches"
    LEFTOVERS = "Application Leftovers"
    PYTHON_CONDA = "Python & Conda Caches"
    NODE_JS = "Node.js & Package Managers"
    AI_MODELS = "AI Model Storage"
    LARGE_FILES = "Large Files (>500MB)"
    DUPLICATES = "Duplicate Files"
    LOGS_CRASH = "Logs & Crash Dumps"
    RECYCLE_BIN = "Recycle Bin"
    BUILD_ARTIFACTS = "Build Artifacts"
    GENERAL = "General Storage"

ALL_CATEGORIES = [
    ScanCategory.TEMP_FILES,
    ScanCategory.APP_CACHE,
    ScanCategory.BROWSER_CACHE,
    ScanCategory.LEFTOVERS,
    ScanCategory.PYTHON_CONDA,
    ScanCategory.NODE_JS,
    ScanCategory.AI_MODELS,
    ScanCategory.LARGE_FILES,
    ScanCategory.DUPLICATES,
    ScanCategory.LOGS_CRASH,
    ScanCategory.RECYCLE_BIN,
    ScanCategory.BUILD_ARTIFACTS,
]
