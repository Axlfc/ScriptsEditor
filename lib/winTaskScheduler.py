import subprocess
import argparse
import datetime
import re

"""
Lista de parámetros: 
x /Create         Crea una nueva tarea programada.
x /Delete         Elimina las tareas programadas.
x /Query          Muestra todas las tareas programadas.
/Change         Cambia las propiedades de la tarea programada.
/Run            Ejecuta la tarea programada a petición.
/End            Detiene la tarea programada que se está ejecutando actualmente.
/ShowSid        Muestra el identificador de seguridad correspondiente al nombre de una tarea programada.

# https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/?view=windowsserver2019-ps
"""
windows_tasks_file_path = "C:\\Windows\\System32\\schtasks.exe"
windows_cmd_file_path = "C:\\Windows\\System32\\cmd.exe"


def format_time_input(time_str):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Formats a given time string into HH:MM:SS format.

        Parameters:
        time_str (str): The time string to format. Can be in various formats like '8', '8:30', '8:8:8'.

        Returns:
        datetime.time: A datetime.time object representing the formatted time.
    ""\"
    ""\"
    ""\"
    ""\" """
    parts = time_str.split(":")
    while len(parts) < 3:
        parts.append("00")
    formatted_parts = [str(int(part)).zfill(2) for part in parts]
    formatted_time_str = ":".join(formatted_parts)
    return datetime.datetime.strptime(formatted_time_str, "%H:%M:%S").time()


def parse_create_args(subparsers):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Adds argument parsing for the 'create' sub-command in the argparse parser.

        Parameters:
        subparsers (argparse._SubParsersAction): The subparsers action object from argparse.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    parser_create = subparsers.add_parser("create")
    parser_create.add_argument("name")
    parser_create.add_argument("start_time")
    parser_create.add_argument("schedule_type")
    parser_create.add_argument("--interval", default=None)
    parser_create.add_argument("--program", default=None)


def parse_delete_args(subparsers):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Adds argument parsing for the 'delete' sub-command in the argparse parser.

        Parameters:
        subparsers (argparse._SubParsersAction): The subparsers action object from argparse.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    parser_delete = subparsers.add_parser("delete")
    parser_delete.add_argument("name")


def parse_list_args(subparsers):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Adds argument parsing for the 'list' sub-command in the argparse parser.

        Parameters:
        subparsers (argparse._SubParsersAction): The subparsers action object from argparse.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    subparsers.add_parser("list")


def parse_change_args(subparsers):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Adds argument parsing for the 'change' sub-command in the argparse parser.

        Parameters:
        subparsers (argparse._SubParsersAction): The subparsers action object from argparse.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    parser_change = subparsers.add_parser("change")
    parser_change.add_argument("name")
    parser_change.add_argument("--program", default=None)
    parser_change.add_argument("--start_time", default=None)


def parse_run_args(subparsers):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Adds argument parsing for the 'run' sub-command in the argparse parser.

        Parameters:
        subparsers (argparse._SubParsersAction): The subparsers action object from argparse.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    parser_run = subparsers.add_parser("run")
    parser_run.add_argument("name")


def parse_end_args(subparsers):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Adds argument parsing for the 'end' sub-command in the argparse parser.

        Parameters:
        subparsers (argparse._SubParsersAction): The subparsers action object from argparse.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    parser_end = subparsers.add_parser("end")
    parser_end.add_argument("name")


def parse_showsid_args(subparsers):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Adds argument parsing for the 'showsid' sub-command in the argparse parser.

        Parameters:
        subparsers (argparse._SubParsersAction): The subparsers action object from argparse.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    parser_showsid = subparsers.add_parser("showsid")
    parser_showsid.add_argument("name")


def parse_at_args(subparsers):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Adds argument parsing for the 'at' sub-command in the argparse parser.

        Parameters:
        subparsers (argparse._SubParsersAction): The subparsers action object from argparse.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    parser_at = subparsers.add_parser("at")
    parser_at.add_argument("name")
    parser_at.add_argument("start_time")
    parser_at.add_argument("program")


def parse_crontab_args(subparsers):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Adds argument parsing for the 'crontab' sub-command in the argparse parser.

        Parameters:
        subparsers (argparse._SubParsersAction): The subparsers action object from argparse.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    parser_crontab = subparsers.add_parser("crontab")
    parser_crontab.add_argument("name")
    parser_crontab.add_argument("minute")
    parser_crontab.add_argument("hour")
    parser_crontab.add_argument("day")
    parser_crontab.add_argument("month")
    parser_crontab.add_argument("day_of_week")
    parser_crontab.add_argument("script_path")


