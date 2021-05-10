import json
import sys
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import six

from six.moves import urllib
from six.moves import urllib_parse
from StorageServer import StorageServer

pktv_api = "https://www.pokemon.com/api/pokemontv/v2/channels/"
media_types = ["episode", "movie", "original", ""]
media_names = ["Series", "Movies", "Originals", "Other"]

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
addon = xbmcaddon.Addon()
args = urllib_parse.parse_qs(sys.argv[2][1:])

xbmcplugin.setContent(addon_handle, "movies")

PLUGIN_ID = base_url.replace("plugin://","")
MEDIA_URL = 'special://home/addons/{0}/resources/media/'.format(PLUGIN_ID)

#python 3 compatibility methods
if six.PY3:

    def cmp(a, b):
        return (a > b) - (a < b)

    def cmp_to_key(mycmp):
        'Convert a cmp= function into a key= function'
        class K(object):
            def __init__(self, obj, *args):
                self.obj = obj
            def __lt__(self, other):
                return mycmp(self.obj, other.obj) < 0
            def __gt__(self, other):
                return mycmp(self.obj, other.obj) > 0
            def __eq__(self, other):
                return mycmp(self.obj, other.obj) == 0
            def __le__(self, other):
                return mycmp(self.obj, other.obj) <= 0
            def __ge__(self, other):
                return mycmp(self.obj, other.obj) >= 0
            def __ne__(self, other):
                return mycmp(self.obj, other.obj) != 0
        return K

def notBlank(d, k):
    return d is not None and k is not None and d[k] is not None and d[k] != ""

def construct_request(query):
    return base_url + "?" + urllib_parse.urlencode(query)

def fetchDb(lang):
    response = urllib.request.urlopen(pktv_api + lang + "/")
    if response.getcode() != 200:
        raise

    return json.load(response)

def getChannel(db, cid):
    for channel in db:
        if channel["channel_id"] == cid:
            return channel

    return None

cache = StorageServer("pokemontvdb", 48)

db = cache.cacheFunction(fetchDb, addon.getSetting("language"))

xbmc.log(sys.argv[2], xbmc.LOGWARNING)
mode = args.get("mode", None)
if mode is not None:
    mode = mode[0]

if mode is None:

    # Type selection
    for i, variant in enumerate(media_types):
        list_item = xbmcgui.ListItem(media_names[i])
        list_item.setArt({
            "icon":MEDIA_URL + media_names[i] + '.jpg',
            "poster":MEDIA_URL + media_names[i] + '.jpg',
        });
        callback = construct_request({
            "mode": "channels",
            "type": variant,
        })
        xbmcplugin.addDirectoryItem(
            handle = addon_handle,
            url = callback,
            listitem = list_item,
            isFolder = True
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

    if six.PY3:
        channels.sort(key=cmp_to_key(channel_cmp))
    else:
        channels.sort(channel_cmp)

    for channel in channels:
        list_item = xbmcgui.ListItem(channel["channel_name"])
        list_item.setArt({
            "icon":channel["channel_images"]["dashboard_image_1125_1500"],
            "poster":channel["channel_images"]["dashboard_image_1125_1500"],
            "fanart":channel["channel_images"]["spotlight_image_2048_1152"],
        });
        callback = construct_request({
            "mode": "videos",
            "channel": channel["channel_id"],
            "variant": variant,
        })
        xbmcplugin.addDirectoryItem(
            handle = addon_handle, url = callback,
            listitem = list_item, isFolder = True
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
                list_item = xbmcgui.ListItem(video["title"])

                #set episode's images
                if video["images"] is not None and notBlank(video["images"], "large"):
                    for art_type in ["thumb", "poster", "banner", "fanart","icon"]:
                        list_item.setArt({art_type:video["images"]["large"]})

                #add captions
                if notBlank(video, "captions"):
                    list_item.setSubtitles([video["captions"]])

                #set the episode's info
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

                list_item.setInfo("video", metadata)

                callback = None
                if quality == "Low":
                    callback = video["offline_url"]
                elif quality == "Dynamic":
                    callback = video["stream_url"]

                xbmcplugin.addDirectoryItem(
                    handle = addon_handle, url = callback,
                    listitem = list_item
                )
    xbmcplugin.endOfDirectory(addon_handle)
