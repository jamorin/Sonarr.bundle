from datetime import datetime
import requests

PREFIX  = '/video/sonarr'
NAME   = 'Sonarr'

def Start():
    #requests.packages.urllib3.disable_warnings()
    ObjectContainer.art    = R('logo.png')
    ObjectContainer.title1 = NAME
    ObjectContainer.title2 = NAME
    DirectoryObject.thumb  = R('question-circle.png')
    Dict['utcOffset'] = Datetime.Now().replace(minute=0, second=0,
        microsecond=0) - datetime.utcnow().replace(minute=0, second=0,
        microsecond=0, tzinfo=None)
    Log.Debug('UTC Offset: %s' % Dict['utcOffset'])
    ValidatePrefs()
    #HTTP.ClearCache()

@handler(PREFIX, NAME, '1024.png', 'logo.png')
def MainMenu():
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(Series), title=L('series'),
        summary = L('seriesInfo'),  thumb=R('play.png')))
    oc.add(DirectoryObject(key=Callback(Calendar), title=L('calendar'),
        summary = L("calendarInfo"), thumb=R('calendar.png')))
    oc.add(DirectoryObject(key=Callback(Queue), title=L('queue'),
        summary = L("queueInfo"), thumb=R('cloud.png')))
    oc.add(DirectoryObject(key=Callback(History), title=L('history'),
        summary = L('historyInfo'), thumb=R('history.png')))
    oc.add(DirectoryObject(key=Callback(Wanted), title=L('missing'),
        summary = L('missingInfo'), thumb=R('exclamation-triangle.png')))
    oc.add(PrefsObject(title=L('settings'), summary=L('settingsInfo'),
        thumb=R('cogs.png')))
    return oc

def ValidatePrefs():
    Dict['host']  = '{}://{}:{}'.format('http', Prefs['ip'], Prefs['port'])
    Dict['apiUrl'] = "{}/api/".format(Dict['host']+Prefs['base'])
    Dict['headers'] = {'X-Api-Key': Prefs['apiKey']}
    Log.Debug('Sonarr url: %s' % Dict['host'])
    Log.Debug('API Url: %s' % Dict['apiUrl'])

@route('%s/series' % PREFIX)
def Series():
    url = Dict['apiUrl']+'series'
    try:
        r = requests.get(url, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L('error'), e.message)
    oc = ObjectContainer(title2="Series")
    oc.add(InputDirectoryObject(key=Callback(SeriesSearch), title=L("addSeries"),
        thumb=R("search-plus.png"), prompt=L("seriesSearch")))
    for series in sorted(r.json(), key=lambda x: x['sortTitle']):
        title = series['title']
        seriesId = series['id']
        seasons = series['seasonCount']
        status = series['status']
        network = series['network']
        monitored = series['monitored']
        summary = "{}: {}  {}: {}  {}: {}  {}: {}".format(L('status'), status,
            L('network'), network, L('monitored'), monitored, L('seasons'), seasons)
        dirObj = DirectoryObject(key=Callback(SeriesOptions, seriesId=seriesId,
            title2=title), title=title, summary=summary)
        for coverType in series['images']:
            if coverType['coverType'] == "poster":
                dirObj.thumb=Callback(GetThumb, url=Dict['host']+coverType['url'])
                break
        oc.add(dirObj)
    return oc

@route('%s/series/search' % PREFIX)
def SeriesSearch(query):
    url = Dict['apiUrl']+'series/lookup'
    try:
        r = requests.get(url, params={'term': query}, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L('error'), e.message)
    oc = ObjectContainer(title2='Results')
    # Default to first found profile
    profile = requests.get(Dict['apiUrl']+'qualityprofile',
        headers=Dict['headers']).json()[0]['id']
    rootFolderPath = requests.get(Dict['apiUrl']+'rootfolder',
        headers=Dict['headers']).json()[0]['path']
    for series in r.json():
        title = '%s (%s)' % (series['title'], series['year'])
        tvdbId = series['tvdbId']
        title = series['title']
        titleSlug = series['titleSlug']
        seasons = series['seasons']
        # Default to use season folder.
        seasonFolder = True
        newSeries = {'tvdbId': tvdbId, 'title': title, 'profileId': profile,
            'titleSlug': titleSlug, 'seasons': seasons, 'seasonFolder': seasonFolder,
            'rootFolderPath': rootFolderPath}
        overview = L("noInfo")
        network = L("unknown")
        if 'overview' in series:
            overview = series['overview']
        if 'network' in series:
            network = series['network']
        dirObj = DirectoryObject(key=Callback(AddSeries, series=newSeries),
            title=title, summary='Network: %s Description: %s' % (network, overview))
        if 'remotePoster' in series:
            dirObj.thumb=Callback(GetThumb, url=series['remotePoster'])
        oc.add(dirObj)
    if not len(oc):
        return MessageContainer(L("status"), L("noResults"))
    return oc

