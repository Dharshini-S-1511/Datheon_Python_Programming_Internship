"""Hangman - tkinter GUI version (bonus). Uses words.txt if available."""
import random
import string
import tkinter as tk
from tkinter import messagebox

MAX_MISTAKES = 6
WORDS_FILE = "words.txt"
FALLBACK_WORDS = ["python", "pantheon", "variable", "function", "keyboard",
                  "algorithm", "compiler", "database", "network", "program"]


def load_words(path=WORDS_FILE):
    try:
        with open(path, encoding="utf-8") as f:
            words = [w.strip().lower() for w in f
                     if w.strip().isalpha() and len(w.strip()) >= 4]
        if words:
            return words
    except OSError:
        pass
    return FALLBACK_WORDS


class HangmanGUI:
    def __init__(self, root):
        self.root = root
        self.words = load_words()
        root.title("Hangman")
        root.minsize(600, 450)
        root.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(root, width=240, height=260, bg="white")
        self.canvas.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.canvas.bind("<Configure>", lambda e: self.draw())

        right = tk.Frame(root)
        right.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.word_label = tk.Label(right, font=("Courier", 24, "bold"))
        self.word_label.pack(pady=10, expand=True)
        self.info_label = tk.Label(right, font=("Arial", 12))
        self.info_label.pack()
        self.msg_label = tk.Label(right, font=("Arial", 11), fg="gray")
        self.msg_label.pack(pady=5)
        right.bind("<Configure>", self.on_resize)

        keys = tk.Frame(root)
        keys.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        self.buttons = {}
        for i, ch in enumerate(string.ascii_lowercase):
            b = tk.Button(keys, text=ch.upper(), width=3,
                          command=lambda c=ch: self.guess(c))
            b.grid(row=i // 9, column=i % 9, padx=2, pady=2)
            self.buttons[ch] = b

        tk.Button(root, text="New Game", command=self.new_game).grid(
            row=2, column=0, columnspan=2, pady=(0, 10))
        root.bind("<Key>", self.on_key)
        self.new_game()

    def new_game(self):
        self.word = random.choice(self.words)
        self.guessed = set()
        self.mistakes = set()
        self.over = False
        for b in self.buttons.values():
            b.config(state="normal")
        self.msg_label.config(text="Pick a letter!", fg="gray")
        self.refresh()

    def on_key(self, event):
        ch = event.char.lower()
        if len(ch) == 1 and ch in self.buttons:
            self.guess(ch)

    def guess(self, ch):
        if self.over or ch in self.guessed or ch in self.mistakes:
            return  # duplicate guesses are ignored, no penalty
        self.buttons[ch].config(state="disabled")
        if ch in self.word:
            self.guessed.add(ch)
            self.msg_label.config(text=f"'{ch}' is in the word!", fg="green")
        else:
            self.mistakes.add(ch)
            self.msg_label.config(text=f"'{ch}' is not in the word.", fg="red")
        self.refresh()
        self.check_end()

    def refresh(self):
        shown = " ".join(c if c in self.guessed else "_" for c in self.word)
        self.word_label.config(text=shown)
        self.info_label.config(
            text=f"Wrong: {' '.join(sorted(self.mistakes)) or '-'}\n"
                 f"Attempts left: {MAX_MISTAKES - len(self.mistakes)}")
        self.draw()

    def on_resize(self, event):
        size = max(24, min(event.width // 12, 60))
        self.word_label.config(font=("Courier", size, "bold"))
        self.info_label.config(font=("Arial", max(12, size // 2)))
        self.msg_label.config(font=("Arial", max(11, size // 2)))

    def draw(self):
        c, n = self.canvas, len(self.mistakes)
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        s = min(w / 240, h / 260)          # scale factor
        ox, oy = (w - 240 * s) / 2, (h - 260 * s) / 2
        lw = max(3, int(3 * s))

        def line(x1, y1, x2, y2):
            c.create_line(ox + x1 * s, oy + y1 * s, ox + x2 * s, oy + y2 * s,
                          width=lw)

        line(20, 240, 120, 240)    # base
        line(70, 240, 70, 20)      # pole
        line(70, 20, 160, 20)      # beam
        line(160, 20, 160, 50)     # rope
        if n >= 1:                 # head
            c.create_oval(ox + 140 * s, oy + 50 * s, ox + 180 * s,
                          oy + 90 * s, width=lw)
        if n >= 2: line(160, 90, 160, 160)     # body
        if n >= 3: line(160, 105, 130, 140)    # left arm
        if n >= 4: line(160, 105, 190, 140)    # right arm
        if n >= 5: line(160, 160, 135, 205)    # left leg
        if n >= 6: line(160, 160, 185, 205)    # right leg

    def check_end(self):
        if set(self.word) <= self.guessed:
            self.finish(f"YOU WIN! 🎉\nThe word was '{self.word}'.", "green")
        elif len(self.mistakes) >= MAX_MISTAKES:
            self.finish(f"GAME OVER!\nThe word was '{self.word}'.", "red")

    def finish(self, text, color):
        self.over = True
        for b in self.buttons.values():
            b.config(state="disabled")
        self.msg_label.config(text=text.split("\n")[0], fg=color)
        if messagebox.askyesno("Hangman", text + "\n\nPlay again?"):
            self.new_game()


if __name__ == "__main__":
    root = tk.Tk()
    HangmanGUI(root)
    root.mainloop()
