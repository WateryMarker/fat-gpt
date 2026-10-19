# FAT-GPT

A Thai chatbot with a Windows XP look and a hunger meter. Feed it before asking questions. Its energy drains over time, food changes its mood, and a minigame lets you earn more calories.

The game includes Minecraft food, TNT, combos, and random memes. You can add your own images.

## Run on macOS

Open Terminal in the project folder:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python fat_gpt_mac_app.py
```

## Run on Windows

Install Python 3.14, download and extract the project, then open PowerShell in its folder:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe fat_gpt_app.py
```

After setup, use only the last command to launch the app. You do not need to activate `.venv`.
If you get `No module named PIL`, run the package installation command again.
Python must include Tkinter. Check with `python3 -m tkinter` on macOS or `py -3.14 -m tkinter` on Windows.
The app has not been tested on a Windows machine yet.

## Chat and voice settings

The default connection is Ollama at `http://localhost:11434/v1` with `qwen2.5:14b`.
Start Ollama and install that model, or choose an installed model in the app's settings.
You can also enter a base URL, model name, and API key for a compatible API. The app does not save the key to a file.

Voice uses [edge-tts](https://github.com/rany2/edge-tts) with the Thai male voice Niwat and currently works only on macOS.
Use the button at the top of the app to turn it on or off. Speech generation requires an internet connection and sends the reply text to Microsoft's service.

## Add memes

Put images in `memes/` or next to the app. Supported formats are PNG, JPG, JPEG, WEBP, and the first frame of a GIF.

Minecraft images and sounds belong to Mojang / Microsoft. This is an unofficial fan project.
Sources are listed in [assets/minecraft](assets/minecraft/README.md) and its `sources.json` files.
