import json
from pathlib import Path

DATA_DIR = Path("data")
USER_ENTRY_FILE = DATA_DIR / "user-entry.json"
ABUSIVE_WORDS_FILE = DATA_DIR / "abusive-words.json"
TWEETS_SAMPLE_FILE = DATA_DIR / "tweet-sample.json"


def load_data_from_file(file_path: Path, return_dict: bool = False) -> dict:
    """
    Loads JSON data from a file.

    Args:
        file_path (Path): The path to the JSON file to load.
        return_dict (bool, optional): If True and the loaded data is a list, returns a dictionary
            with stringified integer keys starting from '1'. If False, returns the data as loaded.
            Defaults to False.

    Returns:
        dict: The loaded data as a dictionary. If the file contains a list and return_dict is True,
            returns a dictionary with string keys. Returns an empty dictionary if the file is not found
            or if there is a JSON decoding error.

    Raises:
        None. Errors are caught and printed; an empty dictionary is returned on failure.
    """

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            if not return_dict:
                return data
            else:
                return (
                    {str(i + 1): v for i, v in enumerate(data)}
                    if isinstance(data, list)
                    else data
                )
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file: {file_path} - {e}")
        return {}
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return {}


if __name__ == "__main__":
    DICT_KEY = "1"  # Example key to access the first entry in the loaded data

    # Load and print data from the specified files
    print("Loading data from files...")
    print(USER_ENTRY_FILE)
    print(json.dumps(load_data_from_file(USER_ENTRY_FILE)["1"], indent=2))

    print(TWEETS_SAMPLE_FILE)
    print(
        json.dumps(
            load_data_from_file(TWEETS_SAMPLE_FILE, return_dict=True)["1"], indent=2
        )
    )

    print(ABUSIVE_WORDS_FILE)
    print(
        json.dumps(
            load_data_from_file(ABUSIVE_WORDS_FILE, return_dict=True)["1"], indent=2
        )
    )
