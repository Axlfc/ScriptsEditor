import os
import json
import re
from tkinter import Toplevel, Frame, Button, LEFT, RIGHT, Y, X, N, S, W, E, BOTH, Label, Entry, END, Checkbutton, \
    scrolledtext, LabelFrame, messagebox, StringVar, Menu, simpledialog, INSERT
from tkinter.ttk import Treeview

# Add these constants at the top of the file
ALIAS_PATTERN = r'^[a-z][a-z0-9_]*[a-z0-9]$'
ALIAS_MIN_LENGTH = 3
ALIAS_MAX_LENGTH = 50

DEFAULT_CATEGORY_FILE = "data/prompt_categories.json"  # File for default categories


def generate_prompt_alias(self, title):
    """Generate a valid prompt alias from the title."""
    # Remove all characters except letters, numbers, and spaces
    cleaned = ''.join(char.lower() for char in title if char.isalnum() or char.isspace())
    # Replace spaces with underscores and remove leading/trailing underscores
    alias = cleaned.replace(' ', '_').strip('_')
    # Ensure it starts with a letter
    if alias and not alias[0].isalpha():
        alias = 'p_' + alias
    # Ensure minimum length
    if len(alias) < ALIAS_MIN_LENGTH:
        alias = alias + '_prompt'
    # Truncate if too long
    if len(alias) > ALIAS_MAX_LENGTH:
        alias = alias[:ALIAS_MAX_LENGTH].rstrip('_')
    return alias


class VariableEditDialog(Toplevel):
    def __init__(self, parent, variable=None):
        super().__init__(parent)
        self.title("Edit Variable")
        # Ensure `variable` is a dictionary, even if None is passed
        self.variable = variable or {}
        self.result = None

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Create and pack the form
        form = Frame(self)
        form.pack(padx=10, pady=5, fill=BOTH, expand=True)

        # Name field
        Label(form, text="Name:").grid(row=0, column=0, sticky=W, pady=2)
        self.name_var = StringVar(value=self.variable.get("name", ""))
        self.name_entry = Entry(form, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, sticky=W + E, pady=2)

        # Description field
        Label(form, text="Description:").grid(row=1, column=0, sticky=W, pady=2)
        self.desc_var = StringVar(value=self.variable.get("description", ""))
        self.desc_entry = Entry(form, textvariable=self.desc_var)
        self.desc_entry.grid(row=1, column=1, sticky=W + E, pady=2)

        # Type field
        Label(form, text="Type:").grid(row=2, column=0, sticky=W, pady=2)
        self.type_var = StringVar(value=self.variable.get("type", "text"))
        self.type_entry = Entry(form, textvariable=self.type_var)
        self.type_entry.grid(row=2, column=1, sticky=W + E, pady=2)

        # Default value field
        Label(form, text="Default Value:").grid(row=3, column=0, sticky=W, pady=2)
        self.default_var = StringVar(value=self.variable.get("default", ""))
        self.default_entry = Entry(form, textvariable=self.default_var)
        self.default_entry.grid(row=3, column=1, sticky=W + E, pady=2)

        # Buttons
        button_frame = Frame(form)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        Button(button_frame, text="OK", command=self.ok).pack(side=LEFT, padx=5)
        Button(button_frame, text="Cancel", command=self.cancel).pack(side=LEFT, padx=5)

        # Center the dialog
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))

        self.wait_window(self)

    def ok(self):
        self.result = {
            "name": self.name_var.get(),
            "description": self.desc_var.get(),
            "type": self.type_var.get(),
            "default": self.default_var.get()
        }
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()


