# from mock_framework import *
from datetime import datetime
import requests

PREFIX = "/video/sonarr"
NAME = "Sonarr"


def Start():
    global utc_offset, S
    requests.packages.urllib3.disable_warnings()
    ObjectContainer.art = R("logo.png")
    ObjectContainer.title1 = NAME
    ObjectContainer.title2 = NAME
    DirectoryObject.thumb = R("question-circle.png")
    local_hour = Datetime.Now().replace(minute=0, second=0, microsecond=0)
    utc_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0, tzinfo=None)
    utc_offset = local_hour - utc_hour
    Log.Debug("UTC Offset: %s" % utc_offset)
    S = lambda x: str(L(x))
    ValidatePrefs()


def ValidatePrefs():
    global endpoint, apiUrl, headers, auth, request_options
    endpoint = "{}://{}:{}".format("https" if Prefs["https"] else "http", Prefs["ip"], Prefs["port"])
    apiUrl = "{}/api/".format(endpoint + Prefs["base"])
    headers = {"X-Api-Key": Prefs["apiKey"]}
    if Prefs["auth"] == "None":
        auth = None
    elif Prefs["auth"] == "Basic":
        auth = requests.auth.HTTPBasicAuth(Prefs["username"], Prefs["password"])
    else:
        auth = requests.auth.HTTPDigestAuth(Prefs["username"], Prefs["password"])
    request_options = {"headers": headers, "auth": auth, "verify": False, "timeout": 60}
    Log.Debug("Endpoint url: %s" % endpoint)
    Log.Debug("API Url: %s" % apiUrl)


@handler(PREFIX, NAME, "1024.png", "logo.png")
def main_menu():
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(series), title=S("series"), summary=S("seriesInfo"), thumb=R("play.png")))
    oc.add(DirectoryObject(key=Callback(calendar), title=S("calendar"), summary=S("calendarInfo"),
                           thumb=R("calendar.png")))
    oc.add(DirectoryObject(key=Callback(queue), title=S("queue"), summary=S("queueInfo"), thumb=R("cloud.png")))
    oc.add(DirectoryObject(key=Callback(history), title=S("history"), summary=S("historyInfo"), thumb=R("history.png")))
    oc.add(DirectoryObject(key=Callback(wanted), title=S("missing"), summary=S("missingInfo"),
                           thumb=R("exclamation-triangle.png")))
    oc.add(PrefsObject(title=S("settings"), summary=S("settingsInfo"),
                       thumb=R("cogs.png")))
    return oc


@route("%s/calendar/list" % PREFIX)
def calendar():
    start = timestamp(datetime.utcnow() - Datetime.Delta(hours=6))
    end = timestamp(datetime.utcnow() + Datetime.Delta(weeks=2))

    url = apiUrl + "calendar"
    try:
        r = requests.get(url, params={"start": start, "end": end}, **request_options)
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)

    oc = ObjectContainer(title2=S("calendar"))
    for e in r.json():
        season_nbr = e["seasonNumber"]
        episode_nbr = e["episodeNumber"]
        episode_id = e["id"]
        dt = Datetime.ParseDate(e["airDateUtc"])
        episode_title = e["title"]
        episode_overview = e.get("overview", S("noInfo"))
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
    url = apiUrl + "episode"
    try:
        r = requests.get(url, params={"seriesId": series_id}, **request_options)
        # r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)
    request = r.json()
    current_season = "Season " + season_id
    oc = ObjectContainer(title2=current_season)
    # for e in reversed(request):
    # for e in reversed(request):
    for e in sorted(request, key=lambda x: x["episodeNumber"], reverse=True):
        season_nbr = str(e["seasonNumber"])
        if not season_nbr == season_id:
            continue
        thumb = monitor_badge(e["monitored"])
        episode_nbr = e["episodeNumber"]
        title = "%02d" % episode_nbr
        if e["hasFile"]:
            title += u"\u2713"
        title += " " + e["title"]

        summary = e.get("overview", S("noInfo"))
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
                           summary=S("monitorConfirm") % monitor_state, thumb=thumb))
    return oc


@route("%s/episode/monitor/set" % PREFIX, episode_id=int, monitor_state=bool)
def episode_monitor_set(episode_id, monitor_state):
    url = apiUrl + "episode/%s" % episode_id
    Log.Debug("Episode: %d" % episode_id)
    try:
        r = requests.get(url, **request_options)
        # r.raise_for_status()
        url = apiUrl + "episode"
        puts = r.json()
        puts["monitored"] = monitor_state
        requests.put(url, json=puts, **request_options)
        # r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)
    return MessageContainer(S("success"), S("monitorSet") % monitor_state)


