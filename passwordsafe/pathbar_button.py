"""Gtk.Button representing a path element in the pathbar"""
from uuid import UUID
from gi.repository import Gtk


class PathbarButton(Gtk.Button):
    """Gtk.Button representing a path element in the pathbar

    notable instance variables are:
    .uuid: the UUID of the group or entry
    """
    is_group = NotImplemented

    def __init__(self, uuid: UUID):
        Gtk.Button.__init__(self)
        self.set_name("PathbarButtonDynamic")
        self.uuid: UUID = uuid

    def set_is_group(self):
        self.is_group = True

    def set_is_entry(self):
        self.is_group = False

    def get_is_group(self) -> bool:
        return self.is_group