class PromptEnhancementWindow:
    def __init__(self):
        """Initialize the Prompt Enhancement Studio window."""
        self.enhancement_window = Toplevel()
        self.enhancement_window.title("Prompt Enhancement Studio")
        self.enhancement_window.geometry("1200x800")

        # Initialize data storage
        self.prompt_data = {}
        self.categories = {}
        self.default_categories = self.load_default_categories()
        self.variables = []
        self.prompt_folder = "data/prompts"

        # Ensure prompt directory exists
        os.makedirs(self.prompt_folder, exist_ok=True)

        # Setup UI
        self.setup_ui()

        # Load saved categories and prompts
        self.load_saved_categories()

        self.alias_valid = False
        self.alias_error = None

        self.title_entry.bind('<KeyRelease>', self.update_alias)

    def load_default_categories(self):
        """Load default categories from a file."""
        if os.path.exists(DEFAULT_CATEGORY_FILE):
            with open(DEFAULT_CATEGORY_FILE, "r") as f:
                return json.load(f)
        else:
            return {}

    def create_context_menus(self):
        """Create context menus for the category tree."""
        self.category_menu = Menu(self.enhancement_window, tearoff=0)
        self.category_menu.add_command(label="New Category", command=self.new_category)
        self.category_menu.add_command(label="Rename Category", command=self.rename_category)
        self.category_menu.add_command(label="Delete Category", command=self.delete_category)

        self.prompt_menu = Menu(self.enhancement_window, tearoff=0)
        self.prompt_menu.add_command(label="Rename Prompt", command=self.rename_prompt)
        self.prompt_menu.add_command(label="Delete Prompt", command=self.delete_prompt)

        self.category_tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """Show the appropriate context menu based on the selected item."""
        item = self.category_tree.identify_row(event.y)
        if item:
            self.category_tree.selection_set(item)
            item_type = self.category_tree.item(item, "values")
            if item_type and item_type[0] == "category":
                self.category_menu.post(event.x_root, event.y_root)
            elif item_type and item_type[0] == "prompt":
                self.prompt_menu.post(event.x_root, event.y_root)

    def new_category(self):
        """Add a new category."""
        name = simpledialog.askstring("New Category", "Enter category name:")
        if name and name.strip():
            if name not in self.categories:
                self.categories[name] = {"description": "", "subcategories": {}}
                self.category_tree.insert('', 'end', text=name, values=("category",))
                self.save_categories()
            else:
                messagebox.showerror("Error", "Category already exists!")

    def rename_category(self):
        """Rename selected category."""
        selected = self.category_tree.selection()
        if not selected:
            return

        item = selected[0]
        if self.category_tree.item(item)["values"][0] != "category":
            return

        old_name = self.category_tree.item(item)["text"]
        new_name = messagebox.askstring("Rename Category", "Enter new name:", initialvalue=old_name)

        if new_name and new_name.strip() and new_name != old_name:
            if new_name not in self.categories:
                self.categories[new_name] = self.categories.pop(old_name)
                self.category_tree.item(item, text=new_name)
                self.save_categories()
            else:
                messagebox.showerror("Error", "Category already exists!")

    def delete_category(self):
        """Delete selected category and all its prompts."""
        selected = self.category_tree.selection()
        if not selected:
            return

        item = selected[0]
        if self.category_tree.item(item)["values"][0] != "category":
            return

        category = self.category_tree.item(item)["text"]
        if messagebox.askyesno("Confirm Delete", f"Delete category '{category}' and all its prompts?"):
            # Delete prompt files
            for prompt in self.categories[category]:
                try:
                    os.remove(os.path.join(self.prompt_folder, f"{prompt}.json"))
                except OSError:
                    pass

            # Delete category
            del self.categories[category]
            self.category_tree.delete(item)
            self.save_categories()

    def rename_prompt(self):
        """Rename selected prompt."""
        selected = self.category_tree.selection()
        if not selected:
            return

        item = selected[0]
        if self.category_tree.item(item)["values"][0] != "prompt":
            return

        old_name = self.category_tree.item(item)["text"]
        new_name = messagebox.askstring("Rename Prompt", "Enter new name:", initialvalue=old_name)

        if new_name and new_name.strip() and new_name != old_name:
            # Update prompt file
            old_file = os.path.join(self.prompt_folder, f"{old_name}.json")
            new_file = os.path.join(self.prompt_folder, f"{new_name}.json")

            try:
                with open(old_file, 'r') as f:
                    prompt_data = json.load(f)

                prompt_data['title'] = new_name

                with open(new_file, 'w') as f:
                    json.dump(prompt_data, f, indent=4)

                os.remove(old_file)

                # Update category listing
                category = self.category_tree.item(self.category_tree.parent(item))["text"]
                self.categories[category].remove(old_name)
                self.categories[category].append(new_name)

                self.category_tree.item(item, text=new_name)
                self.save_categories()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to rename prompt: {str(e)}")

    def delete_prompt(self):
        """Delete selected prompt."""
        selected = self.category_tree.selection()
        if not selected:
            return

        item = selected[0]
        if self.category_tree.item(item)["values"][0] != "prompt":
            return

        prompt = self.category_tree.item(item)["text"]
        if messagebox.askyesno("Confirm Delete", f"Delete prompt '{prompt}'?"):
            try:
                os.remove(os.path.join(self.prompt_folder, f"{prompt}.json"))
                category = self.category_tree.item(self.category_tree.parent(item))["text"]
                self.categories[category].remove(prompt)
                self.category_tree.delete(item)
                self.save_categories()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete prompt: {str(e)}")

    def search_prompt(self):
        """Search for a category or prompt in the tree."""
        query = simpledialog.askstring("Search", "Enter search term:")
        if not query:
            return

        query = query.lower()
        results = []

        # Recursive function to search through the tree
        def search_tree(item, path=""):
            text = self.category_tree.item(item, "text").lower()
            if query in text:
                results.append((item, path + text))
            for child in self.category_tree.get_children(item):
                search_tree(child, path + text + " > ")

        # Start searching from the root items
        for top_level_item in self.category_tree.get_children():
            search_tree(top_level_item)

        # Display results
        if results:
            result_text = "\n".join(f"{path}" for _, path in results)
            messagebox.showinfo("Search Results", f"Found the following matches:\n\n{result_text}")
            # Highlight the first result in the tree
            self.category_tree.selection_set(results[0][0])
            self.category_tree.focus(results[0][0])
        else:
            messagebox.showinfo("Search Results", "No matches found.")

    def setup_ui(self):
        """Setup the UI layout."""
        main_frame = Frame(self.enhancement_window)
        main_frame.grid(row=0, column=0, sticky=(N, W, E, S))
        self.enhancement_window.columnconfigure(0, weight=1)
        self.enhancement_window.rowconfigure(0, weight=1)

        # Toolbar
        toolbar = Frame(main_frame)
        toolbar.grid(row=0, column=0, columnspan=2, sticky=(W, E))
        Button(toolbar, text="New", command=self.new_prompt).pack(side=LEFT, padx=2)
        Button(toolbar, text="Save", command=self.save_prompt).pack(side=LEFT, padx=2)
        Button(toolbar, text="Load", command=self.load_prompt).pack(side=LEFT, padx=2)
        Button(toolbar, text="Export", command=self.export_prompt).pack(side=LEFT, padx=2)
        Button(toolbar, text="Search", command=self.search_prompt).pack(side=LEFT, padx=2)
        Button(toolbar, text="Help").pack(side=RIGHT, padx=2)

        # Sidebar for categories and templates
        sidebar = Frame(main_frame, width=300)
        sidebar.grid(row=1, column=0, sticky=(N, S, W, E), padx=5, pady=5)

        # Category tree
        self.category_tree = Treeview(sidebar, height=20)
        self.category_tree.heading('#0', text='Categories')
        self.category_tree.pack(fill=Y, expand=True)
        self.category_tree.bind('<<TreeviewSelect>>', self.on_treeview_select)

        # Right-click context menus
        self.create_context_menus()

        # Main prompt editing area
        editor_frame = Frame(main_frame)
        editor_frame.grid(row=1, column=1, sticky=(N, S, W, E), pady=5)

        # Title and alias frame
        title_frame = Frame(editor_frame)
        title_frame.pack(fill=X, pady=5)

        # Title subframe
        title_subframe = Frame(title_frame)
        title_subframe.pack(fill=X, expand=True)
        Label(title_subframe, text="Title:").pack(side=LEFT)
        self.title_entry = Entry(title_subframe)
        self.title_entry.pack(side=LEFT, fill=X, expand=True, padx=5)

        # Alias subframe with validation feedback
        alias_subframe = Frame(title_frame)
        alias_subframe.pack(fill=X, expand=True, pady=(5, 0))
        Label(alias_subframe, text="Alias:").pack(side=LEFT)
        self.alias_entry = Entry(alias_subframe)
        self.alias_entry.pack(side=LEFT, fill=X, expand=True, padx=5)
        self.alias_status_label = Label(alias_subframe, text="", fg="black")
        self.alias_status_label.pack(side=LEFT, padx=5)

        # Add binding for alias changes
        self.alias_entry.bind('<KeyRelease>', self.on_alias_change)
        self.alias_entry.bind('<FocusOut>', self.validate_alias)

        category_frame = Frame(editor_frame)
        category_frame.pack(fill=X, pady=5)
        Label(category_frame, text="Category:").pack(side=LEFT)
        self.category_entry = Entry(category_frame)
        self.category_entry.pack(side=LEFT, fill=X, expand=True, padx=5)

        # Main prompt content
        self.prompt_text = scrolledtext.ScrolledText(editor_frame, height=15)
        self.prompt_text.pack(fill=BOTH, expand=True, pady=5)

        # Variable management
        var_frame = LabelFrame(editor_frame, text="Variables")
        var_frame.pack(fill=X, pady=5)

        self.var_tree = Treeview(var_frame, columns=("name", "description", "type", "default"), height=5,
                                 show="headings")
        self.var_tree.heading("name", text="Name")
        self.var_tree.heading("description", text="Description")
        self.var_tree.heading("type", text="Type")
        self.var_tree.heading("default", text="Default Value")
        self.var_tree.pack(fill=X, pady=5)

        var_button_frame = Frame(var_frame)
        var_button_frame.pack(fill=X, pady=5)
        Button(var_button_frame, text="Add Variable", command=self.add_variable).pack(side=LEFT, padx=5)
        Button(var_button_frame, text="Edit Variable", command=self.edit_variable).pack(side=LEFT, padx=5)
        Button(var_button_frame, text="Delete Variable", command=self.delete_variable).pack(side=LEFT, padx=5)

        # Enhancement options
        options_frame = LabelFrame(editor_frame, text="Enhancement Options")
        options_frame.pack(fill=X, pady=5)
        Checkbutton(options_frame, text="Add context retention").pack(anchor=W)
        Checkbutton(options_frame, text="Include conversation history").pack(anchor=W)
        Checkbutton(options_frame, text="Auto-format response").pack(anchor=W)

        # Bottom action buttons
        button_frame = Frame(editor_frame)
        button_frame.pack(fill=X, pady=5)
        Button(button_frame, text="Test Prompt", command=self.test_prompt).pack(side=LEFT, padx=5)
        Button(button_frame, text="Save Version", command=self.save_prompt).pack(side=LEFT, padx=5)
        Button(button_frame, text="Export", command=self.export_prompt).pack(side=LEFT, padx=5)

    def validate_alias(self, event=None):
        """Validate the alias when focus leaves the entry field."""
        alias = self.alias_entry.get().strip()
        validation_result = self.check_alias_validity(alias)

        if not validation_result['valid']:
            self.alias_status_label.config(text=validation_result['error'], fg="red")
            self.alias_valid = False
            self.alias_error = validation_result['error']
        else:
            self.alias_status_label.config(text="✓", fg="green")
            self.alias_valid = True
            self.alias_error = None

        return self.alias_valid

    def on_alias_change(self, event=None):
        """Handle changes to the alias field in real-time."""
        alias = self.alias_entry.get().strip()
        validation_result = self.check_alias_validity(alias, check_exists=True)

        if not validation_result['valid']:
            self.alias_status_label.config(text="⚠ " + validation_result['error'], fg="orange")
            self.alias_valid = False
            self.alias_error = validation_result['error']
        else:
            self.alias_status_label.config(text="✓", fg="green")
            self.alias_valid = True
            self.alias_error = None

    def check_alias_validity(self, alias, check_exists=True):
        """Check if an alias is valid according to all rules."""
        if not alias:
            return {'valid': False, 'error': "Alias cannot be empty"}

        if len(alias) < ALIAS_MIN_LENGTH:
            return {'valid': False, 'error': f"Min {ALIAS_MIN_LENGTH} chars"}

        if len(alias) > ALIAS_MAX_LENGTH:
            return {'valid': False, 'error': f"Max {ALIAS_MAX_LENGTH} chars"}

        if not re.match(ALIAS_PATTERN, alias):
            return {'valid': False, 'error': "Invalid format"}

        if check_exists and self.check_alias_exists(alias, self.title_entry.get().strip()):
            return {'valid': False, 'error': "Already exists"}

        return {'valid': True, 'error': None}

    def generate_prompt_alias(self, title):
        """Generate a valid prompt alias from the title."""
        # Remove all characters except letters, numbers, and spaces
        cleaned = ''.join(char.lower() for char in title if char.isalnum() or char.isspace())
        # Replace spaces with underscores and remove leading/trailing underscores
        alias = cleaned.replace(' ', '_').strip('_')
        # Ensure it starts with a letter
        if alias and not alias[0].isalpha():
            alias = 'p_' + alias
        # Ensure minimum length
        if len(alias) < ALIAS_MIN_LENGTH:
            alias = alias + '_prompt'
        # Truncate if too long
        if len(alias) > ALIAS_MAX_LENGTH:
            alias = alias[:ALIAS_MAX_LENGTH].rstrip('_')
        return alias

    def update_alias(self, event=None):
        """Update the alias field based on the title in real-time."""
        title = self.title_entry.get().strip()
        if title:
            alias = self.generate_prompt_alias(title)
            current_cursor = self.alias_entry.index(INSERT)  # Save cursor position
            self.alias_entry.delete(0, END)
            self.alias_entry.insert(0, alias)
            self.alias_entry.icursor(current_cursor)  # Restore cursor position
            # Trigger validation
            self.on_alias_change()

    def check_alias_exists(self, alias, current_title=None):
        """Check if an alias already exists in any prompt file.
        Returns True if the alias exists in another prompt, False otherwise."""
        for filename in os.listdir(self.prompt_folder):
            if filename.endswith('.json') and filename != "categories.json":
                try:
                    with open(os.path.join(self.prompt_folder, filename), 'r') as f:
                        prompt_data = json.load(f)
                        if prompt_data.get('alias') == alias and prompt_data.get('title') != current_title:
                            return True
                except Exception:
                    continue
        return False

    def on_treeview_select(self, event):
        """Handle selection in the category tree."""
        try:
            selected_items = self.category_tree.selection()
            if not selected_items:
                return

            selected_item = selected_items[0]  # Get the first selected item
            item_text = self.category_tree.item(selected_item, 'text')
            item_type = self.category_tree.item(selected_item, 'values')

            # Only load prompts, not categories
            if item_type and item_type[0] == "prompt":
                # Prevent recursive loading by unbinding the event temporarily
                self.category_tree.unbind('<<TreeviewSelect>>')

                # Load the prompt
                self.load_prompt_by_title(item_text)

                # Rebind the event after a short delay
                self.enhancement_window.after(100,
                                              lambda: self.category_tree.bind('<<TreeviewSelect>>',
                                                                              self.on_treeview_select))
        except Exception as e:
            messagebox.showerror("Error", f"Error selecting item: {str(e)}")

    def save_categories(self):
        """Save categories and associated prompts."""
        with open(os.path.join(self.prompt_folder, "categories.json"), "w") as f:
            json.dump(self.categories, f, indent=4)

    def load_saved_categories(self):
        """Load categories and prompts from the categories file."""
        categories_file = os.path.join(self.prompt_folder, "categories.json")

        # If no custom categories file exists, use the default
        if os.path.exists(categories_file):
            with open(categories_file, "r") as f:
                self.categories = json.load(f)
        else:
            self.categories = self.default_categories

        # Populate treeview with existing categories and prompts
        self.populate_treeview()

    def sync_prompts_with_categories(self):
        """Sync prompt files with categories and update the treeview."""
        for filename in os.listdir(self.prompt_folder):
            if filename.endswith('.json') and filename != "categories.json":
                prompt_path = os.path.join(self.prompt_folder, filename)
                try:
                    with open(prompt_path, 'r') as f:
                        prompt_data = json.load(f)

                    title = prompt_data.get('title')
                    category = prompt_data.get('category')

                    if title and category:
                        # Ensure category exists and has the correct structure
                        if category not in self.categories or not isinstance(self.categories[category], dict):
                            self.categories[category] = {"prompts": []}

                        # Add prompt to category if not already present
                        if title not in self.categories[category]["prompts"]:
                            self.categories[category]["prompts"].append(title)

                except Exception as e:
                    print(f"Error loading prompt file {filename}: {str(e)}")

        # Save updated categories and refresh the treeview
        self.save_categories()
        self.populate_treeview()

    def populate_treeview(self):
        """Populate the treeview with categories, subcategories, and prompts."""
        self.category_tree.delete(*self.category_tree.get_children())  # Clear existing entries

        def add_subcategories(parent, data):
            if isinstance(data, dict):
                for subcat_name, subcat_data in data.items():
                    subcat_id = self.category_tree.insert(parent, 'end', text=subcat_name, values=("category",))
                    # If it's a dictionary with prompts
                    if isinstance(subcat_data, dict) and "prompts" in subcat_data:
                        for prompt in subcat_data["prompts"]:
                            self.category_tree.insert(subcat_id, 'end', text=prompt, values=("prompt",))
                        # Handle nested subcategories if they exist
                        if "subcategories" in subcat_data:
                            add_subcategories(subcat_id, subcat_data["subcategories"])
                    # If it's just a list of prompts
                    elif isinstance(subcat_data, list):
                        for prompt in subcat_data:
                            self.category_tree.insert(subcat_id, 'end', text=prompt, values=("prompt",))

        # Process each top-level category
        for category, data in self.categories.items():
            # Add category to tree
            category_id = self.category_tree.insert('', 'end', text=category, values=("category",))

            # Handle category data
            if isinstance(data, dict):
                # Add prompts if they exist at the category level
                if "prompts" in data:
                    for prompt in data["prompts"]:
                        self.category_tree.insert(category_id, 'end', text=prompt, values=("prompt",))

                # Add subcategories if they exist
                if "subcategories" in data:
                    add_subcategories(category_id, data["subcategories"])
            elif isinstance(data, list):
                # If data is just a list of prompts
                for prompt in data:
                    self.category_tree.insert(category_id, 'end', text=prompt, values=("prompt",))
    def load_variables_into_tree(self):
        """Load all variables into the Treeview."""
        self.var_tree.delete(*self.var_tree.get_children())
        for var in self.variables:
            self.var_tree.insert("", "end", values=(var["name"], var["description"], var["type"], var.get("default", "")))

    def add_variable(self):
        """Add a new variable using the edit dialog."""
        dialog = VariableEditDialog(self.enhancement_window)
        if dialog.result:
            self.variables.append(dialog.result)
            self.load_variables_into_tree()

    def edit_variable(self):
        """Edit the selected variable using a dialog."""
        selected_item = self.var_tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a variable to edit.")
            return

        item_values = self.var_tree.item(selected_item[0], "values")
        var_index = next((i for i, var in enumerate(self.variables)
                          if var["name"] == item_values[0]), None)

        if var_index is not None:
            dialog = VariableEditDialog(self.enhancement_window, self.variables[var_index])
            if dialog.result:
                self.variables[var_index] = dialog.result
                self.load_variables_into_tree()

    def delete_variable(self):
        """Delete the selected variable."""
        selected_item = self.var_tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a variable to delete.")
            return

        item_values = self.var_tree.item(selected_item, "values")
        self.variables = [var for var in self.variables if var["name"] != item_values[0]]
        self.load_variables_into_tree()

    def save_prompt(self):
        """Save the current prompt template to file with validation."""
        title = self.title_entry.get().strip()
        category = self.category_entry.get().strip()
        content = self.prompt_text.get("1.0", END).strip()
        alias = self.alias_entry.get().strip()

        # Validate all required fields
        if not all([title, content, category, alias]):
            messagebox.showerror("Error", "Title, category, content, and alias cannot be empty.")
            return

        # Validate alias format
        if not self.alias_valid:
            messagebox.showerror("Error", f"Invalid alias: {self.alias_error}")
            return

        # Check for existing prompt with same title
        if os.path.exists(os.path.join(self.prompt_folder, f"{title}.json")) and \
                title != self.prompt_data.get('title'):
            messagebox.showerror("Error", f"A prompt with the title '{title}' already exists.")
            return

        try:
            self.prompt_data = {
                "title": title,
                "alias": alias,
                "category": category,
                "content": content,
                "variables": self.variables,
            }

            # Save prompt file
            prompt_filename = os.path.join(self.prompt_folder, f"{title}.json")
            with open(prompt_filename, "w") as f:
                json.dump(self.prompt_data, f, indent=4)

            self._update_categories(title, category)
            self.populate_treeview()
            self.select_prompt_in_tree(title)

            messagebox.showinfo("Success", f"Prompt '{title}' saved successfully.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save prompt: {str(e)}")

    def _update_categories(self, title, category):
        """Helper method to update categories when saving prompt."""
        if category not in self.categories or not isinstance(self.categories[category], dict):
            self.categories[category] = {"prompts": []}

        if "prompts" not in self.categories[category]:
            self.categories[category]["prompts"] = []

        if title not in self.categories[category]["prompts"]:
            self.categories[category]["prompts"].append(title)

        self.save_categories()

    def select_prompt_in_tree(self, title):
        """Select a prompt in the treeview without triggering reload."""
        def find_prompt(node):
            item_text = self.category_tree.item(node, "text")
            item_type = self.category_tree.item(node, "values")

            if item_type and item_type[0] == "prompt" and item_text == title:
                return node

            for child in self.category_tree.get_children(node):
                result = find_prompt(child)
                if result:
                    return result
            return None

        # Temporarily unbind the selection event
        self.category_tree.unbind('<<TreeviewSelect>>')

        # Search through all items
        for item in self.category_tree.get_children():
            prompt_item = find_prompt(item)
            if prompt_item:
                # Select and show the prompt
                self.category_tree.selection_set(prompt_item)
                self.category_tree.see(prompt_item)
                break

        # Rebind the selection event after a short delay
        self.enhancement_window.after(100,
            lambda: self.category_tree.bind('<<TreeviewSelect>>', self.on_treeview_select))

    def load_prompt(self):
        """Load a prompt selected from the Treeview."""
        selected_item = self.category_tree.selection()
        if selected_item:
            item_text = self.category_tree.item(selected_item, 'text')
            item_type = self.category_tree.item(selected_item, 'values')

            if item_type and item_type[0] == "prompt":
                self.load_prompt_by_title(item_text)
            else:
                messagebox.showinfo("Info", "Please select a valid prompt to load.")
        else:
            messagebox.showinfo("Info", "No prompt selected.")

    def load_prompt_by_title(self, title):
        """Load a prompt by its title."""
        if not title:
            return

        prompt_filename = os.path.join(self.prompt_folder, f"{title}.json")
        try:
            with open(prompt_filename, "r") as f:
                self.prompt_data = json.load(f)

            # Update UI elements
            self.title_entry.delete(0, END)
            self.title_entry.insert(0, self.prompt_data.get('title', ''))

            # Set alias from saved data or generate from title if not present
            alias = self.prompt_data.get('alias') or generate_prompt_alias(self.prompt_data.get('title', ''))
            self.alias_entry.delete(0, END)
            self.alias_entry.insert(0, alias)

            self.category_entry.delete(0, END)
            self.category_entry.insert(0, self.prompt_data.get('category', ''))

            self.prompt_text.delete("1.0", END)
            self.prompt_text.insert("1.0", self.prompt_data.get('content', ''))

            # Load variables
            self.variables = self.prompt_data.get("variables", [])
            self.load_variables_into_tree()

        except FileNotFoundError:
            messagebox.showerror("Error", f"No saved prompt found with the title '{title}'.")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading prompt: {str(e)}")

    def export_prompt(self):
        """Export the current prompt to a file."""
        title = self.title_entry.get().strip()
        content = self.prompt_text.get("1.0", END).strip()

        if title and content:
            export_filename = os.path.join(self.prompt_folder, f"{title}.txt")
            with open(export_filename, "w") as f:
                f.write(content)
            print(f"Prompt exported as {export_filename}")
        else:
            print("Title and content cannot be empty.")

    def test_prompt(self):
        """Test the current prompt with variables replaced."""
        content = self.prompt_text.get("1.0", END).strip()
        if content:
            for var in self.variables:
                content = content.replace(f"{{{{{var['name']}}}}}", var.get("default", ""))
            print("Processed Prompt:")
            print(content)
        else:
            print("Prompt content is empty.")

    def new_prompt(self):
        """Clear fields to create a new prompt."""
        self.title_entry.delete(0, END)
        self.alias_entry.delete(0, END)
        self.category_entry.delete(0, END)
        self.prompt_text.delete("1.0", END)
        self.variables = []
        self.var_tree.delete(*self.var_tree.get_children())
        self.prompt_data = {}