@route("%s/episode/options" % PREFIX)
def episode_options(episode_id):
    url = apiUrl + "episode/%s" % episode_id
    try:
        r = requests.get(url, **request_options)
        # r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)
    e = r.json()
    title = e["title"]
    episode_id = e["id"]
    monitored = e["monitored"]
    thumb = monitor_badge(monitored)
    oc = ObjectContainer(title2=title)
    oc.add(DirectoryObject(key=Callback(episode_monitor, episode_id=episode_id, monitor_state=(not monitored)),
                           title=S("toggleMonitor"), thumb=thumb))
    oc.add(DirectoryObject(key=Callback(search, episode_id=int(episode_id)), title=S("episodeSearch"),
                           summary=S("episodeSearchInfo"), thumb=R("search.png")))
    return oc


@route("%s/history/list" % PREFIX, page=int, page_size=int)
def history(page=1, page_size=19):
    url = apiUrl + "history"
    try:
        r = requests.get(url, params={"page": page, "pageSize": page_size, "sortKey": "date", "sortDir": "desc"},
                         **request_options)
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)
    oc = ObjectContainer(title2=S("history"))
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
            summary = S("imported")
            thumb = R("download.png")
        elif event == "downloadFailed":
            summary = S("failed")
            thumb = R("exclamation-triangle.png")
        elif event == "grabbed":
            summary = S("grabbed")
            thumb = R("cloud-download.png")
        elif event == "episodeFileDeleted":
            summary = S("deleted")
            thumb = R("trash-o.png")
        else:
            summary = record["eventType"]
            thumb = R("question-circle.png")
        title = "%s - %dX%02d - %s" % (series_title, season_nbr, episode_nbr, pretty_datetime(date))
        summary = "%s: %s  %s: %s" % (summary, episode_title, S("quality"), episode_quality)
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
                           summary=S("monitorConfirm") % monitor_state, thumb=thumb))
    return oc


@route("%s/monitor/set" % PREFIX, monitor_state=bool, season_nbr=int)
def monitor_set(series_id, monitor_state, season_nbr):
    url = apiUrl + "series/%s" % series_id
    Log.Debug("Season: %d" % season_nbr)
    try:
        r = requests.get(url, **request_options)
        # r.raise_for_status()

        url = apiUrl + "series"
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
        requests.put(url, json=puts, **request_options)
        # r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)
    return MessageContainer(S("success"), S("monitorSet") % monitor_state)


@route("%s/queue/list" % PREFIX)
def queue():
    url = apiUrl + "queue"
    try:
        r = requests.get(url, **request_options)
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)
    oc = ObjectContainer(title2=S("queue"))
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
    url = apiUrl + "command"
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
        requests.post(url, json=params, **request_options)
        # r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)
    return MessageContainer(S("success"), S("searchResponse"))


@route("%s/season/delete" % PREFIX)
def season_delete(series_id, season_id):
    url = apiUrl + "episodefile"
    season_nbr = int(season_id)
    try:
        r = requests.get(url, params={"seriesId": int(series_id)}, **request_options)
        # r.raise_for_status()
        for e in r.json():
            if e["seasonNumber"] == season_nbr:
                Log.Info("Deleting: %d" % e["id"])
                requests.delete(url + "/%s" % e["id"], **request_options)
                # r.raise_for_status()
        url = apiUrl + "series/%s" % series_id
        r = requests.get(url, **request_options)
        # r.raise_for_status()
        url = apiUrl + "series"
        puts = r.json()
        for season in puts["seasons"]:
            if season["seasonNumber"] == season_nbr:
                Log.Info("Unmonitoring S%d for series: %s" % (season_nbr, series_id))
                season["monitored"] = False
                break
        requests.put(url, json=puts, **request_options)
        # r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)
    return MessageContainer(S("success"), S("deleted"))


@route("%s/season/delete/confirm" % PREFIX)
def season_delete_confirm(series_id, season_id):
    oc = ObjectContainer(title2=S("season") % season_id)
    oc.add(DirectoryObject(key=Callback(season_delete, series_id=series_id, season_id=season_id),
                           title=S("confirmDelete"), summary=S("fileWarn"), thumb=R("exclamation-triangle.png")))
    return oc


