from plexapi.myplex import MyPlexAccount
from plexapi.exceptions import NotFound


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
        if track.title == source_item.title and track.parentTitle == source_item.parentTitle:
            print(f"     Found exact match for Title: {track.title}, Album: {track.parentTitle}, Artist: {track.grandparentTitle}")
            matched_track = track
            break
    if matched_track is None:
        i = 0
        print("")
        print(f"     Did not find an exact match, but these are close matches to Title: {source_item.title}, Album: {source_item.parentTitle}, Artist: {source_item.grandparentTitle}")
        for track in matching_tracks:
            print(f"     {i}: Title: {track.title},  Album: {track.parentTitle} Artist: {track.grandparentTitle}")
            i += 1
        print("")
        selection = input("     Select matching track number or N for None >>>")
        if selection != "n" and selection != "N":
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
    i = 0
    available_resources = account.resources()
    print("")
    for resource in available_resources:
        print(f"{i}: {resource.name}")
        i += 1
    key_input = input("Select the server which you wish to copy a playlist from >>>")

    source_server = account.resource(available_resources[int(key_input)].name).connect()
    source_playlists = source_server.playlists()
    i = 0
    print("")
    for playlist in source_playlists:
        print(f"{i}: {playlist.title}")
        i += 1
    key_input = input("Select the playlist number we should copy from >>>")
    source_playlist = source_playlists[int(key_input)]

    i = 0
    print("")
    for resource in available_resources:
        print(f"{i}: {resource.name}")
        i += 1
    key_input = input("Please select the server you wish to copy the playlist to >>>")
    target_server = account.resource(available_resources[int(key_input)].name).connect()

    print("")
    target_playlist_title = input("Please enter the name to use for the target playlist >>>")
    target_playlist = None
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
        print(f"Attempting to match track # {total_tracks}, Title:{item.title}, Album: {item.parentTitle}, Artist: {item.grandparentTitle}")

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