@route('%s/series/add' % PREFIX, series=dict)
def AddSeries(series):
    url = Dict['apiUrl'] + 'series'
    try:
        r = requests.post(url, json=series, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L('error'), e.message)
    return MessageContainer(L('success'), L('addSeriesInfo'))

@route('%s/queue' % PREFIX)
def Queue():
    url = Dict['apiUrl']+'queue'
    try:
        r = requests.get(url, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L('error'), e.message)
    oc = ObjectContainer(title2=L('queue'))
    for episode in r.json():
        status = episode['status']
        title = episode['title']
        seriesTitle = episode['series']['title']
        episodeTitle = episode['episode']['title']
        summary = "Status: {}  Title: {}".format(status, title)
        seasonNbr = episode['episode']['seasonNumber']
        episodeNbr = episode['episode']['episodeNumber']
        episodeId = episode['episode']['id']
        header ="%s - %dX%02d" % (seriesTitle, seasonNbr, episodeNbr)
        dirObj = DirectoryObject(key=Callback(EpisodeOptions,
            episodeId=episodeId), title=header, summary=summary)
        for coverType in episode['series']['images']:
            if coverType['coverType'] == "poster":
                dirObj.thumb=Callback(GetThumb, url=coverType['url'])
                break
        oc.add(dirObj)
    if not len(oc):
        return MessageContainer(L("empty"), L("noResults"))
    return oc

@route('%s/history' % PREFIX, page=int, pageSize=int)
def History(page=1, pageSize=19):
    url = Dict['apiUrl']+'history'
    try:
        r = requests.get(url, params={'page': page, 'pageSize': pageSize,
            'sortKey': 'date', 'sortDir': 'desc'}, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L('error'), e.message)
    oc = ObjectContainer(title2=L('history'))
    for record in r.json()['records']:
        seasonNbr = record['episode']['seasonNumber']
        episodeNbr = record['episode']['episodeNumber']
        seriesTitle = record['series']['title']
        episodeTitle = record['episode']['title']
        episodeQuality = record['quality']['quality']['name']
        date = Datetime.ParseDate(record['date'])
        event = record['eventType']
        episodeId = record['episodeId']
        if event == "downloadFolderImported":
            summary = L('imported')
            thumb = R('download.png')
        elif event == "downloadFailed":
            summary = L('failed')
            thumb = R('exclamation-triangle.png')
        elif event == "grabbed":
            summary = L('grabbed')
            thumb = R('cloud-download.png')
        elif event == "episodeFileDeleted":
            summary = L('deleted')
            thumb = R('trash-o.png')
        else:
            summary = record['eventType']
            thumb = R('question-circle.png')
        title="%s - %dX%02d - %s" % (seriesTitle, seasonNbr, episodeNbr,
            PrettyDate(date))
        summary = "%s: %s  %s: %s" % (summary, episodeTitle, L('quality'),
            episodeQuality)
        oc.add(DirectoryObject(key=Callback(EpisodeOptions, episodeId=episodeId),
            title=title, summary=summary, thumb=thumb))
    if not len(oc):
        return MessageContainer(L('history'), L('noResults'))
    if page*pageSize < r.json()['totalRecords']:
        oc.add(NextPageObject(key=Callback(History, page=page+1)))
    return oc

