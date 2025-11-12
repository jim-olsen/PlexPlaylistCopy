from plexapi.myplex import MyPlexAccount
from plexapi.exceptions import NotFound, BadRequest

import re
import csv
import os


#
# Given a list, select a single item from the list, or return None if they skip the selection
#
# item_list - Contains the list of items to choose from
# prompt - The prompt to display to the user for choosing an item
# item_format_str - An old style python format string to use to display each item.  The names of the values in the
#                   format string should match an attribute in the given items.  So for example 'Title: %(title)s'
#                   means that each item should have an attribute of 'title' in it
# RETURN VALUE - Either None if no item is selected, or the index of the item chosen from the list
#
#
def select_item(item_list, prompt, item_format_str):
    pattern = re.compile('(?:%\\()([A-z]+)(?:\\))')
    return_value = None
    for item_index, item in enumerate(item_list):
        display_string_values = {}
        # Create a dynamic list of the values for this item
        for field in pattern.findall(item_format_str):
            display_string_values[field] = getattr(item, field, "N/A")
        display_string_values['index'] = item_index
        print(item_format_str % display_string_values)
    while True:
        selection = input(prompt)
        if selection.lower() != 'n':
            try:
                return_value = int(selection)
                break
            except ValueError:
                print (f"{selection} is not a valid choice.  Please enter either a number or 'n' to indicate none")
                pass
        else:
            break

    return return_value


#
# This method simplifies the string to trimmed whitespace and no special characters all lower case.  Often one of these
# issues is a source of problems in matching titles.
#
def simplify_string(source_str):
    return ''.join(e for e in source_str if e.isalnum() or e == ' ').strip().lower()


#
# Create a safe filename from an arbitrary string (e.g., playlist title)
# Removes/normalizes characters that are invalid on common filesystems (Windows/macOS/Linux).
#
def sanitize_filename(name: str) -> str:
    # Characters not allowed on Windows: < > : " / \ | ? * and control chars
    invalid_chars = '<>:"/\\|?*'
    sanitized = ''.join('_' if (c in invalid_chars or ord(c) < 32) else c for c in name)
    # Trim spaces and dots from ends (Windows quirk)
    sanitized = sanitized.strip(' .')
    # Provide a default if empty after sanitization
    return sanitized if sanitized else 'playlist'

#
# Login to your plex account, and list out all possible devices by name.  Servers and clients will show up here, so
# just allow the user to choose which one they want.  Then choose the playlist from the playlists on the source server
# and ask for the user to provide a name for the playlist on the target server.  If the playlist exists, perform
# a merge of the data.  If not, create a new playlist with all matched items.
#
def main():
    user = input("Enter username: ")
    password = input("Enter Password: ")
    account = MyPlexAccount(user, password)

    available_resources = account.resources()
    print("")
    selection = select_item(account.resources(), "Select the server which you wish to copy a playlist from >>>",
                            "%(index)x: %(name)s")
    source_server = account.resource(available_resources[selection].name).connect()
    source_playlists = source_server.playlists()
    print("")
    selection = select_item(source_playlists, "Select the number of the playlist to copy from >>>",
                            "%(index)x: %(title)s")
    source_playlist = source_playlists[selection]

    # Prepare CSV file named after the playlist title in the current working directory
    csv_filename = f"{sanitize_filename(source_playlist.title)}.csv"
    headers = ["Title", "Album", "Artist", "Duration", "Track Number"]

    # Write CSV with UTF-8 encoding
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        for item in source_playlist.items():
            title = getattr(item, 'title', '')
            album = getattr(item, 'parentTitle', '')
            artist = getattr(item, 'grandparentTitle', '')
            duration = getattr(item, 'duration', '')
            track_no = getattr(item, 'trackNumber', '')

            print(f"Title: {title}, Album: {album}, Artist: {artist}, Duration: {duration}, Track Number: {track_no}")
            writer.writerow([title, album, artist, duration, track_no])

    print(f"\nExported playlist to CSV: {os.path.abspath(csv_filename)}")


#
# Just executes the main function if run manually
#
if __name__ == '__main__':
    main()
