import json
import os
import pathlib

current_file_path = os.path.abspath(__file__)
current_repo_path = os.path.normpath(os.path.join(current_file_path, "..", "..", ".."))
user_config_file_path = os.path.normpath(
    os.path.join(current_repo_path, "data", "user_config.json")
)


def read_config_parameter(parameter_path):
    """ ""\"
    ""\"
    Read a specific parameter from user_config.json (if available).

    Parameters:
    - parameter_path: Dot-separated path to the parameter (e.g., "view_options.is_directory_view_visible")

    Returns:
    - The value of the parameter if found, otherwise None.
    ""\"
    ""\" """

    def get_nested_value(data_dict, keys_list):
        """ ""\"
        ""\"
            get_nested_value

                Args:
                    data_dict (Any): Description of data_dict.
                    keys_list (Any): Description of keys_list.

                Returns:
                    None: Description of return value.
            ""\"
        ""\" """
        current_level = data_dict
        for key in keys_list:
            if isinstance(current_level, dict) and key in current_level:
                current_level = current_level[key]
            else:
                return None
        return current_level

    path_parts = parameter_path.split(".")
    try:
        with open(user_config_file_path, "r") as user_config_file:
            user_config_data = json.load(user_config_file)
            value = get_nested_value(user_config_data, path_parts)
            return value
    except Exception as e:
        print(f"Error reading user_config.json: {e}")
        return None


def write_config_parameter(parameter_path, parameter_value):
    """ ""\"
    ""\"
    Write a parameter and its value to user_config.json, creating the file if necessary.

    Parameters:
    - parameter_path: Dot-separated path to the parameter (e.g., "view_options.is_directory_view_visible")
    - parameter_value: Value to assign to the parameter.

    Returns:
    - True if the parameter was successfully written, otherwise False.
    ""\"
    ""\" """
    try:
        with open(user_config_file_path, "r") as user_config_file:
            user_config_data = json.load(user_config_file)
    except Exception as e:
        print(f"Error reading user_config.json: {e}")
        return False
    path_parts = parameter_path.split(".")
    current_level = user_config_data
    for part in path_parts[:-1]:
        if part not in current_level:
            current_level[part] = {}
        current_level = current_level[part]
    current_level[path_parts[-1]] = parameter_value
    try:
        with open(user_config_file_path, "w") as user_config_file:
            json.dump(user_config_data, user_config_file, indent=4)
        return True
    except Exception as e:
        print(f"Error writing user_config.json: {e}")
        return False


def get_scriptsstudio_directory():
    """ ""\"
    ""\"
    get_scriptsstudio_directory

    Args:
        None

    Returns:
        None: Description of return value.
    ""\"
    ""\" """
    project_directory = os.getcwd()
    abs_path = os.path.abspath(project_directory)
    data_path = abs_path + "\\data"
    write_config_parameter("options.file_management.current_working_directory", "")
    write_config_parameter("options.file_management.current_file_path", "")
    write_config_parameter("options.file_management.scriptsstudio_directory", abs_path)
    write_config_parameter(
        "options.file_management.scriptsstudio_data_directory", data_path
    )
    write_config_parameter(
        "options.file_management.scriptsstudio_config_path", data_path + "\\config.json"
    )
    write_config_parameter(
        "options.file_management.scriptsstudio_user_config_path",
        data_path + "\\user_config.json",
    )
    return abs_path


def ensure_user_config():
    """ ""\"
    ""\"
    ensure_user_config

    Args:
        None

    Returns:
        None: Description of return value.
    ""\"
    ""\" """
    config_path = "data/config.json"
    user_config_path = "data/user_config.json"
    if not os.path.exists(user_config_path):
        with open(config_path, "r") as config_file:
            with open(user_config_path, "w") as user_config_file:
                user_config_file.write(config_file.read())
    else:
        pass


def load_theme_setting():
    theme = read_config_parameter("options.theme_appearance.theme")
    if theme is None:
        theme = "cosmo"
    return theme