@route('%s/series/options' % PREFIX)
def SeriesOptions(seriesId, title2):
    url = Dict['apiUrl']+'series/%s' % seriesId
    try:
        r = requests.get(url, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L('error'), e.message)
    monitored = r.json()['monitored']
    thumb = Monitored(monitored)
    oc = ObjectContainer(title2=title2)
    oc.add(DirectoryObject(key=Callback(Seasons, seriesId=seriesId),
        title=L('listSeasons'), thumb=R('th-list.png')))
    oc.add(PopupDirectoryObject(key=Callback(Monitor, seriesId=seriesId,
        setMonitor=(not monitored)), title=L("toggleMonitor"),
        summary='%s: %s' % (L('monitored'), monitored), thumb=thumb))
    oc.add(DirectoryObject(key=Callback(QualityProfile, seriesId=seriesId),
        title=L("changeQuality"), thumb=R('wrench.png')))
    oc.add(DirectoryObject(key=Callback(CommandSearch, seriesId=int(seriesId)),
        title=L("seriesSearch"), thumb=R('search.png')))
    oc.add(DirectoryObject(key=Callback(DeleteSeriesPopup, entityId=seriesId,
        title2=title2), title=L("deleteSeries"), thumb=R('trash-o.png')))
    return oc

@route('%s/delete/popup' % PREFIX)
def DeleteSeriesPopup(entityId, title2):
    oc = ObjectContainer(title2=title2)
    oc.add(DirectoryObject(key=Callback(DeleteSeries, entityId=entityId),
        title=L("confirmDelete"), summary=L("fileWarn"), thumb=R('exclamation-triangle.png')))
    return oc

@route('%s/delete/execute' % PREFIX)
def DeleteSeries(entityId):
    url = Dict['apiUrl']+'series/%s' % entityId
    try:
        r = requests.delete(url, json={'deleteFiles': True }, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L('error'), e.message)
    return MessageContainer(L("success"), L("deleted"))

@route('%s/qualityprofile' % PREFIX)
def QualityProfile(seriesId):
    url = Dict['apiUrl']+'series/%s' % seriesId
    try:
        r = requests.get(url, headers=Dict['headers'])
        r.raise_for_status()
        series = r.json()

        url = Dict['apiUrl']+'qualityprofile'
        r = requests.get(url, headers=Dict['headers'])
        r.raise_for_status()
        profiles = r.json()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    oc = ObjectContainer(title2=L("quality"))
    for profile in profiles:
        title = profile['name']
        qualityId = profile['id']
        if qualityId == series['profileId']:
            title += L("current")
            thumb = R('square.png')
        else:
            thumb = R('circle-o.png')
        oc.add(DirectoryObject(key=Callback(QualityProfileSet, seriesId=seriesId,
            qualityId=qualityId), title=title,
            summary="%s: %s" % (L("cutOff"), profile['cutoff']['name']), thumb=thumb))
    if not len(oc):
        return MessageContainer(L("quality"), L("noResults"))
    return oc

