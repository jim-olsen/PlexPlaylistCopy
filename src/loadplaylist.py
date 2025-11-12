from plexapi.myplex import MyPlexAccount
from plexapi.exceptions import NotFound, BadRequest

import re
import os
import csv


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
def find_matching_item(csv_item, target_server):
    """
    Given a CSV row (dict) describing a track, find the best matching track on the target server.
    Matching strategy:
      1) Search by title on server (limit 100)
      2) Filter by simplified Title and Album equality
      3) If Artist provided, also require simplified Artist equality
      4) If multiple remain and Track Number provided, require track number equality
      5) If multiple remain and Duration provided, pick by duration within tolerance (±2000 ms)
      6) If still multiple or none, let user select from close matches (search by simplified title); allow skip
    """
    title = csv_item.get('Title', '') or csv_item.get('title', '')
    album = csv_item.get('Album', '') or csv_item.get('album', '')
    artist = csv_item.get('Artist', '') or csv_item.get('artist', '')
    duration = csv_item.get('Duration')
    track_no = csv_item.get('Track Number') or csv_item.get('TrackNumber')

    # Normalize numeric fields
    try:
        duration = int(duration) if duration not in (None, '') else None
    except ValueError:
        duration = None
    try:
        track_no = int(track_no) if track_no not in (None, '') else None
    except ValueError:
        track_no = None

    print("     Searching for tracks in target server")
    try:
        candidates = target_server.search(title, mediatype='track', limit=100)
    except BadRequest:
        candidates = []

    def match_basic(t):
        return simplify_string(t.title) == simplify_string(title) and \
               simplify_string(getattr(t, 'parentTitle', '')) == simplify_string(album)

    filtered = [t for t in candidates if match_basic(t)]

    # Artist constraint if available
    if artist:
        filtered_artist = [t for t in filtered if simplify_string(getattr(t, 'grandparentTitle', '')) == simplify_string(artist)]
        if filtered_artist:
            filtered = filtered_artist

    # Track number filter if multiple and provided
    if track_no is not None and len(filtered) > 1:
        filtered_track = [t for t in filtered if getattr(t, 'trackNumber', None) == track_no]
        if filtered_track:
            filtered = filtered_track

    # Duration tolerance filter if multiple and provided
    if duration is not None and len(filtered) > 1:
        tol_ms = 5
        filtered_dur = [t for t in filtered if getattr(t, 'duration', None) is not None and abs(getattr(t, 'duration') - duration) <= tol_ms]
        if filtered_dur:
            filtered = filtered_dur

    if len(filtered) == 1:
        t = filtered[0]
        print(f"     Found match for Title: {t.title}, Album: {t.parentTitle}, Artist: {t.grandparentTitle}")
        return t

    # If nothing exact, offer close matches by simplified title
    print("")
    print(f"     Did not find a unique exact match. Close matches to Title: {title}, Album: {album}, Artist: {artist}, Track: {track_no}, Duration: {duration} ms")
    try:
        matching_tracks = target_server.search(simplify_string(title), mediatype='track', limit=100)
    except BadRequest:
        matching_tracks = []

    selection = select_item(
        matching_tracks,
        "     Select matching track number or 'n' for None >>>",
        "     %(index)x: Title: %(title)s, Album: %(parentTitle)s, Artist: %(grandparentTitle)s, Track: %(trackNumber)s, Duration: %(duration)s ms"
    )

    if selection is not None:
        chosen = matching_tracks[int(selection)]
        print(f"     Adding track {chosen.title}, {chosen.parentTitle}")
        return chosen
    else:
        print("     Skipping matching this track....")
        print("")
        return None


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
    selection = select_item(available_resources, "Please select the server you wish to load the playlist to >>>",
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

    # Discover CSV files in current directory
    csv_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]
    if not csv_files:
        print("No CSV files found in the current directory. Please place your exported playlist CSV here and rerun.")
        return

    # Simple objects to allow attribute access in select_item formatting
    class _CSVFile:
        def __init__(self, name):
            self.name = name
            self.title = name

    selection = select_item([_CSVFile(f) for f in csv_files],
                            "Select the CSV file to load from >>>",
                            "%(index)x: %(title)s")
    chosen_csv = csv_files[selection]

    # Read CSV rows
    rows = []
    with open(chosen_csv, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        # Normalize headers to a standard set
        def norm(name):
            return (name or '').strip().lower()
        header_map = {norm(h): h for h in reader.fieldnames or []}
        # Expected keys (case-insensitive):
        key_title = header_map.get('title')
        key_album = header_map.get('album')
        key_artist = header_map.get('artist')
        key_duration = header_map.get('duration')
        key_track = header_map.get('track number') or header_map.get('tracknumber')

        if not key_title or not key_album:
            print("CSV missing required headers 'Title' and/or 'Album'.")
            return

        for r in reader:
            rows.append({
                'Title': r.get(key_title, ''),
                'Album': r.get(key_album, ''),
                'Artist': r.get(key_artist, '') if key_artist else '',
                'Duration': r.get(key_duration, '') if key_duration else '',
                'Track Number': r.get(key_track, '') if key_track else ''
            })

    total_tracks = 0
    unmatched_items = []
    playlist_items = []
    for row in rows:
        print("")
        total_tracks += 1
        print(
            f"Attempting to match track # {total_tracks}, Title:{row.get('Title','')}, Album: {row.get('Album','')}, Artist: {row.get('Artist','')}")

        matched_track = None
        try:
            if target_playlist is not None:
                # Skip if an item with same title already exists in target playlist
                try:
                    target_playlist.item(row.get('Title', ''))
                    print("Found existing entry in playlist, skipping track....")
                    continue
                except NotFound:
                    pass
            matched_track = find_matching_item(row, target_server)
        except BadRequest:
            print("Search failed, skipping...")

        if matched_track is not None:
            playlist_items.append(matched_track)
        else:
            unmatched_items.append(row)

    for row in unmatched_items:
        print(f"No match for Title: {row.get('Title','')}, Album: {row.get('Album','')}, Artist: {row.get('Artist','')}")

    if target_playlist is None:
        target_server.createPlaylist(target_playlist_title, items=playlist_items)
    else:
        target_playlist.addItems(playlist_items)


#
# Just executes the main function if run manually
#
if __name__ == '__main__':
    main()