@route("%s/season/list" % PREFIX)
def seasons(series_id):
    url = apiUrl + "series/%s" % series_id
    try:
        r = requests.get(url, **request_options)
        # r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)
    title = r.json()["title"]
    oc = ObjectContainer(title2=title)
    for season in reversed(r.json()["seasons"]):
        thumb = monitor_badge(season["monitored"])
        season_nbr = str(season["seasonNumber"])
        season_str = S("season") % season_nbr
        oc.add(DirectoryObject(key=Callback(season_options, series_id=series_id, season_id=season_nbr,
                                            monitored=season["monitored"]), title=season_str, summary=season_str,
                               thumb=thumb))
    return oc


@route("%s/season/options" % PREFIX, monitored=bool)
def season_options(series_id, season_id, monitored):
    oc = ObjectContainer(title2=S("season") % season_id)
    thumb = monitor_badge(monitored)
    oc.add(DirectoryObject(key=Callback(episode, series_id=series_id, season_id=season_id), title=S("listEpisodes"),
                           thumb=R("th-list.png")))
    oc.add(DirectoryObject(key=Callback(monitor, series_id=series_id, monitor_state=(not monitored),
                                        season_nbr=int(season_id)), title=S("toggleMonitor"), thumb=thumb))
    oc.add(DirectoryObject(key=Callback(search, series_id=int(series_id), season_id=int(season_id)),
                           title=S("seasonSearch"), thumb=R("search.png")))
    oc.add(DirectoryObject(key=Callback(season_delete, series_id=series_id, season_id=season_id),
                           title=S("deleteSeason"), thumb=R("trash-o.png")))
    return oc


@route("%s/series/add" % PREFIX, series_payload=dict)
def series_add(series_payload):
    url = apiUrl + "series"
    try:
        Log.Debug("Payload: %s" % series_payload)
        requests.post(url, json=series_payload, **request_options)
        # r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)
    return MessageContainer(S("success"), S("addSeriesInfo"))


@route("%s/series/delete" % PREFIX)
def series_delete(entity_id):
    url = apiUrl + "series/%s" % entity_id
    try:
        Log.Debug("%s %s" % (url, Prefs["delete_files"]))
        requests.delete(url, params={"deleteFiles": Prefs["delete_files"]}, **request_options)
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)
    return MessageContainer(S("success"), S("deleted"))


@route("%s/series/delete/confirm" % PREFIX)
def series_delete_confirm(entity_id, title2):
    oc = ObjectContainer(title2=title2)
    oc.add(DirectoryObject(key=Callback(series_delete, entity_id=entity_id), title=S("confirmDelete"),
                           summary=S("fileWarn"), thumb=R("exclamation-triangle.png")))
    return oc


@route("%s/series/list" % PREFIX)
def series():
    url = apiUrl + "series"
    try:
        r = requests.get(url, **request_options)
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)
    oc = ObjectContainer(title2="Series")
    oc.add(InputDirectoryObject(key=Callback(series_lookup), title=S("addSeries"), summary=S("addSeriesSummary"),
                                thumb=R("search.png"), prompt=S("search")))
    for s in sorted(r.json(), key=lambda x: x["sortTitle"]):
        title = s["title"]
        series_id = s["id"]
        status = s["status"]
        network = s.get("network", S("unknown"))
        summary = "{}: {}  {}: {}".format(S("network"), network, S("status"), status)
        do = DirectoryObject(key=Callback(series_options, series_id=series_id, title2=title), title=title,
                             summary=summary)
        for coverType in s["images"]:
            if coverType["coverType"] == "poster":
                do.thumb = Callback(get_thumb, url=endpoint + coverType["url"])
                break
        oc.add(do)
    return oc


@route("%s/series/lookup" % PREFIX)
def series_lookup(query):
    url = apiUrl + "series/lookup"
    try:
        r = requests.get(url, params={"term": query}, **request_options)
        # r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)
    oc = ObjectContainer(title2="Results")
    # Default to first found profile
    profile = requests.get(apiUrl + "profile", **request_options).json()[0]["id"]
    root_folder_path = requests.get(apiUrl + "rootfolder", **request_options).json()[0]["path"]
    for s in r.json():
        tvdb_id = s["tvdbId"]
        title = s["title"]
        title_slug = s["titleSlug"]
        nbr_seasons = s["seasons"]
        season_folder = Prefs["season_folder"]
        new_series = {"tvdbId": tvdb_id, "title": title, "profileId": profile, "titleSlug": title_slug,
                      "seasons": nbr_seasons, "seasonFolder": season_folder, "rootFolderPath": root_folder_path}
        network = s.get("network", S("unknown"))
        overview = s.get("overview", S("noInfo"))
        do = DirectoryObject(key=Callback(series_add, series_payload=new_series), title=title,
                             summary="Network: %s Description: %s" % (network, overview))
        if "remotePoster" in s:
            do.thumb = Callback(get_thumb, url=s["remotePoster"])
        oc.add(do)
    return oc


