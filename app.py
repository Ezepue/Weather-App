"""WSGI entry point.

Kept at the repository root because Vercel, gunicorn and `python app.py` all
look for it here.
"""

from weatherapp import create_app

app = create_app()

if __name__ == "__main__":
    import os

    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        # Opt in explicitly: the debugger allows arbitrary code execution.
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
