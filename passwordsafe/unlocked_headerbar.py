# SPDX-License-Identifier: GPL-3.0-only
from __future__ import annotations

import os
import typing
from enum import IntEnum
from typing import Optional

from gi.repository import GObject, Gtk, Handy

from passwordsafe.selection_ui import SelectionUI
if typing.TYPE_CHECKING:
    from passwordsafe.main_window import MainWindow
    from passwordsafe.unlocked_database import UnlockedDatabase


class UnlockedHeaderBar(Handy.HeaderBar):

    __gtype_name__ = "UnlockedHeaderBar"

    class Mode(IntEnum):
        GROUP = 0
        GROUP_EDIT = 1
        ENTRY = 2
        SELECTION = 3

    def __new__(cls, unlocked_database):
        builder = Gtk.Builder()
        builder.add_from_resource(
            "/org/gnome/PasswordSafe/unlocked_headerbar.ui")

        new_object = builder.get_object("headerbar")
        new_object.finish_initializing(builder, unlocked_database)
        return new_object

    def finish_initializing(self, builder, unlocked_database):
        self.builder = builder
        self._unlocked_database = unlocked_database
        self._action_bar = unlocked_database.action_bar
        self._db_manager = unlocked_database.database_manager
        self._pathbar = unlocked_database.pathbar
        self._window = unlocked_database.window

        self._headerbar_box = self.builder.get_object("headerbar_box")

        self._headerbar_right_box = self.builder.get_object("headerbar_right_box")
        self._selection_ui = SelectionUI(self._unlocked_database)
        self._headerbar_right_box.add(self._selection_ui)

        self._search_button = self.builder.get_object("search_button")
        self._search_button.connect("clicked", self._on_search_button_clicked)
        self._unlocked_database.bind_accelerator(self._search_button, "<Control>f")

        self._selection_button = self.builder.get_object("selection_button")
        self._selection_button.connect(
            "clicked", self._on_selection_button_clicked)

        self._selection_button_mobile = builder.get_object("selection_button_mobile")
        self._selection_button_mobile.connect(
            "clicked", self._on_selection_button_clicked)

        self._selection_options_button = self.builder.get_object(
            "selection_options_button")
        self._unlocked_database.bind_property(
            "selection-mode", self._selection_options_button, "visible",
            GObject.BindingFlags.SYNC_CREATE)

        self._secondary_menu_button = self.builder.get_object("secondary_menu_button")
        self._entry_menu = self.builder.get_object("entry_menu")
        self._group_menu = self.builder.get_object("group_menu")
        self._linkedbox_right = self.builder.get_object("linkedbox_right")

        self._title_label = self.builder.get_object("title_label")
        self._window.connect(
            "notify::mobile-width", self._on_mobile_width_changed)

        self._unlocked_database.bind_property(
            "selection-mode", self, "show-close-button",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.INVERT_BOOLEAN)

        self._pathbar_button_selection_revealer = self.builder.get_object(
            "pathbar_button_selection_revealer")
        self._selection_button_revealer = self.builder.get_object(
            "selection_button_revealer")

        self._mode: int = UnlockedHeaderBar.Mode.GROUP
        self.props.mode: int = UnlockedHeaderBar.Mode.GROUP
        self._unlocked_database.connect(
            "notify::selection-mode", self._on_selection_mode_changed)
        self._unlocked_database.connect(
            "notify::search-active", self._on_search_active)

        self._on_mobile_width_changed(None, None)

    def _on_search_button_clicked(self, _btn: Gtk.Button) -> None:
        self._unlocked_database.props.search_active = True

    def _on_search_active(
            self, _unlocked_database: UnlockedDatabase,
            _value: GObject.ParamSpecBoolean) -> None:
        self._update_action_bar()

    def _on_selection_button_clicked(self, _button: Gtk.Button) -> None:
        self._unlocked_database.props.selection_mode = True

    def _on_selection_mode_changed(
            self, _unlocked_database: UnlockedDatabase,
            _value: GObject.ParamSpecInt) -> None:
        style_context = self.get_style_context()
        if self._unlocked_database.props.selection_mode:
            style_context.add_class("selection-mode")
            self.props.mode = UnlockedHeaderBar.Mode.SELECTION
        else:
            style_context.remove_class("selection-mode")

    def _on_mobile_width_changed(
            self, _klass: Optional[MainWindow],
            _value: GObject.ParamSpecBoolean) -> None:
        self._update_title()
        self._update_selection_buttons()
        self._update_action_bar()

    def _update_title(self):
        is_mobile = self._window.props.mobile_width
        scrolled_page = self._unlocked_database.get_current_page()
        cur_elt = self._unlocked_database.current_element

        if is_mobile and not self._unlocked_database.props.selection_mode:
            if not scrolled_page or not scrolled_page.edit_page:
                # No edit page, show safe filename
                title = os.path.basename(self._db_manager.database_path)
            elif self._db_manager.check_is_group_object(cur_elt):
                # on group edit page, show entry title
                title = cur_elt.name or ""
            else:
                # on entry edit page, show entry title
                title = cur_elt.title or ""

            self._title_label.props.label = title

        show = is_mobile and not self._unlocked_database.props.selection_mode
        self._title_label.props.visible = show

    def _update_selection_buttons(self):
        """Update the visibility of the headerbar buttons."""
        scrolled_page = self._unlocked_database.get_current_page()
        if ((scrolled_page and scrolled_page.edit_page)
                or self._unlocked_database.props.selection_mode):
            self._pathbar_button_selection_revealer.props.reveal_child = False
            self._selection_button_revealer.props.reveal_child = False
            return

        is_mobile = self._window.props.mobile_width
        self._pathbar_button_selection_revealer.props.reveal_child = is_mobile
        self._selection_button_revealer.props.reveal_child = not is_mobile

    def _update_action_bar(self):
        """Move pathbar between top headerbar and bottom actionbar if needed"""
        page = self._unlocked_database.get_current_page()
        is_mobile = self._window.props.mobile_width

        if page is None:
            # Initial placement of pathbar before content appeared
            if is_mobile and not self._action_bar.get_children():
                # mobile mode
                self._action_bar.add(self._pathbar)
                self._action_bar.show()
                self._unlocked_database.revealer.props.reveal_child = True
            elif not is_mobile:
                # desktop mode
                self._headerbar_box.add(self._pathbar)

            return

        if self._unlocked_database.props.search_active:
            # No pathbar in search mode
            self._unlocked_database.revealer.props.reveal_child = False
            return

        if is_mobile and not self._action_bar.get_children():
            # mobile width: hide pathbar in header
            self._headerbar_box.remove(self._pathbar)
            # and put it in the bottom Action bar instead
            self._action_bar.add(self._pathbar)
            self._action_bar.show()
        elif not is_mobile and self._action_bar.get_children():
            # Desktop width and pathbar is in actionbar
            self._action_bar.remove(self._pathbar)
            self._headerbar_box.add(self._pathbar)

        self._unlocked_database.revealer.props.reveal_child = is_mobile

    @property
    def selection_ui(self) -> SelectionUI:
        """SelectionUI getter

        :returns: selection box
        :rtype: SelectionUI
        """
        return self._selection_ui

    @GObject.Property(type=int, default=0, flags=GObject.ParamFlags.READWRITE)
    def mode(self) -> int:
        """Get headerbar mode

        :returns: headerbar mode
        :rtype: int
        """
        return self._mode

    @mode.setter  # type: ignore
    def mode(self, new_mode: int) -> None:
        """Set headerbar mode

        :param int new_mode: new headerbar mode
        """
        self._mode = new_mode

        if new_mode == UnlockedHeaderBar.Mode.GROUP:
            self._secondary_menu_button.props.visible = False
            selection_mode = self._unlocked_database.props.selection_mode
            self._linkedbox_right.props.visible = not selection_mode
        elif new_mode == UnlockedHeaderBar.Mode.GROUP_EDIT:
            self._secondary_menu_button.props.menu_model = self._group_menu
            self._secondary_menu_button.props.visible = True
            self._linkedbox_right.props.visible = False
        elif new_mode == UnlockedHeaderBar.Mode.ENTRY:
            self._secondary_menu_button.props.menu_model = self._entry_menu
            self._secondary_menu_button.props.visible = True
            self._linkedbox_right.props.visible = False
        else:
            self._secondary_menu_button.props.visible = False
            self._linkedbox_right.props.visible = False

        self._update_title()
        self._update_selection_buttons()