@route("%s/series/options" % PREFIX)
def series_options(series_id, title2):
    url = apiUrl + "series/%s" % series_id
    try:
        r = requests.get(url, **request_options)
        # r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)
    monitored = r.json()["monitored"]
    thumb = monitor_badge(monitored)
    oc = ObjectContainer(title2=title2)
    oc.add(DirectoryObject(key=Callback(seasons, series_id=series_id), title=S("listSeasons"), thumb=R("th-list.png")))
    oc.add(PopupDirectoryObject(key=Callback(monitor, series_id=series_id, monitor_state=(not monitored)),
                                title=S("toggleMonitor"), summary="%s: %s" % (S("monitored"), monitored), thumb=thumb))
    oc.add(DirectoryObject(key=Callback(series_profile, series_id=series_id), title=S("changeQuality"),
                           thumb=R("wrench.png")))
    oc.add(DirectoryObject(key=Callback(search, series_id=int(series_id)), title=S("seriesSearch"),
                           thumb=R("search.png")))
    oc.add(DirectoryObject(key=Callback(series_delete_confirm, entity_id=series_id, title2=title2),
                           title=S("deleteSeries"), thumb=R("trash-o.png")))
    return oc


@route("%s/series/profile" % PREFIX)
def series_profile(series_id):
    url = apiUrl + "series/%s" % series_id
    try:
        r = requests.get(url, **request_options)
        # r.raise_for_status()
        s = r.json()
        url = apiUrl + "profile"
        r = requests.get(url, **request_options)
        # r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)
    oc = ObjectContainer(title2=S("quality"))
    for profile in r.json():
        title = profile["name"]
        quality_id = profile["id"]
        if quality_id == s["profileId"]:
            title += S("current")
            thumb = R("square.png")
        else:
            thumb = R("circle-o.png")
        oc.add(DirectoryObject(key=Callback(series_profile_set, series_id=series_id, quality_id=quality_id),
                               title=title, summary="%s: %s" % (S("cutOff"), profile["cutoff"]["name"]), thumb=thumb))
    return oc


@route("%s/series/profile/set" % PREFIX, quality_id=int)
def series_profile_set(series_id, quality_id):
    url = apiUrl + "series/%s" % series_id
    try:
        r = requests.get(url, **request_options)
        # r.raise_for_status()
        s = r.json()
        s["profileId"] = quality_id
        url = apiUrl + "series"
        requests.put(url, json=s, **request_options)
        # r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)
    return MessageContainer(S("success"), S("saved"))


@route("%s/thumb" % PREFIX)
def get_thumb(url, content_type="image/jpeg"):
    try:
        data = requests.get(url, **request_options)
    except Exception as e:
        Log.Critical(e.message)
        return DataObject(Resource.Load("question-circle.png", binary=True), "image/png")
    return DataObject(data.content, content_type)


@route("%s/wanted/list" % PREFIX, page=int, page_size=int)
def wanted(page=1, page_size=19):
    oc = ObjectContainer(title2="Wanted")

    url = apiUrl + "missing"
    try:
        r = requests.get(url, params={"page": page, "pageSize": page_size, "sortKey": "airDate", "sortDir": "desc"},
                         **request_options)
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(S("error"), e.message)

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
    dt = d.replace(tzinfo=None) + utc_offset
    diff = now - dt
    # Future
    if dt > now:
        if now.day == dt.day:
            pretty = dt.strftime(S("today") + "%I:%M%p")
        elif (now + Datetime.Delta(days=1)).day == dt.day:
            pretty = dt.strftime(S("tomorrow") + "%I:%M%p")
        else:
            pretty = dt.strftime("%a %I:%M%p")
    # Past
    else:
        s = diff.seconds
        if diff.days > 7:
            pretty = dt.strftime("%d %b %Y")
        elif diff.days > 1:
            pretty = str(diff.days) + S("daysago")
        elif diff.days == 1:
            pretty = S("yesterday")
        elif s < 3600:
            pretty = str(s / 60) + S("minutesago")
        else:
            pretty = str(s / 3600) + S("hoursago")
    return pretty


def monitor_badge(is_monitored):
    if is_monitored:
        return R("bookmark.png")
    else:
        return R("bookmark-o.png")


def timestamp(time=datetime.utcnow()):
    """ Convert a datetime to ISO-8601 formatted in UTC to send to Sonarr """
    return str(time.isoformat("T")).split(".")[0] + "Z"
