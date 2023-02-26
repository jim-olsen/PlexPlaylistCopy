from plexapi.myplex import MyPlexAccount
from plexapi.exceptions import NotFound

from getpass import getpass

import os

import time

import re


#
# Clear the screen 
# uses 'cls' on windows and 'clear' on linux / macos
#
def cls():
    os.system('cls' if os.name=='nt' else 'printf "\033c"')

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
    print("\nSearching for tracks on target server...")
    matching_tracks = target_server.search(source_item.title, mediatype='track', limit=100)
    matched_track = None
    for track in matching_tracks:
        if simplify_string(track.title) == simplify_string(source_item.title) and simplify_string(track.parentTitle) \
                == simplify_string(source_item.parentTitle):
            print("\nFound exact match!")
            time.sleep(0.3)
            matched_track = track
            break
    if matched_track is None:
        print("")
        
        matching_tracks = target_server.search(simplify_string(source_item.title), mediatype='track', limit=100)
        if len(matching_tracks) > 0:
            print("No exact match found, but these are very similar:\n")
            selection = select_item(matching_tracks, "\nSelect matching track number or 'n' to skip the track: ",
                                "     %(index)x: Title: %(title)s, Album: %(parentTitle)s, Artist: %(grandparentTitle)s")
        else:
            print("Track not found.\n")
            time.sleep(1)
            selection = None
            
        if selection is not None:
            matched_track = matching_tracks[int(selection)]
            print(f"     Adding track {matched_track.title}, {matched_track.parentTitle}")
            

    return matched_track


#
# Login to your plex account, and list out all possible devices by name.  Servers will show up here, so
# just allow the user to choose which one they want.  Then choose the playlist from the playlists on the source server
# and ask for the user to provide a name for the playlist on the target server.  If the playlist exists, perform
# a merge of the data.  If not, create a new playlist with all matched items.
#
def main():
    
    cls()
    print("##############################")
    print("#     Plex Playlist Copy     #")
    print("##############################")
    print("To start, please log in to your Plex account.")
    print("")
    
    user = input("Enter username: ")
    password = getpass("Enter Password: ")
    
    while True:
        two_factor_used = input("Is your account using two factor authentication? (y/n): ").lower().strip()
        if two_factor_used == "y":
            two_factor_used = True
            break
        elif two_factor_used == "n":
            two_factor_used = False
            break
        else:
            continue
    
    if two_factor_used:
        code = getpass("Enter Two-Factor Code: ")
        account = MyPlexAccount(username=user, password=password, code=code)
    else:
        account = MyPlexAccount(username=user, password=password)

    available_resources = account.resources()
    available_servers = []
    
    for resource in available_resources:
        if resource.product == "Plex Media Server":
            available_servers.append(resource)
        
    cls()
    print("################################")
    print("#     Select source server     #")
    print("################################")
    print("")
    
    selection = select_item(available_servers, "\nSelect the server from which you want to copy a playlist: ",
                            "%(index)x: %(name)s")
    source_server = available_servers[selection].connect()
    
    # Remove source server from the list so that it is not available as a destination
    available_servers.pop(selection)
    
    cls()
    print("#####################################")
    print("#     Select destination server     #")
    print("#####################################")
    print("")
    
    selection = select_item(available_servers, "\nSelect the server to which you want to copy the playlist: ",
                            "%(index)x: %(name)s")
    target_server = available_servers[selection].connect()
    
    cls()
    print("###########################")
    print("#     Select playlist     #")
    print("###########################")
    print("")
    
    source_playlists_unfiltered = source_server.playlists()
    source_playlists = []
    
    for playlist in source_playlists_unfiltered:
        if playlist.smart == False:
            source_playlists.append(playlist)
    
    selection = select_item(source_playlists, "\nSelect the number of the playlist you want to copy: ",
                            "%(index)x: %(title)s")
    source_playlist = source_playlists[selection]

    cls()
    print("##########################")
    print("#     Name selection     #")
    print("##########################")
    print("")
    
    while True:
        use_original_name = input("Do you want to keep the same name for the playlist on the destination server? (y/n): ").lower().strip()
        if use_original_name == "y":
            target_playlist_title = source_playlist.title
            break
        elif use_original_name == "n":
            target_playlist_title = input("\nEnter the name to be used for the copied playlist: ")
            break
        else:
            continue
    
    try:
        target_playlist = target_server.playlist(target_playlist_title)
        print("Target playlist already exists, all missing tracks will be added.")
    except NotFound:
        print("Target playlist does not exist, a new playlist will be created.")
        target_playlist = None

    total_tracks = 0
    unmatched_items = []
    playlist_items = []
    for item in source_playlist.items():
        
        cls()
        print("##########################")
        print("#     Finding tracks     #")
        print("##########################")
        print("")
        
        total_tracks += 1
        print(f"Attempting to match track #{total_tracks}:\n\nTitle:{item.title}\nAlbum: {item.parentTitle}\nArtist: {item.grandparentTitle}\n")
        print("-----------------------------")

        matched_track = None
        try:
            if target_playlist is not None:
                target_playlist.item(item.title)
                print("Found existing entry in playlist, skipping track....")
            else:
                matched_track = find_matching_item(item, target_server)
                if matched_track is None:
                    unmatched_items.append(item)
        except NotFound:
            matched_track = find_matching_item(item, target_server)
            if matched_track is None:
                unmatched_items.append(item)

        if matched_track is not None:
            playlist_items.append(matched_track)

    cls()
    print("#################")
    print("#     Done!     #")
    print("#################")
    print("")
    
    if target_playlist is None:
        target_server.createPlaylist(target_playlist_title, items=playlist_items)
        print("Added new playlist to target server!")
    else:
        target_playlist.addItems(playlist_items)
        print("Updated playlist on target server!")
        
    print("\n\nThe following tracks could not be copied:\n")
    for item in unmatched_items:
        print(f"No match for Title: {item.title}, Album: {item.parentTitle}, Artist: {item.grandparentTitle}")
    
    


#
# Just executes the main function if run manually
#
if __name__ == '__main__':
    main()
    