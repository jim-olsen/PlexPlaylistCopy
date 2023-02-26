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
    print("\nSearching for items on target server...")
    matching_tracks = target_server.search(source_item.title, libtype='album', limit=100)
    matched_item = None
    for track in matching_tracks:
        if simplify_string(track.title) == simplify_string(source_item.title) and simplify_string(track.parentTitle) \
                == simplify_string(source_item.parentTitle):
            print("\nFound exact match!")
            time.sleep(0.3)
            matched_item = track
            break
    if matched_item is None:
        print("")
        
        matching_tracks = target_server.search(simplify_string(source_item.title), libtype='album', limit=100)
        if len(matching_tracks) > 0:
            print("No exact match found, but these are very similar:\n")
            selection = select_item(matching_tracks, "\nSelect matching album number or 'n' to skip the album: ",
                                "     %(index)x: Title: %(title)s, Artist: %(parentTitle)s")
        else:
            print("Album not found.\n")
            time.sleep(1)
            selection = None
            
        if selection is not None:
            matched_item = matching_tracks[int(selection)]
            print(f"     Adding Album {matched_item.title}, {matched_item.parentTitle}")
            

    return matched_item


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
    print("##########################")
    print("#     Select section     #")
    print("##########################")
    print("")
    
    
    sections = source_server.library.sections()
    
    selection = select_item(sections, "\nSelect the number of the section the collection is a part of: ",
                            "%(index)x: %(title)s")
                        
    source_section = sections[selection]
    
    cls()
    print("#####################################")
    print("#     Select destination server     #")
    print("#####################################")
    print("")
    
    selection = select_item(available_servers, "\nSelect the server to which you want to copy the collection: ",
        "%(index)x: %(name)s")
    target_server = available_servers[selection].connect()
    
    cls()
    print("######################################")
    print("#     Select destination section     #")
    print("######################################")
    print("")
    
    sections = target_server.library.sections()
    
    selection = select_item(sections, "\nSelect the number of the section the collection is a part of: ",
                            "%(index)x: %(title)s")
    
    target_section = sections[selection]
    
    cls()
    print("#############################")
    print("#     Select collection     #")
    print("#############################")
    print("")
    
    collections = source_section.collections()
    
    selection = select_item(collections, "\nSelect the number of the collection you want to copy: ",
                            "%(index)x: %(title)s")
    
    source_collection = collections[selection]
    

    cls()
    print("##########################")
    print("#     Name selection     #")
    print("##########################")
    print("")
    
    while True:
        use_original_name = input("Do you want to keep the same name for the collection on the destination server? (y/n): ").lower().strip()
        if use_original_name == "y":
            target_collection_title = source_collection.title
            break
        elif use_original_name == "n":
            target_collection_title = input("\nEnter the name to be used for the copied collection: ")
            break
        else:
            continue
    
    try:
        target_collection = target_section.collection(target_collection_title)
        print("Target collection already exists, all missing tracks will be added.")
    except NotFound:
        print("Target collection does not exist, a new collection will be created.")
        target_collection = None

    total_items = 0
    unmatched_items = []
    collection_items = []
    for item in source_collection.items():
        
        cls()
        print("#########################")
        print("#     Finding items     #")
        print("#########################")
        print("")
        
        total_items += 1
        print(f"Attempting to match item #{total_items}:\n\nTitle:{item.title}\nArtist: {item.parentTitle}\n")
        print("-----------------------------")

        matched_item = None
        try:
            if target_collection is not None:
                target_collection.item(item.title)
                print("Found existing entry in collection, skipping item....")
            else:
                matched_item = find_matching_item(item, target_section)
                if matched_item is None:
                    unmatched_items.append(item)
        except NotFound:
            matched_item = find_matching_item(item, target_section)
            if matched_item is None:
                unmatched_items.append(item)

        if matched_item is not None:
            collection_items.append(matched_item)

    cls()
    print("#################")
    print("#     Done!     #")
    print("#################")
    print("")
    
    if len(collection_items) > 0:
        if target_collection is None:
            target_section.createCollection(target_collection_title, items=collection_items)
            print("Added new collection to target server!")
        else:
            target_collection.addItems(collection_items)
            print("Updated collection on target server!")
    else:
        print("Collection could not be copied because no matching items could be found. ")
        
        
    print("\n\nThe following items could not be copied:\n")
    for item in unmatched_items:
        print(f"No match for Album: {item.title}, Artist: {item.parentTitle}")
    
    


#
# Just executes the main function if run manually
#
if __name__ == '__main__':
    main()
    