import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Launch the Streamlit frontend application."""
    # Get the directory where this __init__.py file is located
    frontend_dir = Path(__file__).parent
    app_path = frontend_dir / "app.py"

    if not app_path.exists():
        print(f"Error: Streamlit app not found at {app_path}")
        sys.exit(1)

    print("🚀 Starting Multi-Provider LLM Chat Interface...")
    print(f"📁 App location: {app_path}")
    print("🌐 Opening in your default browser...")

    # Launch Streamlit
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(app_path),
                "--server.address",
                "localhost",
                "--server.port",
                "8501",
                "--browser.gatherUsageStats",
                "false",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error launching Streamlit: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