@route('%s/qualityprofile/set' % PREFIX, qualityId=int)
def QualityProfileSet(seriesId, qualityId):
    url = Dict['apiUrl']+'series/%s' % seriesId
    try:
        r = requests.get(url, headers=Dict['headers'])
        r.raise_for_status()
        series = r.json()
        series['profileId'] = qualityId
        url = Dict['apiUrl']+'series'
        r = requests.put(url, json=series, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    return MessageContainer(L("success"), L("saved"))

@route('%s/monitor/popup' % PREFIX, setMonitor=bool, seasonNbr=int)
def Monitor(seriesId, setMonitor, seasonNbr=-1):
    oc = ObjectContainer()
    thumb = Monitored(setMonitor)
    oc.add(DirectoryObject(key=Callback(MonitorToggle, seriesId=seriesId,
        setMonitor=setMonitor, seasonNbr=seasonNbr), title='Set Monitoring: %s' % setMonitor,
        summary=str(L("monitorConfirm")) % setMonitor, thumb=thumb))
    return oc

@route('%s/monitor/toggle' % PREFIX, setMonitor=bool, seasonNbr=int)
def MonitorToggle(seriesId, setMonitor, seasonNbr):
    oc = ObjectContainer()
    url = Dict['apiUrl']+'series/%s' % seriesId
    Log.Debug('Season: %d' % seasonNbr)
    try:
        r = requests.get(url, headers=Dict['headers'])
        r.raise_for_status()

        url = Dict['apiUrl']+'series'
        puts = r.json()
        if seasonNbr == -1:
            Log.Debug('Toggling at the series level')
            puts['monitored'] = setMonitor
        else:
            Log.Debug('Toggling at the season level')
            for season in puts['seasons']:
                if season["seasonNumber"] == seasonNbr:
                    season['monitored'] = setMonitor
                    break
        r = requests.put(url, json=puts, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    return MessageContainer(L("success"), str(L("monitorSet")) % setMonitor)

@route('%s/series/seasons' % PREFIX)
def Seasons(seriesId):
    url = Dict['apiUrl']+'series/%s' % seriesId
    try:
        r = requests.get(url, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    title = r.json()['title']
    oc = ObjectContainer(title2=title)
    for season in reversed(r.json()["seasons"]):
        thumb = Monitored(season["monitored"])
        seasonNbr = season["seasonNumber"]
        seasonStr = str(L("season")) % seasonNbr
        oc.add(DirectoryObject(key=Callback(SeasonsOptions, seriesId=seriesId,
            seasonId=seasonNbr, monitored=season["monitored"]), title=seasonStr,
                summary=seasonStr, thumb=thumb))
    if not len(oc):
        return MessageContainer(title, L("noResults"))
    return oc

@route('%s/series/seasons/options' % PREFIX, monitored=bool)
def SeasonsOptions(seriesId, seasonId, monitored):
    oc = ObjectContainer(title2=str(L("season")) % seasonId)
    thumb = Monitored(monitored)
    oc.add(DirectoryObject(key=Callback(Episodes, seriesId=seriesId, seasonId=seasonId),
        title=L("listEpisodes"), thumb=R('th-list.png')))
    oc.add(DirectoryObject(key=Callback(Monitor, seriesId=seriesId,
        setMonitor=(not monitored), seasonNbr=int(seasonId)),
        title=L("toggleMonitor"), thumb=thumb))
    oc.add(DirectoryObject(key=Callback(CommandSearch, seriesId=int(seriesId),
        seasonId=int(seasonId)), title=L("seasonSearch"), thumb=R('search.png')))
    oc.add(DirectoryObject(key=Callback(DeleteSeasonPopup, seriesId=seriesId,
        seasonId=seasonId), title=L('deleteSeason'), thumb=R('trash-o.png')))
    return oc

@route('%s/command/search' % PREFIX, seriesId=int, seasonId=int, episodeId=int)
def CommandSearch(seriesId=-1, seasonId=-1, episodeId=-1):
    url = Dict['apiUrl']+'command'
    try:
        if not episodeId == -1:
            Log.Info('Episode Search:%d' % episodeId)
            params = {'name': 'EpisodeSearch', 'episodeIds': [episodeId]}
        elif seasonId == -1:
            Log.Info('Series Search:%d' % seriesId)
            params = {'name': 'SeriesSearch', 'seriesId': int(seriesId)}
        else:
            Log.Info('Season Search:%d for Series:%d' % (seasonId, seriesId))
            params = {'name': 'SeasonSearch', 'seriesId': int(seriesId),
                'seasonNumber': seasonId}
        Log.Debug('Command: %s' % url)
        r = requests.post(url, json=params, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L('error'), e.message)
    return MessageContainer(L("success"), L("search"))

@route("%s/delete/season/popup" % PREFIX)
def DeleteSeasonPopup(seriesId, seasonId):
    oc = ObjectContainer(title2=str(L("season")) % seasonId)
    oc.add(DirectoryObject(key=Callback(DeleteSeason, seriesId=seriesId, seasonId=seasonId),
        title=L("confirmDelete"), summary=L("fileWarn"), thumb=R('exclamation-triangle.png')))
    return oc

@route('%s/delete/season/execute' % PREFIX)
def DeleteSeason(seriesId, seasonId):
    url = Dict['apiUrl']+'episodefile'
    seasonNbr = int(seasonId)
    try:
        r = requests.get(url, params={'seriesId': int(seriesId)}, headers=Dict["headers"])
        r.raise_for_status()
        for episode in r.json():
            if episode["seasonNumber"] == seasonNbr:
                Log.Info("Deleting: %d" % episode['id'])
                r = requests.delete(url+'/%s' % episode['id'], headers=Dict['headers'])
                r.raise_for_status()
        url = Dict['apiUrl']+'series/%s' % seriesId
        r = requests.get(url, headers=Dict['headers'])
        r.raise_for_status()
        url = Dict['apiUrl']+'series'
        puts = r.json()
        for season in puts['seasons']:
            if season["seasonNumber"] == seasonNbr:
                Log.Info("Unmonitoring S%d for series: %s" % (seasonNbr, seriesId))
                season['monitored'] = False
                break
        r = requests.put(url, json=puts, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L('error'), e.message)
    return MessageContainer(L("success"), L("deleted"))

@route('%s/episodes' % PREFIX)
def Episodes(seriesId, seasonId):
    url = Dict['apiUrl']+'episode'
    try:
        r = requests.get(url, params={'seriesId': seriesId}, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    request = r.json()
    seriesTitle = request[0]['series']['title']
    oc = ObjectContainer(title2=seriesTitle)
    for episode in reversed(request):
        seasonNbr = str(episode['seasonNumber'])
        if not seasonNbr == seasonId:
            continue
        thumb = Monitored(episode["monitored"])
        episodeNbr = episode["episodeNumber"]
        title = "%d - %s" % (episodeNbr, episode['title'])
        if episode["hasFile"]:
            title = "[X] "+title
        else:
            title = "[ ] "+title
        overview = L("noInfo")
        if 'overview' in episode:
            overview = episode['overview']
        summary = str(L("downloaded")) % (episode['hasFile'], overview)
        episodeId = episode['id']
        oc.add(DirectoryObject(key=Callback(EpisodeOptions, episodeId=episodeId),
            title=title, summary=summary, thumb=thumb))
    if not len(oc):
        return MessageContainer(L("status"), L("noResults"))
    return oc

@route('%s/episodes/options' % PREFIX)
def EpisodeOptions(episodeId):
    url = Dict['apiUrl']+"episode/%s" % episodeId
    try:
        r = requests.get(url, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    episode = r.json()
    title = episode['title']
    episodeId = episode['id']
    monitored = episode['monitored']
    thumb = Monitored(monitored)
    oc = ObjectContainer(title2=title)
    oc.add(DirectoryObject(key=Callback(EpisodeMonitorPopup, episodeId=episodeId,
        setMonitor=(not monitored)), title=L("toggleMonitor"), thumb=thumb))
    oc.add(DirectoryObject(key=Callback(CommandSearch, episodeId=int(episodeId)),
        title=L("episodeSearch"), summary=L("episodeSearchInfo"), thumb=R('search.png')))
    return oc

@route('%s/episodes/monitor/popup' % PREFIX, episodeId=int, setMonitor=bool)
def EpisodeMonitorPopup(episodeId, setMonitor):
    oc = ObjectContainer()
    thumb = Monitored(setMonitor)
    oc.add(DirectoryObject(key=Callback(EpisodeMonitorToggle, episodeId=episodeId,
        setMonitor=setMonitor), title='Set Monitoring: %s' % setMonitor,
        summary=str(L("monitorConfirm")) % setMonitor, thumb=thumb))
    return oc

@route('%s/episodes/monitor/toggle' % PREFIX, episodeId=int, setMonitor=bool)
def EpisodeMonitorToggle(episodeId, setMonitor):
    oc = ObjectContainer()
    url = Dict['apiUrl']+'episode/%s' % episodeId
    Log.Debug('Episode: %d' % episodeId)
    try:
        r = requests.get(url, headers=Dict['headers'])
        r.raise_for_status()
        url = Dict['apiUrl']+'episode'
        puts = r.json()
        puts['monitored'] = setMonitor
        r = requests.put(url, json=puts, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L("error"), e.message)
    return MessageContainer(L("success"), str(L('monitorSet')) % setMonitor)

@route('%s/thumb' % PREFIX)
def GetThumb(url, contentType='image/jpeg', timeout=15, cacheTime=3600):
    data = HTTP.Request(url=url, timeout=timeout, cacheTime=cacheTime)
    return DataObject(data.content, contentType)

def PrettyDate(d):
    now = Datetime.Now()
    dt = d.replace(tzinfo=None)+Dict['utcOffset']
    diff = now - dt
    s = diff.seconds

    # Future
    if dt > now:
        if now.day == dt.day:
            pretty = dt.strftime(str(L('today')+'%I:%M%p'))
        elif (now+Datetime.Delta(days=1)).day == dt.day:
            pretty = dt.strftime(str(L('tomorrow'))+'%I:%M%p')
        else:
            pretty = dt.strftime('%a %I:%M%p')
    # Past
    else:
        if diff.days > 7:
            pretty = dt.strftime('%d %b %Y')
        elif diff.days > 1:
            pretty = str(diff.days) + str(L('daysago'))
        elif diff.days == 1:
            pretty = str(L('yesterday'))
        elif s < 3600:
            pretty = str(s/60) + str(L('minutesago'))
        elif s < 7200:
            pretty = str(L('hourago'))
        else:
            pretty = str(s/3600) + str(L('hoursago'))
    return pretty

def Monitored(b):
    if b:
        return R('bookmark.png')
    else:
        return R('bookmark-o.png')

# Convert a datetime to ISO-8601 formatted in UTC to send to Sonarr
def TimeStampUTCString(time=datetime.utcnow()):
    return str(time.isoformat('T')).split('.')[0]+'Z'

@route("%s/calendar" % PREFIX)
def Calendar():
    start = TimeStampUTCString(datetime.utcnow()-Datetime.Delta(hours=6))
    end = TimeStampUTCString(datetime.utcnow()+Datetime.Delta(weeks=1))

    url = Dict['apiUrl']+'calendar'
    try:
        r = requests.get(url, params={'start':start, 'end':end}, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer(L('error'), e.message)

    oc = ObjectContainer(title2=L("calendar"))
    for episode in r.json():
        seasonNbr = episode['seasonNumber']
        episodeNbr = episode['episodeNumber']
        episodeId = episode['id']
        dt = Datetime.ParseDate(episode['airDateUtc'])
        episodeTitle = episode['title']
        episodeOverview = L("noInfo")
        if 'overview' in episode:
            episodeOverview = episode['overview']
        title="%s - %dX%02d - %s" % (episodeTitle, seasonNbr, episodeNbr,
            PrettyDate(dt))
        dirObj = DirectoryObject(key=Callback(EpisodeOptions, episodeId=episodeId),
            title=title, summary=episodeOverview)
        for coverType in episode['series']['images']:
            if coverType['coverType'] == "poster":
                dirObj.thumb=Callback(GetThumb, url=coverType['url'])
                break
        oc.add(dirObj)
    if not len(oc):
        return MessageContainer(L('status'), L("noResults"))
    return oc

@route("%s/wanted" % PREFIX, page=int, pageSize=int)
def Wanted(page=1, pageSize=19):
    oc = ObjectContainer(title2='Wanted')

    url = Dict['apiUrl']+'missing'
    try:
        r = requests.get(url, params={'page':page, 'pageSize':pageSize,
            'sortKey':'airDateUtc', 'sortDir':'desc'}, headers=Dict['headers'],
            verify=False)
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        raise
        return MessageContainer(L('error'), e.message)

    for record in r.json()['records']:
        seasonNbr = record['seasonNumber']
        episodeNbr = record['episodeNumber']
        seriesTitle = record['series']['title']
        episodeTitle = record['title']
        date = Datetime.ParseDate(record['airDateUtc'])
        episodeId = record['id']
        title="%s - %dX%02d - %s" % (seriesTitle, seasonNbr, episodeNbr,
            PrettyDate(date))
        episodeTitle = record['title']
        summary = "%s" % episodeTitle
        dirObj = DirectoryObject(key=Callback(EpisodeOptions, episodeId=episodeId),
            title=title, summary=summary)
        for coverType in record['series']['images']:
            if coverType['coverType'] == "poster":
                dirObj.thumb=Callback(GetThumb, url=coverType['url'])
                break
        oc.add(dirObj)
    if not len(oc):
        return MessageContainer(L('status'), L('noResults'))
    if page*pageSize < r.json()['totalRecords']:
        oc.add(NextPageObject(key=Callback(Wanted, page=page+1)))
    return oc