def process_parse_args():
    """ ""\"
    ""\"
    ""\"
    ""\"
    Sets up the argument parser and subparsers for different task scheduling commands.

        Returns:
        argparse.Namespace: The parsed arguments as a Namespace object.
    ""\"
    ""\"
    ""\"
    ""\" """
    parser = argparse.ArgumentParser(description="Task Scheduler Wrapper")
    subparsers = parser.add_subparsers(dest="command")
    parse_create_args(subparsers)
    parse_delete_args(subparsers)
    parse_list_args(subparsers)
    parse_change_args(subparsers)
    parse_run_args(subparsers)
    parse_end_args(subparsers)
    parse_showsid_args(subparsers)
    parse_at_args(subparsers)
    parse_crontab_args(subparsers)
    return parser.parse_args()


def delete_task(name):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Deletes a scheduled task by name.

        Parameters:
        name (str): The name of the task to delete.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    command = [windows_tasks_file_path, "/Delete", "/TN", name, "/F"]
    try:
        subprocess.run(command, check=True)
        print(f"Successfully deleted task: {name}")
    except subprocess.CalledProcessError as e:
        print(f"Error deleting task: {e}")


def list_tasks():
    """ ""\"
    ""\"
    ""\"
    ""\"
    Lists all scheduled tasks, excluding tasks in specified folders.

        Returns:
        list: A list of detailed information about each scheduled task.
    ""\"
    ""\"
    ""\"
    ""\" """
    excluded_folders = [
        "\\Microsoft",
        "\\Adobe",
        "\\PowerToys",
        "\\Mozilla",
        "\\MEGA",
        "\\Opera",
        "\\NVIDIA",
        "\\NvTmRep",
        "\\NvProfileUpdaterOnLogon_",
        "\\NvProfileUpdaterDaily_",
        "\\NvNodeLauncher_",
        "\\NvDriverUpdateCheckDaily_",
        "\\NahimicTask",
        "\\NahimicSvc",
        "\\Dragon_Center",
        "\\MSI_Dragon",
        "\\MSISCMTsk",
        "\\MSIAfterburner",
        "\\CreateExplorerShellUnelevatedTask",
        "\\ViGEmBus",
        "\\GoogleSystem",
    ]
    list_command = [windows_tasks_file_path, "/Query", "/FO", "LIST"]
    process = subprocess.Popen(
        list_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    output, error = process.communicate()
    if error:
        print("Error:", error)
        return []
    tasks = output.strip().split("\n\n")
    filtered_tasks = [
        task for task in tasks if not any(folder in task for folder in excluded_folders)
    ]
    detailed_task_info = []
    for task in filtered_tasks:
        task_name_match = re.search(
            "Nombre de tarea:(\\s*\\\\[^\\\\]+\\\\)?\\s*([^\\r\\n]+)", task
        )
        if task_name_match:
            task_name = task_name_match.group(2).strip()
            detail_command = [
                windows_tasks_file_path,
                "/Query",
                "/TN",
                task_name,
                "/V",
                "/FO",
                "LIST",
            ]
            detail_process = subprocess.Popen(
                detail_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            detail_output, detail_error = detail_process.communicate()
            if detail_error:
                print(f"Error getting details for task {task_name}: {detail_error}")
            else:
                command_match = re.search(
                    "Tarea que se ejecutar\xa0:\\s*([^\\r\\n]+)", detail_output
                )
                command = (
                    command_match.group(1).strip()
                    if command_match
                    else "Unknown Command"
                )
                next_run_time_match = re.search(
                    "Hora pr¢xima ejecuci¢n:\\s*([^\\r\\n]+)", detail_output
                )
                next_run_time = (
                    next_run_time_match.group(1).strip()
                    if next_run_time_match
                    else "Unknown Next Run Time"
                )
                task_name = task_name.split("\\")[1]
                detailed_task_info.append(
                    f'"{task_name}": ({command}) - {next_run_time}'
                )
    """for task in detailed_task_info:
        print(task)
        print('-' * 80)  # Separator for readability"""
    return detailed_task_info


def change_task(name, program=None, start_time=None):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Changes properties of an existing scheduled task.

        Parameters:
        name (str): The name of the task to change.
        program (str, optional): The new program path for the task.
        start_time (str, optional): The new start time for the task.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    command = [windows_tasks_file_path, "/Change", "/TN", name]
    if program:
        command.extend(["/TR", program])
    if start_time:
        command.extend(["/ST", start_time])
    subprocess.run(command, check=True)


def run_task(name):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Runs a scheduled task on demand.

        Parameters:
        name (str): The name of the task to run.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    command = [windows_tasks_file_path, "/Run", "/TN", name]
    subprocess.run(command, check=True)


def end_task(name):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Ends a currently running scheduled task.

        Parameters:
        name (str): The name of the task to end.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    command = [windows_tasks_file_path, "/End", "/TN", name]
    subprocess.run(command, check=True)


def showsid_task(name):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Displays the security identifier (SID) for a scheduled task.

        Parameters:
        name (str): The name of the task.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    command = [windows_tasks_file_path, "/ShowSid", "/TN", name]
    subprocess.run(command, check=True)


def create_task(name, start_time, schedule_type=None, interval=None, program=None):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Creates a new scheduled task.

        Parameters:
        name (str): The name of the new task.
        start_time (str): The start time for the task.
        schedule_type (str, optional): The type of schedule (e.g., daily, weekly).
        interval (str, optional): The interval for the task repetition.
        program (str, optional): The program path to execute.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    command = [windows_tasks_file_path, "/Create", "/TN", name, "/ST", start_time]
    if interval:
        command.extend(["/MO", interval])
    if program:
        command.extend(["/TR", program])
    if schedule_type:
        command.extend(["/SC", schedule_type])
    subprocess.run(command, check=True)


def create_self_deleting_task(name, start_time, program):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Creates a task that deletes itself after execution.

        Parameters:
        name (str): The name of the task.
        start_time (str): The start time for the task.
        program (str): The program path to execute.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    program_path = f'"{program}"' if " " in program else program
    delete_command = f' && {windows_tasks_file_path} /Delete /TN "{name}" /f'
    full_command = f"{windows_cmd_file_path} /c start /b {program_path}{delete_command}"
    command = [
        windows_tasks_file_path,
        "/Create",
        "/TN",
        name,
        "/ST",
        start_time,
        "/TR",
        full_command,
        "/SC",
        "ONCE",
    ]
    try:
        subprocess.run(command, check=True)
        print(f"Self-deleting task '{name}' created successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error creating self-deleting task: {e}")


def at_function(name, start_time, program):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Creates a task using 'at' command with a self-deleting feature.

        Parameters:
        name (str): The name of the task.
        start_time (str): The start time for the task in HH:MM format.
        program (str): The program path to execute.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    formatted_start_time = format_time_input(start_time)
    current_time = datetime.datetime.now().time()
    if formatted_start_time < current_time:
        print("Error: The specified time is earlier than the current time.")
        return
    formatted_start_time_str = formatted_start_time.strftime("%H:%M:%S")
    create_self_deleting_task(name, formatted_start_time_str, program)


def crontab_function(task_name, minute, hour, day, month, day_of_week, script_path):
    """ ""\"
    ""\"
    ""\"
    ""\"
    Creates a scheduled task using crontab-like syntax.

        Parameters:
        task_name (str): The name of the task.
        minute (str): Minute part of the schedule.
        hour (str): Hour part of the schedule.
        day (str): Day part of the schedule.
        month (str): Month part of the schedule.
        day_of_week (str): Day of the week part of the schedule.
        script_path (str): The script path to execute.

        Returns:
        bool: True if the task was created successfully, False otherwise.
    ""\"
    ""\"
    ""\"
    ""\" """
    script_path = f'"{script_path}"' if " " in script_path else script_path
    if day_of_week != "*":
        schedule_type = "/SC WEEKLY"
        day_argument = f"/D {day_of_week.upper()}"
    elif day != "*":
        schedule_type = "/SC MONTHLY"
        day_argument = f"/D {day}"
    elif month != "*":
        schedule_type = "/SC MONTHLY"
        day_argument = ""
    else:
        schedule_type = "/SC DAILY"
        day_argument = ""
    month_argument = f"/M {month.upper()}" if month != "*" else ""
    start_time = f"{hour}:{minute}" if hour != "*" and minute != "*" else "00:00"
    full_command = f'{windows_tasks_file_path} /Create /TN "{task_name}" /TR {script_path} {schedule_type} {day_argument} {month_argument} /ST {start_time} /F'
    try:
        subprocess.run(full_command, check=True, shell=True)
        print("Scheduled task created successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating scheduled task: {e}")
        return False


def main():
    """ ""\"
    ""\"
    ""\"
    ""\"
    Main function to process command line arguments and execute corresponding task scheduler functions.

        Returns:
        None
    ""\"
    ""\"
    ""\"
    ""\" """
    args = process_parse_args()
    if args.command == "create":
        create_task(
            args.name, args.start_time, args.schedule_type, args.interval, args.program
        )
    elif args.command == "delete":
        delete_task(args.name)
    elif args.command == "list":
        list_tasks()
    elif args.command == "change":
        change_task(args.name, args.program, args.start_time)
    elif args.command == "run":
        run_task(args.name)
    elif args.command == "end":
        end_task(args.name)
    elif args.command == "showsid":
        showsid_task(args.name)
    elif args.command == "at":
        at_function(args.name, args.start_time, args.program)
    elif args.command == "crontab":
        crontab_function(
            args.name,
            args.minute,
            args.hour,
            args.day,
            args.month,
            args.day_of_week,
            args.script_path,
        )


if __name__ == "__main__":
    main()
