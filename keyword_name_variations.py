import json
import keyword


def make_variation(name, word):
    """Create a repeatable name variation influenced by a Python keyword."""
    remaining = list(name.lower())
    front = []

    for letter in word.lower():
        if letter in remaining:
            front.append(letter)
            remaining.remove(letter)

    rotation_size = min(len(remaining), len(word) + 1)
    if rotation_size > 1:
        rotated = remaining[1:rotation_size] + remaining[:1]
        remaining = rotated + remaining[rotation_size:]

    return "".join(front + remaining)


def make_unique_variation(name, word, used_variations):
    variation = make_variation(name, word)
    if variation not in used_variations:
        return variation

    base_variation = variation
    suffix_number = 2
    while variation in used_variations:
        variation = f"{base_variation}{suffix_number}"
        suffix_number += 1

    return variation


def ask_for_name():
    while True:
        name = input("Enter a name with at least 5 characters: ").strip()
        if len(name) >= 5:
            return name

        print("Name must be at least 5 characters long. Try again.")


def main():
    name = ask_for_name()
    variations = {}
    used_variations = set()

    for word in keyword.kwlist:
        variation = make_unique_variation(name, word, used_variations)
        variations[word] = variation
        used_variations.add(variation)

    output_file = f"{name.lower()}_python_keywords.json"
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(variations, file, indent=2)

    print(f"Created {output_file} with {len(variations)} keyword variations.")


if __name__ == "__main__":
    main()
