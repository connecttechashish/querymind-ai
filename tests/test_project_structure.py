from pathlib import Path

def test_project_files_exist():
    # Define expected files relative to backend project root
    expected_files = [
        "src/querymindai_backend/__init__.py",
        "src/querymindai_backend/constants.py",
        "src/querymindai_backend/config.py",
        "src/querymindai_backend/logging_config.py",
        ".env.example",
        ".gitignore",
        "README.md",
    ]
    
    # Resolve backend root path relative to this test file
    test_dir = Path(__file__).parent
    backend_root = test_dir.parent
    
    for relative_path in expected_files:
        full_path = backend_root / relative_path
        assert full_path.exists(), f"Expected file does not exist: {relative_path}"
        assert full_path.is_file(), f"Expected path is not a file: {relative_path}"
