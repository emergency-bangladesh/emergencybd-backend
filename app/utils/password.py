import random
import string


def generate_random_password(length: int = 8) -> str:
    if length < 4:
        raise ValueError("Password length must be at least 4 characters")

    # Define character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special_chars = "!@#$%^&*()_-+=<>?/[]{}|"

    # Ensure at least one character from each category
    password = [
        random.choice(uppercase),
        random.choice(lowercase),
        random.choice(digits),
        random.choice(special_chars),
    ]

    # Fill the rest with random characters from all categories
    all_chars = uppercase + lowercase + digits + special_chars
    password.extend(random.choices(all_chars, k=length - 4))

    # Shuffle to avoid predictable pattern
    random.shuffle(password)

    return "".join(password)
