# from mock_framework import *
from datetime import datetime
import requests
import requests_cache

PREFIX = "/video/sonarr"
NAME = "Sonarr"


def Start():
    requests.packages.urllib3.disable_warnings()
    ObjectContainer.art = R("logo.png")
    ObjectContainer.title1 = NAME
    ObjectContainer.title2 = NAME
    DirectoryObject.thumb = R("question-circle.png")
    requests_cache.install_cache("test_cache", backend="memory", expire_after=3600)
    requests_cache.clear()
    local_hour = Datetime.Now().replace(minute=0, second=0, microsecond=0)
    utc_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0, tzinfo=None)
    Dict["utc_offset"] = local_hour - utc_hour
    Log.Debug("UTC Offset: %s" % Dict["utc_offset"])
    ValidatePrefs()


def ValidatePrefs():
    Dict["host"] = "{}://{}:{}".format("http", Prefs["ip"], Prefs["port"])
    Dict["apiUrl"] = "{}/api/".format(Dict["host"] + Prefs["base"])
    Dict["headers"] = {"X-Api-Key": Prefs["apiKey"]}
    Log.Debug("Sonarr url: %s" % Dict["host"])
    Log.Debug("API Url: %s" % Dict["apiUrl"])


@handler(PREFIX, NAME, "1024.png", "logo.png")
def main_menu():
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(series), title=L("series"), summary=L("seriesInfo"), thumb=R("play.png")))
    oc.add(DirectoryObject(key=Callback(calendar), title=L("calendar"), summary=L("calendarInfo"),
                           thumb=R("calendar.png")))
    oc.add(DirectoryObject(key=Callback(queue), title=L("queue"), summary=L("queueInfo"), thumb=R("cloud.png")))
    oc.add(DirectoryObject(key=Callback(history), title=L("history"), summary=L("historyInfo"), thumb=R("history.png")))
    oc.add(DirectoryObject(key=Callback(wanted), title=L("missing"), summary=L("missingInfo"),
                           thumb=R("exclamation-triangle.png")))
    oc.add(PrefsObject(title=L("settings"), summary=L("settingsInfo"),
                       thumb=R("cogs.png")))
    return oc


@route("%s/calendar/list" % PREFIX)
def calendar():
    start = timestamp(datetime.utcnow() - Datetime.Delta(hours=6))
    end = timestamp(datetime.utcnow() + Datetime.Delta(weeks=1))

    url = Dict["apiUrl"] + "calendar"
    try:
        with requests_cache.disabled():
            r = requests.get(url, params={"start": start, "end": end}, headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)

    oc = ObjectContainer(title2=L("calendar"))
    for e in r.json():
        season_nbr = e["seasonNumber"]
        episode_nbr = e["episodeNumber"]
        episode_id = e["id"]
        dt = Datetime.ParseDate(e["airDateUtc"])
        episode_title = e["title"]
        episode_overview = e.get("overview", L("noInfo"))
        title = "%s - %dX%02d - %s" % (episode_title, season_nbr, episode_nbr, pretty_datetime(dt))
        do = DirectoryObject(key=Callback(episode_options, episode_id=episode_id), title=title,
                             summary=episode_overview)
        for coverType in e["series"]["images"]:
            if coverType["coverType"] == "poster":
                do.thumb = Callback(get_thumb, url=coverType["url"])
                break
        oc.add(do)
    return oc


