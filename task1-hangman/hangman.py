"""Hangman - console word guessing game."""
import os
import random

MAX_MISTAKES = 6
WORDS_FILE = "words.txt"  # the downloaded English word list
FALLBACK_WORDS = ["python", "pantheon", "variable", "function", "keyboard",
                  "algorithm", "compiler", "database", "network", "program"]

STAGES = [
    """
  +---+
  |   |
      |
      |
      |
      |
=========""",
    """
  +---+
  |   |
  O   |
      |
      |
      |
=========""",
    """
  +---+
  |   |
  O   |
  |   |
      |
      |
=========""",
    """
  +---+
  |   |
  O   |
 /|   |
      |
      |
=========""",
    """
  +---+
  |   |
  O   |
 /|\\  |
      |
      |
=========""",
    """
  +---+
  |   |
  O   |
 /|\\  |
 /    |
      |
=========""",
    """
  +---+
  |   |
  O   |
 /|\\  |
 / \\  |
      |
=========""",
]


def load_words(path=WORDS_FILE):
    """Load words (alphabetic, 4+ letters) from file, else use fallback list."""
    try:
        with open(path, encoding="utf-8") as f:
            words = [w.strip().lower() for w in f
                     if w.strip().isalpha() and len(w.strip()) >= 4]
        if words:
            return words
    except OSError:
        pass
    return FALLBACK_WORDS


def mask_word(word, guessed):
    return " ".join(ch if ch in guessed else "_" for ch in word)


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def draw(word, guessed, mistakes, message=""):
    clear()
    print("=== HANGMAN ===")
    print(STAGES[len(mistakes)])
    print(f"\nWord:    {mask_word(word, guessed)}")
    print(f"Wrong:   {' '.join(sorted(mistakes)) or '-'}")
    print(f"Guessed: {' '.join(sorted(guessed | mistakes)) or '-'}")
    print(f"Attempts left: {MAX_MISTAKES - len(mistakes)}")
    if message:
        print(f"\n{message}")


def get_guess(guessed, mistakes):
    """Prompt until a valid, not-yet-guessed single letter is entered."""
    while True:
        guess = input("\nGuess a letter: ").strip().lower()
        if len(guess) != 1 or not guess.isalpha():
            print("Please enter a single letter (a-z).")
        elif guess in guessed or guess in mistakes:
            print(f"You already guessed '{guess}'. Try another.")
        else:
            return guess


def play_round(word):
    guessed, mistakes = set(), set()
    message = ""
    while len(mistakes) < MAX_MISTAKES and not set(word) <= guessed:
        draw(word, guessed, mistakes, message)
        guess = get_guess(guessed, mistakes)
        if guess in word:
            guessed.add(guess)
            message = f"Good guess! '{guess}' is in the word."
        else:
            mistakes.add(guess)
            message = f"Sorry, '{guess}' is not in the word."

    draw(word, guessed, mistakes)
    if set(word) <= guessed:
        print(f"\n*** YOU WIN! The word was '{word}'. ***")
    else:
        print(f"\n*** GAME OVER! The word was '{word}'. ***")


def main():
    words = load_words()
    while True:
        play_round(random.choice(words))
        if input("\nPlay again? (y/n): ").strip().lower() != "y":
            print("Thanks for playing!")
            break


if __name__ == "__main__":
    main()
