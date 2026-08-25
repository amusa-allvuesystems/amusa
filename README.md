# Technology Experience Feedback

A Streamlit feedback form for collecting and prioritizing workplace technology improvements. It covers meeting room consistency, collaboration tools such as Microsoft Teams, hybrid work, executive support, service visibility, proactive support, and business value.

## Run the feedback form

The form stores responses in the active browser session and provides a CSV download with all collected responses. It does not send feedback to a server.

```bash
chmod +x run-gui.sh
./run-gui.sh
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
az login
streamlit run gui/app.py
```

Open `http://localhost:8501` after Streamlit starts.
