# Plex Playlist Copy

This python code is utilized to copy a playlist from one server in your account to another.  It will not move any music
files, so the music must already be installed on both servers.  It will just recreate the playlist on the new server
using the metadata from the playlist to find the existing songs on the target plex server.  If an exact match is not
found, it will do a search of similar songs, and allow you to pick one or skip it all together.

If the playlist exists, then it will find any new or missing items in the existing playlist, and add those into the
playlist as well.

This is useful if you maintain multiple servers at multiple locations (for instance a main home and a summer home)
where you want to preserve your playlists on both servers to execute locally rather than across the network.  It is also
useful if you are settting up a new server replacing the old one, and things such as files locations are not the same
yet you want to keep your playlists.

Keep in mind this is doing a very rudimentary match based on metadata only.  It is not doing any fingerprinting, hashing
or any other methodology.  It is assuming that you likely have the same library of music on both servers, but just want
to have the same playlists on both servers as well.

Also, this is done as a quick and dirty python script.  A known limitation right now is if the titles of the songs don't
exactly match, it will show up as missing on a sync so you must manually skip those.  It might be something I resolve
but since my libraries are very close on both servers, it has not been a big concern for me.

Also, there is very little protection built into this script for user error, so please enter all input accurately.  I
just did this for my own needs quickly, but will probably improve over time.  So when it asks you to choose a number
of a track in a list, make sure you enter a valid number, or just 'n' if you want to skip that track.

This code requires python v3.6 or higher.

To use, first make sure the plex python library is installed on your python instance:
```
pip install plexapi
```

Then run:

```
python ./src/copyplaylist.py
```

It will prompt you for your plex username and password.

Then choose the source server by number from the list.

Next, it will list out all playlists on that server, and again choose by entering the number from the list

Then it will ask you to choose the target server, again from the list by number

Next it will ask you to enter the textual name of the playlist you either want to sync or create.  Enter an existing one
to sync, or any text to create a new playlist.

You will then see it going song by song.  If it finds exact matches it will proceed to the next track.

If it does not find an exact match, it will give you a list of possible matches by doing a search on the title.  Either
select an acceptable match from the list by number, or type 'n' followed by the enter key to skip this track.

After all songs have been completed, it will write the results to the target server.  If you end the program before it
has finished all of the tracks, no results will be written.

## This is experimental code so use at your own risk!  I am not responsible for any damage to your plex instances.