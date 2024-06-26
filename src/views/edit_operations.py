from tkinter import INSERT, SEL, END
from tkinter.constants import SEL_FIRST, SEL_LAST

from src.views.tk_utils import root, text, script_text


def cut(event=None):
    """
        Cuts the selected text from the editor and places it into the clipboard.
    """
    try:
        # Check if there is selected text
        selected_text = text.get(SEL_FIRST, SEL_LAST)
        root.clipboard_clear()
        root.clipboard_append(string=selected_text)
        text.delete(SEL_FIRST, SEL_LAST)
    except Exception as e:
        # No text is selected
        pass


def copy(event=None):
    """
        Copies the selected text from the editor to the clipboard.
    """
    try:
        selected_text = text.get(SEL_FIRST, SEL_LAST)
        root.clipboard_clear()
        root.clipboard_append(string=selected_text)
    except Exception as e:
        # No text is selected
        pass


def paste(event=None):
    """
        Pastes text from the clipboard into the editor at the current cursor position.

        This function retrieves everything from the clipboard and inserts it at the current cursor position in the editor.

        Parameters:
        event (optional): An event object representing the event that triggered this function.

        Returns:
        None
    """
    # get gives everyting from the clipboard and paste it on the current cursor position
    # it does'nt removes it from the clipboard.
    text.insert(INSERT, root.clipboard_get())


def select_all(event=None):
    """
        Selects all the text within the editor.

        This function adds a 'select' tag from the beginning to the end of the text, effectively selecting all the text.

        Parameters:
        event (optional): An event object representing the event that triggered this function.

        Returns:
        None
    """
    text.tag_add(SEL, "1.0", END)


def delete_all():
    """
        Deletes all text in the editor.

        This function removes all the content in the editor, clearing the text field.

        Parameters:
        None

        Returns:
        None
    """
    text.delete(1.0, END)


def duplicate(event=None):
    """
        Duplicates the selected text in the editor.
    """
    try:
        selected_text = text.get(SEL_FIRST, SEL_LAST)
        text.insert(INSERT, selected_text)
    except Exception as e:
        # No text is selected
        pass


def undo():
    """
        Undoes the last action in the script text editor.

        This function reverts the last change made in the script text editor, typically used for undoing edits.

        Parameters:
        None

        Returns:
        None
    """
    script_text.edit_undo()


def redo():
    """
        Redoes the last undone action in the script text editor.

        If actions were previously undone using the undo function, this function allows redoing those actions.

        Parameters:
        None

        Returns:
        None
    """
    script_text.edit_redo()


def delete():
    """
        Deletes the currently selected text in the editor.

        This function removes the text that is currently selected within the editor.

        Parameters:
        None

        Returns:
        None
    """
    text.delete(index1=SEL_FIRST, index2=SEL_LAST)
