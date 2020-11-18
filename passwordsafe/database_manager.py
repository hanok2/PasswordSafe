# SPDX-License-Identifier: GPL-3.0-only
import hashlib
import logging
from datetime import datetime
from gettext import gettext as _
from typing import List, Optional, Union
from uuid import UUID
from pykeepass import PyKeePass
from pykeepass.entry import Entry
from pykeepass.group import Group
from gi.repository import Gio, GObject

import passwordsafe.config_manager
from passwordsafe.safe_entry import SafeEntry


class DatabaseManager(GObject.GObject):
    # pylint: disable=too-many-public-methods

    """Implements database functionality that is independent of the UI

    Useful attributes:
     .database_path: str containing the filepath of the database

    Group objects are of type `pykeepass.group.Group`
    Entry objects are of type `pykeepass.entry.Entry`
    Instances of both have useful attributes:
    .uuid: a `uuid.UUID` object
    """

    # self.db contains a `PyKeePass` database
    password_try = ""
    keyfile_hash = NotImplemented
    _is_dirty = False  # Does the database need saving?
    save_running = False

    locked = GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    def __init__(
        self,
        database_path: str,
        password: Optional[str] = None,
        keyfile: Optional[str] = None,
    ) -> None:
        super().__init__()

        # password remains accessible as self.db.password
        self.db = PyKeePass(database_path, password, keyfile)  # pylint: disable=C0103
        self.database_path = database_path

    #
    # Group Transformation Methods
    #

    def get_group(self, uuid: UUID) -> Optional[Group]:
        """Return the group object for a group uuid

        :returns: a `pykeepass.group.Group` object or None if it does not exist
        """
        assert isinstance(uuid, UUID), "uuid needs to be of type UUID"
        return self.db.find_groups(uuid=uuid, first=True)

    def get_group_name(self, data: Union[Group, UUID]) -> str:
        """Get group name from a group or an uuid

        :param data: a group or an uuid
        :returns: group name or an empty string if it does not exist
        :rtype: str
        """
        if isinstance(data, UUID):
            group: Group = self.db.find_groups(uuid=data, first=True)
            if not group:
                logging.warning(
                    "Trying to look up a non-existing UUID %s, this should "
                    "never happen", data)
                return ""
        else:
            group = data

        return group.name or ""

    def get_notes(self, data: Union[Entry, Group, UUID]) -> str:
        """Get notes from an entry, a group or an uuid

        :param data: a group or an uuid
        :returns: notes or an empty string if it does not exist
        :rtype: str
        """
        if isinstance(data, UUID):
            if self.check_is_group(data):
                value: Union[Entry, Group] = self.db.find_groups(
                    uuid=data, first=True)
                if not value:
                    logging.warning(
                        "Trying to look up a non-existing UUID %s, this "
                        "should never happen", data)
                    return ""
            else:
                value = self.db.find_entries(uuid=data, first=True)
                if not value:
                    logging.warning(
                        "Trying to look up a non-existing UUID %s, this "
                        "should never happen", data)
                    return ""
        else:
            value = data

        return value.notes or ""

    def get_icon(self, data: Union[Entry, Group, UUID]) -> Optional[int]:
        """Get an entry icon from an entry, a group or an uuid

        :param data: entry, group or uuid
        :returns: icon number (int) or None in case of no/invalid icon data.
                  Note that the number range could still be outside of the
                  supported number range 0-68.
        :rtype: Optional[int]
        """
        if isinstance(data, UUID):
            if self.check_is_group(data):
                value: Union[Entry, Group] = self.db.find_groups(
                    uuid=data, first=True)
                if not value:
                    logging.warning(
                        "Trying to look up a non-existing UUID %s, this "
                        "should never happen", data)
                    return None
            else:
                value = self.db.find_entries(uuid=data, first=True)
                if not value:
                    logging.warning(
                        "Trying to look up a non-existing UUID %s, this "
                        "should never happen", data)
                    return None
        else:
            value = data
        try:
            icon = int(value.icon)
        except TypeError:
            return None
        return icon

    #
    # Entry Transformation Methods
    #

    # Return the belonging entry object for a entry uuid
    def get_entry_object_from_uuid(self, uuid):
        return self.db.find_entries(uuid=uuid, first=True)

    def get_entry_name(self, data: Union[Entry, UUID]) -> str:
        """Get entry name from an uuid or an entry

        Passing in an Entry is more performant than passing in a UUID
        as we avoid having to look up the entry.
        :param data: UUID or Entry
        :returns: entry name or an empty string if it does not exist
        :rtype: str
        """
        if isinstance(data, UUID):
            entry: Entry = self.db.find_entries(uuid=data, first=True)
            if not entry:
                logging.warning(
                    "Trying to look up a non-existing UUID %s, this should "
                    "never happen", data)
                return ""
        else:
            entry = data

        return entry.title or ""

    def get_entry_username(self, data: Union[Entry, UUID]) -> str:
        """Get an entry username from an entry or an uuid

        Passing in an Entry is more performant than passing in a UUID
        as we avoid having to look up the entry.
        :param data: entry or uuid
        :returns: entry username or an empty string if it does not exist
        :rtype: str
        """
        if isinstance(data, UUID):
            entry: Entry = self.db.find_entries(uuid=data, first=True)
            if not entry:
                logging.warning(
                    "Trying to look up a non-existing UUID %s, this should "
                    "never happen", data)
                return ""
        else:
            entry = data

        return entry.username or ""

    def get_entry_password(self, data: Union[Entry, UUID]) -> str:
        """Get an entry password from an entry or an uuid

        Passing in an Entry is more performant than passing in a UUID
        as we avoid having to look up the entry.
        :param data: entry or uuid
        :returns: entry password or an empty string if it does not exist
        :rtype: str
        """
        if isinstance(data, UUID):
            entry: Entry = self.db.find_entries(uuid=data, first=True)
            if not entry:
                logging.warning(
                    "Trying to look up a non-existing UUID %s , this should "
                    "never happen", data)
                return ""
        else:
            entry = data

        return entry.password or ""

    def get_entry_url(self, data: Union[Entry, UUID]) -> str:
        """Get an entry url from an entry or an uuid

        Passing in an Entry is more performant than passing in a UUID
        as we avoid having to look up the entry.
        :param data: UUID or Entry
        :returns: entry url or an empty string if it does not exist
        :rtype: str
        """
        if isinstance(data, UUID):
            entry: Entry = self.db.find_entries(uuid=data, first=True)
            if not entry:
                logging.warning(
                    "Trying to look up a non-existing UUID %s, this should "
                    "never happen", data)
                return ""
        else:
            entry = data

        return entry.url or ""

    #
    # Database Modifications
    #

    # Add new group to database
    def add_group_to_database(self, name, icon, notes, parent_group):
        group = self.db.add_group(parent_group, name, icon=icon, notes=notes)
        self.is_dirty = True
        self.set_element_mtime(parent_group)

        return group

    # Add new entry to database
    def add_entry_to_database(
        self,
        group: Group,
        name: Optional[str] = "",
        username: Optional[str] = "",
        password: Optional[str] = "",
    ) -> Entry:
        force: bool = self.check_entry_in_group_exists("", group)
        entry = self.db.add_entry(
            group,
            name,
            username,
            password,
            url=None,
            notes=None,
            expiry_time=None,
            tags=None,
            icon="0",
            force_creation=force,
        )
        self.is_dirty = True
        self.set_element_mtime(group)

        return entry

    # Delete an entry
    def delete_from_database(self, entity: Union[Entry, Group]) -> None:
        """Delete an Entry or a Group from the database.

        :param entity: Entity or Group to delete
        """
        if isinstance(entity, Entry):
            self.db.delete_entry(entity)
        else:
            self.db.delete_group(entity)

        self.is_dirty = True
        if entity.parentgroup is not None:
            self.set_element_mtime(entity.parentgroup)

    def duplicate_entry(self, entry: Entry) -> None:
        """Duplicate an entry

        :param Entry entry: entry to duplicate
        """
        title: str = entry.title or ""
        username: str = entry.username or ""
        password: str = entry.password or ""

        # NOTE: With clone is meant a duplicated object, not the process
        # of cloning/duplication; "the" clone
        clone_entry: Entry = self.db.add_entry(
            entry.parentgroup, title + " - " + _("Clone"), username, password,
            url=entry.url, notes=entry.notes, expiry_time=entry.expiry_time,
            tags=entry.tags, icon=entry.icon, force_creation=True)

        # Add custom properties
        for key in entry.custom_properties:
            value: str = entry.custom_properties[key] or ""
            clone_entry.set_custom_property(key, value)

        self.is_dirty = True
        if entry.parentgroup is not None:
            self.set_element_mtime(entry.parentgroup)

    # Write all changes to database
    def save_database(self, notification=False):
        if self.save_running is False and self.is_dirty:
            self.save_running = True

            # TODO This could be simplified a lot
            # if a copy of the keyfile was stored in memory.
            # This would require careful checks for functionality that
            # modifies the keyfile.
            if self.db.keyfile:
                gfile = Gio.File.new_for_path(self.db.keyfile)
                exists = gfile.query_exists()
                if not exists:
                    self.save_running = False
                    logging.error("Could not find keyfile")
                    if notification:
                        self.emit("save-notification", False)

                    return

            try:
                self.db.save()
                logging.debug("Saved database")
                self.is_dirty = False
            except Exception:  # pylint: disable=broad-except
                logging.error("Error occurred while saving database")

            if notification:
                self.emit("save-notification", not self.is_dirty)

            self.save_running = False

    @property
    def password(self) -> str:
        """Get the current password or '' if not set"""
        return self.db.password or ""

    @password.setter
    def password(self, new_password: Optional[str]) -> None:
        """Set database password (None if a keyfile is used)"""
        self.db.password = new_password
        self.is_dirty = True

    # Set database keyfile
    def set_database_keyfile(self, new_keyfile):
        self.db.keyfile = new_keyfile
        self.is_dirty = True

    #
    # Entry Modifications
    #

    def set_entry_name(self, uuid, name):
        entry = self.db.find_entries(uuid=uuid, first=True)
        entry.title = name
        self.is_dirty = True
        self.set_element_mtime(entry)

    def set_entry_username(self, uuid, username):
        entry = self.db.find_entries(uuid=uuid, first=True)
        entry.username = username
        self.is_dirty = True
        self.set_element_mtime(entry)

    def set_entry_password(self, entry: Entry, password: str) -> None:
        """Change the password and save it.

        :param Entry entry: entry to change
        :param password: new password
        """
        entry.password = password
        self.is_dirty = True
        self.set_element_mtime(entry)

    def set_entry_url(self, uuid, url):
        entry = self.db.find_entries(uuid=uuid, first=True)
        entry.url = url
        self.is_dirty = True
        self.set_element_mtime(entry)

    def set_entry_notes(self, uuid, notes):
        entry = self.db.find_entries(uuid=uuid, first=True)
        entry.notes = notes
        self.is_dirty = True
        self.set_element_mtime(entry)

    def set_entry_icon(self, uuid, icon):
        entry = self.db.find_entries(uuid=uuid, first=True)
        entry.icon = icon
        self.is_dirty = True
        self.set_element_mtime(entry)

    def set_entry_color(self, uuid, color):
        entry = self.db.find_entries(uuid=uuid, first=True)
        entry.set_custom_property("color_prop_LcljUMJZ9X", color)
        self.is_dirty = True
        self.set_element_mtime(entry)

    def set_entry_attribute(self, entry: Entry, key: str, value: str) -> None:
        """Set an entry attribute.

        :param Entry entry: entry to modify
        :param key: key of the attribute
        :param value: value of the attribute
        """
        entry.set_custom_property(key, value)
        self.is_dirty = True
        self.set_element_mtime(entry)

    def delete_entry_attribute(self, entry: Entry, key: str) -> None:
        """Delete an entry attribute.

        :param Entry entry: entry to modify
        :param str key: the attribute key
        """
        entry.delete_custom_property(key)
        self.is_dirty = True
        self.set_element_mtime(entry)

    def add_entry_attachment(self, uuid, byte_buffer, filename):
        entry = self.db.find_entries(uuid=uuid, first=True)
        attachment_id = self.db.add_binary(byte_buffer)
        attachment = entry.add_attachment(attachment_id, filename)
        self.is_dirty = True
        return attachment

    def delete_entry_attachment(self, attachment):
        try:
            self.db.delete_binary(attachment.id)
        except Exception:  # pylint: disable=broad-except
            logging.warning("Failed to delete attachment.")
        self.is_dirty = True

    # Move an entry to another group
    def move_entry(self, uuid, destination_group_object):
        entry = self.db.find_entries(uuid=uuid, first=True)
        # TODO: we will crash if uuid does not exist
        self.db.move_entry(entry, destination_group_object)
        # pylint: disable=no-member
        if entry.parentgroup:
            self.set_element_mtime(entry.parentgroup)
        self.set_element_mtime(destination_group_object)

    def set_element_atime(self, element):
        element.atime = datetime.utcnow()

    def set_element_mtime(self, element):
        element.mtime = datetime.utcnow()

    #
    # Group Modifications
    #

    def set_group_name(self, uuid, name):
        group = self.db.find_groups(uuid=uuid, first=True)
        group.name = name
        self.is_dirty = True
        self.set_element_mtime(group)

    def set_group_notes(self, uuid, notes):
        group = self.db.find_groups(uuid=uuid, first=True)
        group.notes = notes
        self.is_dirty = True
        self.set_element_mtime(group)

    def set_group_icon(self, uuid, icon):
        group = self.db.find_groups(uuid=uuid, first=True)
        group.icon = icon
        self.is_dirty = True
        self.set_element_mtime(group)

    # Move an group
    def move_group(self, group: Group, dest_group: Group) -> None:
        self.db.move_group(group, dest_group)
        if group.parentgroup is not None:
            self.set_element_mtime(group.parentgroup)
        self.set_element_mtime(dest_group)
        self.is_dirty = True

    #
    # Read Database
    #

    # Return the root group of the database instance
    def get_root_group(self):
        return self.db.root_group

    # Check if root group
    def check_is_root_group(self, group):
        return group.is_root_group

    # Check if entry with title in group exists
    def check_entry_in_group_exists(self, title, group):
        entry = self.db.find_entries(title=title, group=group, recursive=False, history=False, first=True)
        if entry is None:
            return False
        return True

    # Search for an entry or a group
    def search(self, string: str, path: str) -> List[Union[Entry, Group]]:
        full_text_search = passwordsafe.config_manager.get_full_text_search()
        global_search = not passwordsafe.config_manager.get_local_search()
        results: List[Union[Entry, Group]] = []

        def search_entry(entry: Union[Entry, Group], lookfor: List[Union[None, str]]) -> None:
            """Looks if the querry string appears in any on the items of lookfor.
            If there is a match adds the entry to the uuid_list.
            """
            for term in lookfor:
                if term is None:
                    continue
                if string.lower() in term.lower():
                    if global_search and entry not in results:
                        results.append(entry)
                    elif entry.parentgroup is not None:
                        parent_group: Group = entry.parentgroup
                        if parent_group.path == path and entry not in results:
                            results.append(entry)

        for group in self.db.groups:
            if group.is_root_group is False:
                search_entry(group, [group.name])
                if full_text_search:
                    notes = group.notes
                    search_entry(group, [notes])

        for entry in self.db.entries:
            search_entry(entry, [entry.title])
            if full_text_search:
                username = entry.username
                notes = entry.notes
                url = entry.url
                search_entry(entry, [username, notes, url])

        return results

    def check_is_group(self, uuid):
        """Whether uuid is a group uuid"""
        return self.get_group(uuid) is not None

    def check_is_group_object(self, group):
        return isinstance(group, Group)

    def get_attachment_from_id(self, attachment_id):
        return self.db.find_attachments(id=attachment_id, first=True)

    #
    # Properties
    #

    def get_element_creation_date(self, element: Union[SafeEntry, Group]) -> str:
        """Returns a string of the Entry|Groups creation time or ''"""
        if isinstance(element, SafeEntry):
            elem = element.entry
        else:
            elem = element

        if elem.ctime is None:
            return ""
        return elem.ctime.strftime("%x %X")

    def get_element_acessed_date(self, element: Union[SafeEntry, Group]) -> str:
        """Returns a string of the Entry|Groups access time or ''"""
        if isinstance(element, SafeEntry):
            elem = element.entry
        else:
            elem = element

        if elem.atime is None:
            return ""
        return elem.atime.strftime("%x %X")

    def get_element_modified_date(self, element: Union[SafeEntry, Group]) -> str:
        """Returns a string of the Entry|Groups modification time or ''"""
        if isinstance(element, SafeEntry):
            elem = element.entry
        else:
            elem = element

        if elem.mtime is None:
            return ""
        return elem.mtime.strftime("%x %X")

    #
    # Database creation methods
    #

    # Set the first password entered by the user (for comparing reasons)
    def set_password_try(self, password):
        self.password_try = password

    def compare_passwords(self, password2: str) -> bool:
        """Compare the first password entered by the user with the second one

        It also does not allow empty passwords.
        :returns: True if passwords match and are non-empty.
        """
        if password2 and self.password_try == password2:
            return True
        return False

    def create_keyfile_hash(self, keyfile_path):
        """Create keyfile hash and returns it"""
        hasher = hashlib.sha512()
        with open(keyfile_path, 'rb') as file:
            buffer = 0
            while buffer != b'':
                buffer = file.read(1024)
                hasher.update(buffer)
        return hasher.hexdigest()

    # Set keyfile hash
    def set_keyfile_hash(self, keyfile_path):
        self.keyfile_hash = self.create_keyfile_hash(keyfile_path)

    def parent_checker(self, current_group, moved_group):
        """Returns True if moved_group is an ancestor of current_group"""
        # recursively invoke ourself until we reach the root group
        if current_group.is_root_group:
            return False
        if current_group.uuid == moved_group.uuid:
            return True
        return self.parent_checker(current_group.parentgroup, moved_group)

    @property
    def version(self):
        """returns the database version"""
        return self.db.version

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    @is_dirty.setter
    def is_dirty(self, value: bool) -> None:
        """
        Enables the save_dirty action whenever the Safe is in a
        dirty state. This makes the save menu button sensitive.
        """
        app = Gio.Application.get_default()
        save_action = app.lookup_action("db.save_dirty")
        save_action.set_enabled(value)
        self._is_dirty = value

    @GObject.Signal(arg_types=(bool,))
    def save_notification(self, _saved):
        return
