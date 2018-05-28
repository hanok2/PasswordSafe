from gi.repository import Gtk
from keepassgtk.logging_manager import LoggingManager
from keepassgtk.pathbar import Pathbar
from keepassgtk.entry_row import EntryRow
from keepassgtk.group_row import GroupRow
import gi
gi.require_version('Gtk', '3.0')


class UnlockedDatabase:
    builder = NotImplemented
    window = NotImplemented
    parent_widget = NotImplemented
    stack = NotImplemented
    database_manager = NotImplemented
    logging_manager = LoggingManager(True)
    current_group = NotImplemented
    pathbar = NotImplemented

    def __init__(self, window, widget, dbm):
        self.window = window
        self.parent_widget = widget
        self.database_manager = dbm
        self.assemble_listbox()

    #
    # Stack Pages
    #

    def assemble_listbox(self):
        self.current_group = self.database_manager.get_root_group()

        self.builder = Gtk.Builder()
        self.builder.add_from_resource("/run/terminal/KeepassGtk/entries_listbox.ui")

        scrolled_window = self.builder.get_object("scrolled_window")
        self.parent_widget.add(scrolled_window)

        self.stack = self.builder.get_object("list_stack")

        self.set_headerbar()

        self.show_page_of_new_directory()

    #
    # Headerbar
    #

    def set_headerbar(self):
        headerbar = self.builder.get_object("headerbar")

        save_button = self.builder.get_object("save_button")
        save_button.connect("clicked", self.on_save_button_clicked)

        self.parent_widget.set_headerbar(headerbar)
        self.window.set_titlebar(headerbar)

        self.pathbar = Pathbar(self, self.database_manager, self.database_manager.get_root_group(), headerbar)

    #
    # Group and Entry Management
    #

    def show_page_of_new_directory(self):
        if self.stack.get_child_by_name(
            self.database_manager.get_group_uuid_from_group_object(
                self.current_group)) is None:
            builder = Gtk.Builder()
            builder.add_from_resource("/run/terminal/KeepassGtk/entries_listbox.ui")
            list_box = builder.get_object("list_box")
            list_box.connect("row-activated", self.on_list_box_row_activated)
            list_box.connect("row-selected", self.on_list_box_row_selected)

            self.add_stack_page(list_box)
            self.insert_groups_into_listbox(list_box)
            self.insert_entries_into_listbox(list_box)
        else:
            self.stack.set_visible_child_name(
                self.database_manager.get_group_uuid_from_group_object(
                    self.current_group))

    def add_stack_page(self, list_box):
        self.stack.add_named(
            list_box,
            self.database_manager.get_group_uuid_from_group_object(
                self.current_group))
        self.switch_stack_page()

    def switch_stack_page(self):
        self.stack.set_visible_child_name(
            self.database_manager.get_group_uuid_from_group_object(
                self.current_group))

    def set_current_group(self, group):
        self.current_group = group

    def get_current_group(self):
        return self.current_group

    #
    # Create Group & Entry Rows
    #

    def insert_groups_into_listbox(self, list_box):
        groups = NotImplemented

        if self.current_group.is_root_group:
            groups = self.database_manager.get_groups_in_root()
        else:
            groups = self.database_manager.get_groups_in_folder(self.database_manager.get_group_uuid_from_group_object(self.current_group))

        for group in groups:
            group_row = GroupRow(self.database_manager, group)
            list_box.add(group_row)

    def insert_entries_into_listbox(self, list_box):
        entries = self.database_manager.get_entries_in_folder(self.database_manager.get_group_uuid_from_group_object(self.current_group))

        for entry in entries:
            entry_row = EntryRow(self.database_manager, entry)
            list_box.add(entry_row)

    #
    # Events
    #

    def on_list_box_row_activated(self, widget, list_box_row):
        if list_box_row.get_type() == "EntryRow":
            self.logging_manager.log_info("Will show details of the entry in near future. Entry clicked: " + list_box_row.get_label())
        elif list_box_row.get_type() == "GroupRow":
            self.set_current_group(self.database_manager.get_group_object_from_uuid(list_box_row.get_group_uuid()))
            self.pathbar.add_pathbar_button_to_pathbar(list_box_row.get_group_uuid())
            self.show_page_of_new_directory()

    def on_list_box_row_selected(self, widget, list_box_row):
        self.logging_manager.log_debug(list_box_row.get_label() + " selected")

    def on_save_button_clicked(self, widget):
        self.database_manager.save()
        self.logging_manager = LoggingManager(True)
        self.logging_manager.log_debug("Database has been saved")
