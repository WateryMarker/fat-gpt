"""macOS entry point for FAT-GPT."""
import tkinter as tk
from fat_gpt_app import FatGPTApp

if __name__ == "__main__":
    root = tk.Tk()
    app = FatGPTApp(root)
    root.mainloop()
