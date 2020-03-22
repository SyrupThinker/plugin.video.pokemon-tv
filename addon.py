import json
import sys
import urllib
import urlparse
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

from StorageServer import StorageServer

pktv_api = "https://www.pokemon.com/api/pokemontv/v2/channels/"
media_types = ["episode", "movie", "original", ""]
media_names = ["Series", "Movies", "Originals", "Other"]

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
addon = xbmcaddon.Addon()
args = urlparse.parse_qs(sys.argv[2][1:])

xbmcplugin.setContent(addon_handle, "movies")

def notBlank(d, k):
    return d is not None and k is not None and d[k] is not None and d[k] != ""

def newCallback(query):
    return base_url + "?" + urllib.urlencode(query)

def fetchDb(lang):
    response = urllib.urlopen(pktv_api + lang + "/") 
    if response.getcode() != 200:
        raise
        
    return json.load(response)

def getChannel(db, cid):
    for channel in db:
        if channel["channel_id"] == cid:
            return channel

    return None

cache = StorageServer("pokemontvdb", 30)

db = cache.cacheFunction(fetchDb, addon.getSetting("language"))

xbmc.log(sys.argv[2], xbmc.LOGWARNING)
mode = args.get("mode", None)
if mode is not None:
    mode = mode[0]

if mode is None:
    # Type selection
    for i, variant in enumerate(media_types):
        item = xbmcgui.ListItem(media_names[i])
        callback = newCallback({
            "mode": "channels",
            "type": variant,
        })
        xbmcplugin.addDirectoryItem(
            handle = addon_handle, url = callback,
            listitem = item, isFolder = True
        )
    xbmcplugin.endOfDirectory(addon_handle)

elif mode == "channels":
    # Channel list
    variant = args.get("type", [""])[0]
    channels = [c for c in db if (variant == "" and c["media_type"] not in media_types) or c["media_type"] == variant]

    def channel_cmp(a, b):
        if variant == "episode":
            # We assume that every episode channel contains only one season
            # Sort from lowest to highest season

            init = cmp(int(a["media"][0]["season"]), int(b["media"][0]["season"]))
            if init == 0:
                # If a season is split up, order them correctly to each other
                init = cmp(int(a["media"][0]["episode"]), int(b["media"][0]["episode"]))

            return init
        else:
            # Otherwise sort by creation date, newest to oldest
            return cmp(int(b["channel_creation_date"]), int(a["channel_creation_date"]))

    channels.sort(channel_cmp)

    for channel in channels:
        item = xbmcgui.ListItem(channel["channel_name"])
        callback = newCallback({
            "mode": "videos",
            "channel": channel["channel_id"],
            "variant": variant,
        })
        xbmcplugin.addDirectoryItem(
            handle = addon_handle, url = callback,
            listitem = item, isFolder = True
        )
    xbmcplugin.endOfDirectory(addon_handle)

elif mode == "videos":
    # Episode list
    channel_id = args.get("channel", [""])[0]
    variant = args.get("variant", [""])[0]

    channel = getChannel(db, channel_id)
    if channel is not None:
        videos = channel["media"]
        if videos is not None and len(videos) > 0:
            quality = addon.getSetting("quality")
            for video in videos:
                item = xbmcgui.ListItem(video["title"])

                if video["images"] is not None and notBlank(video["images"], "large"):
                    for typ in ["thumb", "poster", "banner", "fanart"]:
                        item.addAvailableArtwork(video["images"]["large"], typ)

                if notBlank(video, "captions"):
                    item.setSubtitles([video["captions"]])

                metadata = {}
                metadata["title"] = video["title"]
                metadata["sorttitle"] = video["title"]
                if notBlank(video, "season"):
                    metadata["season"] = int(video["season"])
                    metadata["sortseason"] = metadata["season"]
                if notBlank(video, "episode"):
                    metadata["episode"] = int(video["episode"])
                    metadata["sortepisode"] = metadata["episode"]
                if notBlank(video, "description"):
                    metadata["episodeguide"] = video["description"]
                    metadata["plotoutline"] = video["description"]
                    metadata["plot"] = video["description"]
                metadata["rating"] = video["rating"] * 2

                item.setInfo("video", metadata)

                callback = None
                if quality == "Low":
                    callback = video["offline_url"]
                elif quality == "Dynamic":
                    callback = video["stream_url"]
                    
                xbmcplugin.addDirectoryItem(
                    handle = addon_handle, url = callback,
                    listitem = item
                )
    xbmcplugin.endOfDirectory(addon_handle)
