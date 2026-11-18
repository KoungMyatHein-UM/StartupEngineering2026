# Smart Pantry (PoC)

A crate on a USB scale, watched by two USB cameras. When the weight changes, the cameras take a
picture, a local vision model (VLM) identifies the item, and the inventory ledger keeps track of
what's in the pantry: grams, servings, calories, fat, protein and carbs.

## Setup

### 1. Python packages

```
pip install -r requirements.txt
```

### 2. Ollama (runs the VLM locally)

Ollama is not a Python package, so it's installed separately.

- **Windows / macOS:** download and install it from https://ollama.com/download
- Check that it's installed and recent enough (0.12.7 or newer is needed for Qwen3-VL):

  ```
  ollama --version
  ```

### 3. The vision model

```
ollama pull qwen3-vl:8b-instruct
```

This downloads about 6 GB. Use the **instruct** variant: the default `qwen3-vl:8b` thinks before
answering, which makes it slow and can cut off its answer.

## Running

1. Make sure Ollama is running (its icon is in the taskbar tray on Windows, or in the menu bar
   on macOS). If it isn't, start it from the Start menu / Applications, or run `ollama serve`
   in a separate terminal.
2. Switch on the scale and put the empty crate on it.
3. Run:

   ```
   python main.py
   ```

4. Wait for `ALL READY`, then put items in or take them out. Press **Ctrl+C** to quit.

## Notes

- **Run it in a real terminal** (Windows Terminal, the macOS Terminal, or PyCharm's Terminal tab)
  so the colour dashboard redraws in place. In PyCharm's Run window, turn on
  *Run → Edit Configurations → Emulate terminal in output console*.
- **macOS camera permission:** the first time, macOS asks whether your terminal (or PyCharm) may
  use the cameras. Allow it, or the cameras won't open.
- **MacBook built-in camera:** camera index 0 is skipped on macOS, because that's the built-in
  camera. Keep the lid open; with the lid closed, a USB camera can become index 0 and be skipped.
- **The scale turns itself off** after a few minutes without changes. The app waits for it and
  carries on once you switch it back on.
- **Items** are defined in `data/items.json`: nutrition per gram, serving size and packaging weight.
  The item names there are also the names the VLM answers with.