@route("%s/episode/list" % PREFIX)
def episode(series_id, season_id):
    url = Dict["apiUrl"] + "episode"
    try:
        with requests_cache.disabled():
            r = requests.get(url, params={"seriesId": series_id}, headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    request = r.json()
    series_title = request[0]["series"]["title"]
    oc = ObjectContainer(title2=series_title)
    for e in reversed(request):
        season_nbr = str(e["seasonNumber"])
        if not season_nbr == season_id:
            continue
        thumb = monitor_badge(e["monitored"])
        episode_nbr = e["episodeNumber"]
        title = "%d - %s" % (episode_nbr, e["title"])
        if e["hasFile"]:
            title = "[X] " + title
        else:
            title = "[ ] " + title
        overview = e.get("overview", L("noInfo"))
        summary = str(L("downloaded")) % (e["hasFile"], overview)
        episode_id = e["id"]
        oc.add(DirectoryObject(key=Callback(episode_options, episode_id=episode_id), title=title, summary=summary,
                               thumb=thumb))
    return oc


@route("%s/episode/monitor" % PREFIX, episode_id=int, monitor_state=bool)
def episode_monitor(episode_id, monitor_state):
    oc = ObjectContainer()
    thumb = monitor_badge(monitor_state)
    oc.add(DirectoryObject(key=Callback(episode_monitor_set, episode_id=episode_id, monitor_state=monitor_state),
                           title="Set Monitoring: %s" % monitor_state,
                           summary=str(L("monitorConfirm")) % monitor_state, thumb=thumb))
    return oc


@route("%s/episode/monitor/set" % PREFIX, episode_id=int, monitor_state=bool)
def episode_monitor_set(episode_id, monitor_state):
    url = Dict["apiUrl"] + "episode/%s" % episode_id
    Log.Debug("Episode: %d" % episode_id)
    try:
        with requests_cache.disabled():
            r = requests.get(url, headers=Dict["headers"])
            r.raise_for_status()
            url = Dict["apiUrl"] + "episode"
            puts = r.json()
            puts["monitored"] = monitor_state
            r = requests.put(url, json=puts, headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    return MessageContainer(L("success"), str(L("monitorSet")) % monitor_state)


@route("%s/episode/options" % PREFIX)
def episode_options(episode_id):
    url = Dict["apiUrl"] + "episode/%s" % episode_id
    try:
        with requests_cache.disabled():
            r = requests.get(url, headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    e = r.json()
    title = e["title"]
    episode_id = e["id"]
    monitored = e["monitored"]
    thumb = monitor_badge(monitored)
    oc = ObjectContainer(title2=title)
    oc.add(DirectoryObject(key=Callback(episode_monitor, episode_id=episode_id, monitor_state=(not monitored)),
                           title=L("toggleMonitor"), thumb=thumb))
    oc.add(DirectoryObject(key=Callback(search, episode_id=int(episode_id)), title=L("episodeSearch"),
                           summary=L("episodeSearchInfo"), thumb=R("search.png")))
    return oc


@route("%s/history/list" % PREFIX, page=int, page_size=int)
def history(page=1, page_size=19):
    url = Dict["apiUrl"] + "history"
    try:
        with requests_cache.disabled():
            r = requests.get(url, params={"page": page, "pageSize": page_size, "sortKey": "date", "sortDir": "desc"},
                             headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    oc = ObjectContainer(title2=L("history"))
    for record in r.json()["records"]:
        season_nbr = record["episode"]["seasonNumber"]
        episode_nbr = record["episode"]["episodeNumber"]
        series_title = record["series"]["title"]
        episode_title = record["episode"]["title"]
        episode_quality = record["quality"]["quality"]["name"]
        date = Datetime.ParseDate(record["date"])
        event = record["eventType"]
        episode_id = record["episodeId"]
        if event == "downloadFolderImported":
            summary = L("imported")
            thumb = R("download.png")
        elif event == "downloadFailed":
            summary = L("failed")
            thumb = R("exclamation-triangle.png")
        elif event == "grabbed":
            summary = L("grabbed")
            thumb = R("cloud-download.png")
        elif event == "episodeFileDeleted":
            summary = L("deleted")
            thumb = R("trash-o.png")
        else:
            summary = record["eventType"]
            thumb = R("question-circle.png")
        title = "%s - %dX%02d - %s" % (series_title, season_nbr, episode_nbr, pretty_datetime(date))
        summary = "%s: %s  %s: %s" % (summary, episode_title, L("quality"), episode_quality)
        oc.add(DirectoryObject(key=Callback(episode_options, episode_id=episode_id), title=title, summary=summary,
                               thumb=thumb))
    if page * page_size < r.json()["totalRecords"]:
        oc.add(NextPageObject(key=Callback(history, page=page + 1)))
    return oc


@route("%s/monitor" % PREFIX, monitor_state=bool, season_nbr=int)
def monitor(series_id, monitor_state, season_nbr=-1):
    oc = ObjectContainer()
    thumb = monitor_badge(monitor_state)
    oc.add(DirectoryObject(key=Callback(monitor_set, series_id=series_id, monitor_state=monitor_state,
                                        season_nbr=season_nbr), title="Set Monitoring: %s" % monitor_state,
                           summary=str(L("monitorConfirm")) % monitor_state, thumb=thumb))
    return oc


@route("%s/monitor/set" % PREFIX, monitor_state=bool, season_nbr=int)
def monitor_set(series_id, monitor_state, season_nbr):
    url = Dict["apiUrl"] + "series/%s" % series_id
    Log.Debug("Season: %d" % season_nbr)
    try:
        with requests_cache.disabled():
            r = requests.get(url, headers=Dict["headers"])
            r.raise_for_status()

        url = Dict["apiUrl"] + "series"
        puts = r.json()
        if season_nbr == -1:
            Log.Debug("Toggling at the series level")
            puts["monitored"] = monitor_state
        else:
            Log.Debug("Toggling at the season level")
            for season in puts["seasons"]:
                if season["seasonNumber"] == season_nbr:
                    season["monitored"] = monitor_state
                    break
        with requests_cache.disabled():
            r = requests.put(url, json=puts, headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    return MessageContainer(L("success"), str(L("monitorSet")) % monitor_state)


@route("%s/queue/list" % PREFIX)
def queue():
    url = Dict["apiUrl"] + "queue"
    try:
        with requests_cache.disabled():
            r = requests.get(url, headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    oc = ObjectContainer(title2=L("queue"))
    for e in r.json():
        status = e["status"]
        title = e["title"]
        series_title = e["series"]["title"]
        summary = "Status: {}  Title: {}".format(status, title)
        season_nbr = e["episode"]["seasonNumber"]
        episode_nbr = e["episode"]["episodeNumber"]
        episode_id = e["episode"]["id"]
        header = "%s - %dX%02d" % (series_title, season_nbr, episode_nbr)
        do = DirectoryObject(key=Callback(episode_options, episode_id=episode_id), title=header, summary=summary)
        for coverType in e["series"]["images"]:
            if coverType["coverType"] == "poster":
                do.thumb = Callback(get_thumb, url=coverType["url"])
                break
        oc.add(do)
    return oc


@route("%s/search" % PREFIX, series_id=int, season_id=int, episode_id=int)
def search(series_id=-1, season_id=-1, episode_id=-1):
    url = Dict["apiUrl"] + "command"
    try:
        if not episode_id == -1:
            Log.Info("Episode Search:%d" % episode_id)
            params = {"name": "EpisodeSearch", "episode_ids": [episode_id]}
        elif season_id == -1:
            Log.Info("Series Search:%d" % series_id)
            params = {"name": "SeriesSearch", "seriesId": int(series_id)}
        else:
            Log.Info("Season Search:%d for Series:%d" % (season_id, series_id))
            params = {"name": "SeasonSearch", "seriesId": int(series_id), "seasonNumber": season_id}
        Log.Debug("Command: %s" % url)
        with requests_cache.disabled():
            r = requests.post(url, json=params, headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    return MessageContainer(L("success"), L("search"))


@route("%s/season/delete" % PREFIX)
def season_delete(series_id, season_id):
    url = Dict["apiUrl"] + "episodefile"
    season_nbr = int(season_id)
    try:
        with requests_cache.disabled():
            r = requests.get(url, params={"seriesId": int(series_id)}, headers=Dict["headers"])
            r.raise_for_status()
            for e in r.json():
                if e["seasonNumber"] == season_nbr:
                    Log.Info("Deleting: %d" % e["id"])
                    r = requests.delete(url + "/%s" % e["id"], headers=Dict["headers"])
                    r.raise_for_status()
            url = Dict["apiUrl"] + "series/%s" % series_id
            r = requests.get(url, headers=Dict["headers"])
            r.raise_for_status()
            url = Dict["apiUrl"] + "series"
            puts = r.json()
            for season in puts["seasons"]:
                if season["seasonNumber"] == season_nbr:
                    Log.Info("Unmonitoring S%d for series: %s" % (season_nbr, series_id))
                    season["monitored"] = False
                    break
            r = requests.put(url, json=puts, headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    return MessageContainer(L("success"), L("deleted"))


@route("%s/season/delete/confirm" % PREFIX)
def season_delete_confirm(series_id, season_id):
    oc = ObjectContainer(title2=str(L("season")) % season_id)
    oc.add(DirectoryObject(key=Callback(season_delete, series_id=series_id, season_id=season_id),
                           title=L("confirmDelete"), summary=L("fileWarn"), thumb=R("exclamation-triangle.png")))
    return oc


@route("%s/season/list" % PREFIX)
def seasons(series_id):
    url = Dict["apiUrl"] + "series/%s" % series_id
    try:
        with requests_cache.disabled():
            r = requests.get(url, headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    title = r.json()["title"]
    oc = ObjectContainer(title2=title)
    for season in reversed(r.json()["seasons"]):
        thumb = monitor_badge(season["monitored"])
        season_nbr = season["seasonNumber"]
        season_str = str(L("season")) % season_nbr
        oc.add(DirectoryObject(key=Callback(season_options, series_id=series_id, season_id=season_nbr,
                                            monitored=season["monitored"]), title=season_str, summary=season_str,
                               thumb=thumb))
    return oc


@route("%s/season/options" % PREFIX, monitored=bool)
def season_options(series_id, season_id, monitored):
    oc = ObjectContainer(title2=str(L("season")) % season_id)
    thumb = monitor_badge(monitored)
    oc.add(DirectoryObject(key=Callback(episode, series_id=series_id, season_id=season_id), title=L("listEpisodes"),
                           thumb=R("th-list.png")))
    oc.add(DirectoryObject(key=Callback(monitor, series_id=series_id, monitor_state=(not monitored),
                                        season_nbr=int(season_id)), title=L("toggleMonitor"), thumb=thumb))
    oc.add(DirectoryObject(key=Callback(search, series_id=int(series_id), season_id=int(season_id)),
                           title=L("seasonSearch"), thumb=R("search.png")))
    oc.add(DirectoryObject(key=Callback(season_delete, series_id=series_id, season_id=season_id),
                           title=L("deleteSeason"), thumb=R("trash-o.png")))
    return oc


@route("%s/series/add" % PREFIX, series_payload=dict)
def series_add(series_payload):
    url = Dict["apiUrl"] + "series"
    try:
        with requests_cache.disabled():
            r = requests.post(url, json=series_payload, headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    return MessageContainer(L("success"), L("addSeriesInfo"))


@route("%s/series/delete" % PREFIX)
def series_delete(entity_id):
    url = Dict["apiUrl"] + "series/%s" % entity_id
    try:
        with requests_cache.disabled():
            r = requests.delete(url, params={"deleteFiles": True}, headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    return MessageContainer(L("success"), L("deleted"))


@route("%s/series/delete/confirm" % PREFIX)
def series_delete_confirm(entity_id, title2):
    oc = ObjectContainer(title2=title2)
    oc.add(DirectoryObject(key=Callback(series_delete, entity_id=entity_id), title=L("confirmDelete"),
                           summary=L("fileWarn"), thumb=R("exclamation-triangle.png")))
    return oc


@route("%s/series/list" % PREFIX)
def series():
    url = Dict["apiUrl"] + "series"
    try:
        with requests_cache.disabled():
            r = requests.get(url, headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    oc = ObjectContainer(title2="Series")
    oc.add(InputDirectoryObject(key=Callback(series_lookup), title=L("addSeries"), thumb=R("search.png"),
                                prompt=L("seriesSearch")))
    for s in sorted(r.json(), key=lambda x: x["sortTitle"]):
        title = s["title"]
        series_id = s["id"]
        season_count = s["seasonCount"]
        status = s["status"]
        network = s.get("network", L("unknown"))
        monitored = s["monitored"]
        summary = "{}: {}  {}: {}  {}: {}  {}: {}".format(L("status"), status, L("network"), network, L("monitored"),
                                                          monitored, L("seasons"), season_count)
        do = DirectoryObject(key=Callback(series_options, series_id=series_id, title2=title), title=title,
                             summary=summary)
        for coverType in s["images"]:
            if coverType["coverType"] == "poster":
                do.thumb = Callback(get_thumb, url=Dict["host"] + coverType["url"])
                break
        oc.add(do)
    return oc


@route("%s/series/lookup" % PREFIX)
def series_lookup(query):
    url = Dict["apiUrl"] + "series/lookup"
    try:
        with requests_cache.disabled():
            r = requests.get(url, params={"term": query}, headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    oc = ObjectContainer(title2="Results")
    # Default to first found profile
    with requests_cache.disabled():
        profile = requests.get(Dict["apiUrl"] + "qualityprofile", headers=Dict["headers"]).json()[0]["id"]
        root_folder_path = requests.get(Dict["apiUrl"] + "rootfolder", headers=Dict["headers"]).json()[0]["path"]
    for s in r.json():
        tvdb_id = s["tvdbId"]
        title = s["title"]
        title_slug = s["titleSlug"]
        nbr_seasons = s["seasons"]
        # Default to use season folder.
        season_folder = True
        new_series = {"tvdbId": tvdb_id, "title": title, "profileId": profile, "titleSlug": title_slug,
                      "seasons": nbr_seasons, "seasonFolder": season_folder, "rootFolderPath": root_folder_path}
        network = s.get("network", L("unknown"))
        overview = s.get("overview", L("noInfo"))
        do = DirectoryObject(key=Callback(series_add, series=new_series), title=title,
                             summary="Network: %s Description: %s" % (network, overview))
        if "remotePoster" in s:
            do.thumb = Callback(get_thumb, url=s["remotePoster"])
        oc.add(do)
    return oc


@route("%s/series/options" % PREFIX)
def series_options(series_id, title2):
    url = Dict["apiUrl"] + "series/%s" % series_id
    try:
        with requests_cache.disabled():
            r = requests.get(url, headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    monitored = r.json()["monitored"]
    thumb = monitor_badge(monitored)
    oc = ObjectContainer(title2=title2)
    oc.add(DirectoryObject(key=Callback(seasons, series_id=series_id), title=L("listSeasons"), thumb=R("th-list.png")))
    oc.add(PopupDirectoryObject(key=Callback(monitor, series_id=series_id, monitor_state=(not monitored)),
                                title=L("toggleMonitor"), summary="%s: %s" % (L("monitored"), monitored), thumb=thumb))
    oc.add(DirectoryObject(key=Callback(series_profile, series_id=series_id), title=L("changeQuality"),
                           thumb=R("wrench.png")))
    oc.add(DirectoryObject(key=Callback(search, series_id=int(series_id)), title=L("seriesSearch"),
                           thumb=R("search.png")))
    oc.add(DirectoryObject(key=Callback(series_delete_confirm, entity_id=series_id, title2=title2),
                           title=L("deleteSeries"), thumb=R("trash-o.png")))
    return oc


@route("%s/series/profile" % PREFIX)
def series_profile(series_id):
    url = Dict["apiUrl"] + "series/%s" % series_id
    try:
        with requests_cache.disabled():
            r = requests.get(url, headers=Dict["headers"])
            r.raise_for_status()
            s = r.json()
            url = Dict["apiUrl"] + "qualityprofile"
            r = requests.get(url, headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    oc = ObjectContainer(title2=L("quality"))
    for profile in r.json():
        title = profile["name"]
        quality_id = profile["id"]
        if quality_id == s["profileId"]:
            title += L("current")
            thumb = R("square.png")
        else:
            thumb = R("circle-o.png")
        oc.add(DirectoryObject(key=Callback(series_profile_set, series_id=series_id, quality_id=quality_id),
                               title=title, summary="%s: %s" % (L("cutOff"), profile["cutoff"]["name"]), thumb=thumb))
    return oc


@route("%s/series/profile/set" % PREFIX, quality_id=int)
def series_profile_set(series_id, quality_id):
    url = Dict["apiUrl"] + "series/%s" % series_id
    try:
        with requests_cache.disabled():
            r = requests.get(url, headers=Dict["headers"])
            r.raise_for_status()
            s = r.json()
            s["profileId"] = quality_id
            url = Dict["apiUrl"] + "series"
            r = requests.put(url, json=s, headers=Dict["headers"])
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    return MessageContainer(L("success"), L("saved"))


@route("%s/thumb" % PREFIX)
def get_thumb(url, content_type="image/jpeg", timeout=10, use_cache=True):
    try:
        if not use_cache:
            with requests_cache.disabled():
                data = requests.get(url, timeout=timeout)
        else:
            data = requests.get(url, timeout=timeout)
        Log.Debug("thumb from_cache: %s" % data.from_cache)
    except Exception as e:
        Log.Critical(e.message)
        return DataObject(Resource.Load("question-circle.png", binary=True), "image/png")
    return DataObject(data.content, content_type)


@route("%s/wanted/list" % PREFIX, page=int, page_size=int)
def wanted(page=1, page_size=19):
    oc = ObjectContainer(title2="Wanted")

    url = Dict["apiUrl"] + "missing"
    try:
        with requests_cache.disabled():
            r = requests.get(url,
                             params={"page": page, "pageSize": page_size, "sortKey": "date", "sortDir": "desc"},
                             headers=Dict["headers"], verify=False)
            r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)

    for record in r.json()["records"]:
        season_nbr = record["seasonNumber"]
        episode_nbr = record["episodeNumber"]
        series_title = record["series"]["title"]
        date = Datetime.ParseDate(record["airDateUtc"])
        episode_id = record["id"]
        title = "%s - %dX%02d - %s" % (series_title, season_nbr, episode_nbr, pretty_datetime(date))
        episode_title = record["title"]
        summary = "%s" % episode_title
        do = DirectoryObject(key=Callback(episode_options, episode_id=episode_id), title=title, summary=summary)
        for coverType in record["series"]["images"]:
            if coverType["coverType"] == "poster":
                do.thumb = Callback(get_thumb, url=coverType["url"])
                break
        oc.add(do)
    if page * page_size < r.json()["totalRecords"]:
        oc.add(NextPageObject(key=Callback(wanted, page=page + 1)))
    return oc


def pretty_datetime(d):
    now = Datetime.Now()
    dt = d.replace(tzinfo=None) + Dict["utc_offset"]
    diff = now - dt
    s = diff.seconds
    # Future
    if dt > now:
        if now.day == dt.day:
            pretty = dt.strftime(str(L("today") + "%I:%M%p"))
        elif (now + Datetime.Delta(days=1)).day == dt.day:
            pretty = dt.strftime(str(L("tomorrow")) + "%I:%M%p")
        else:
            pretty = dt.strftime("%a %I:%M%p")
    # Past
    else:
        if diff.days > 7:
            pretty = dt.strftime("%d %b %Y")
        elif diff.days > 1:
            pretty = str(diff.days) + str(L("daysago"))
        elif diff.days == 1:
            pretty = str(L("yesterday"))
        elif s < 3600:
            pretty = str(s / 60) + str(L("minutesago"))
        elif s < 7200:
            pretty = str(L("hourago"))
        else:
            pretty = str(s / 3600) + str(L("hoursago"))
    return pretty


def monitor_badge(is_monitored):
    if is_monitored:
        return R("bookmark.png")
    else:
        return R("bookmark-o.png")


def timestamp(time=datetime.utcnow()):
    """ Convert a datetime to ISO-8601 formatted in UTC to send to Sonarr """
    return str(time.isoformat("T")).split(".")[0] + "Z"
