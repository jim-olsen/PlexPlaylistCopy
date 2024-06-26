from plexapi.myplex import MyPlexAccount
from plexapi.exceptions import NotFound, BadRequest

import re


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
# Given a source item, return either the exact match that exists in the target server, or a user chosen item
# from the closest matches that could be found, or None if no match nor user choice could be found for the source item.
#
# source_item - The item that we should be finding a match for on the target server
#
def find_matching_item(source_item, target_server):
    print("     Searching for tracks in target server")
    matching_tracks = target_server.search(source_item.title, mediatype='track', limit=100)
    matched_track = None
    for track in matching_tracks:
        if simplify_string(track.title) == simplify_string(source_item.title) and simplify_string(track.parentTitle) \
                == simplify_string(source_item.parentTitle):
            print(
                f"     Found exact match for Title: {track.title}, Album: {track.parentTitle}, Artist: {track.grandparentTitle}")
            matched_track = track
            break
    if matched_track is None:
        print("")
        print(
            f"     Did not find an exact match, but these are close matches to Title: {source_item.title}, Album: {source_item.parentTitle}, Artist: {source_item.grandparentTitle}")
        matching_tracks = target_server.search(simplify_string(source_item.title), mediatype='track', limit=100)
        selection = select_item(matching_tracks, "     Select matching track number or 'n' for None >>>",
                                "     %(index)x: Title: %(title)s, Album: %(parentTitle)s, Artist: %(grandparentTitle)s"
                                )

        if selection is not None:
            matched_track = matching_tracks[int(selection)]
            print(f"     Adding track {matched_track.title}, {matched_track.parentTitle}")
        else:
            print("     Skipping matching this track....")
            print("")

    return matched_track


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

    selection = select_item(available_resources, "Please select the server you wish to copy the playlist to >>>",
                            "%(index)x: %(name)s")
    target_server = account.resource(available_resources[selection].name).connect()

    print("")
    target_playlist_title = input("Please enter the name to use for the target playlist >>>")
    try:
        target_playlist = target_server.playlist(target_playlist_title)
        print("Target playlist exists, so updating any missing tracks")
    except NotFound:
        print("Target playlist does not exist, will create a new playlist")
        target_playlist = None

    total_tracks = 0
    unmatched_items = []
    playlist_items = []
    for item in source_playlist.items():
        print("")
        total_tracks += 1
        print(
            f"Attempting to match track # {total_tracks}, Title:{item.title}, Album: {item.parentTitle}, Artist: {item.grandparentTitle}")

        matched_track = None
        try:
            if target_playlist is not None:
                target_playlist.item(item.title)
                print("Found existing entry in playlist, skipping track....")
            else:
                matched_track = find_matching_item(item, target_server)
        except NotFound:
            matched_track = find_matching_item(item, target_server)
            if matched_track is None:
                unmatched_items.append(item)
        except BadRequest:
            print("Search failed, skipping...")

        if matched_track is not None:
            playlist_items.append(matched_track)

    for item in unmatched_items:
        print(f"No match for Title: {item.title}, Album: {item.parentTitle}, Artist: {item.grandparentTitle}")

    if target_playlist is None:
        target_server.createPlaylist(target_playlist_title, items=playlist_items)
    else:
        target_playlist.addItems(playlist_items)


#
# Just executes the main function if run manually
#
if __name__ == '__main__':
    main()
