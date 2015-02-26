from datetime import datetime
import requests

PREFIX  = '/video/sonarr'
NAME   = 'Sonarr'

# TODO
# finish other todos
# locale everything

def Start():
    ObjectContainer.art    = R('logo.png')
    ObjectContainer.title1 = NAME
    ObjectContainer.title2 = NAME
    DirectoryObject.thumb  = R('question-circle.png')
    Dict['utcOffset'] = Datetime.Now().replace(minute=0, second=0,
        microsecond=0) - datetime.utcnow().replace(minute=0, second=0,
        microsecond=0, tzinfo=None)
    Log.Debug('UTC Offset: %s' % Dict['utcOffset'])
    #Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    #Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
    ValidatePrefs()

    # TODO - Remove after develop
    HTTP.ClearCache()

@handler(PREFIX, NAME, '1024.png', 'logo.png')
def MainMenu():
    #oc = ObjectContainer(view_group="InfoList")
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(Series), title=L('SERIES'),
        summary = 'View all series or add to your collection',  thumb=R('play.png')))
    oc.add(DirectoryObject(key=Callback(Calendar), title=L('CALENDAR_TITLE'),
        summary = "This week's upcoming episodes", thumb=R('calendar.png')))
    oc.add(DirectoryObject(key=Callback(Queue), title=L('QUEUE_TITLE'),
        summary = 'Display currently downloading info', thumb=R('cloud.png')))
    oc.add(DirectoryObject(key=Callback(History), title=L('HISTORY_TITLE'),
        summary = L('HISTORY_SUMMARY'), thumb=R('history.png')))
    oc.add(DirectoryObject(key=Callback(Wanted), title=L('MISSING_TITLE'),
        summary = 'List missing episodes (episodes without files)', thumb=R('exclamation-triangle.png')))
    oc.add(PrefsObject(title=L('SETTINGS_TITLE'), summary=L('SETTINGS_SUMMARY'),
        thumb=R('cogs.png')))
    return oc

def ValidatePrefs():
    protocol = 'http'
    if Prefs['ssl']:
        protocol = 'https'
    Dict['host']  = '{}://{}:{}'.format(protocol, Prefs['ip'], Prefs['port'])
    Dict['apiUrl'] = "{}/api/".format(Dict['host']+Prefs['base'])
    Dict['headers'] = {'X-Api-Key': Prefs['apiKey']}
    Log.Debug('Sonarr url: %s' % Dict['host'])
    Log.Debug('API Url: %s' % Dict['apiUrl'])

@route('%s/develop' % PREFIX)
def Stub():
    return MessageContainer('MOAR DETAILZ', 'Allan please add details')

@route('%s/series' % PREFIX)
def Series():
    url = Dict['apiUrl']+'series'
    try:
        r = requests.get(url, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer('Error', e.message)
    oc = ObjectContainer(title2="Series")
    oc.add(InputDirectoryObject(key=Callback(SeriesSearch), title="Add Series",
        thumb=R("search-plus.png"), summary="SHIT", prompt="Add New Series"))
    for series in sorted(r.json(), key=lambda x: x['sortTitle']):
        title = series['title']
        seriesId = series['id']
        seasons = series['seasonCount']
        status = series['status']
        network = series['network']
        monitored = series['monitored']
        summary = "Status: {}  Network: {}  Monitored: {}  Seasons: {}".format(status,
            network, monitored, seasons)
        dirObj = DirectoryObject(key=Callback(SeriesOptions,
            seriesId=seriesId, title2=title), title=title, summary=summary)
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
        return MessageContainer('Error', e.message)
    oc = ObjectContainer(title2='Results')
    # TODO do not default to first found profile
    profile = requests.get(Dict['apiUrl']+'qualityprofile', headers=Dict['headers']).json()[0]['id']
    rootFolderPath = requests.get(Dict['apiUrl']+'rootfolder', headers=Dict['headers']).json()[0]['path']
    for series in r.json():
        title = '%s (%s)' % (series['title'], series['year'])
        tvdbId = series['tvdbId']
        title = series['title']
        titleSlug = series['titleSlug']
        seasons = series['seasons']
        # TODO should this default to seasonFolder?
        seasonFolder = True
        newSeries = {'tvdbId': tvdbId, 'title': title, 'profileId': profile,
            'titleSlug': titleSlug, 'seasons': seasons, 'seasonFolder': seasonFolder, 'rootFolderPath': rootFolderPath}
        overview = "No overview provided"
        network = "Unknown"
        if 'overview' in series:
            overview = series['overview']
        if 'network' in series:
            network = series['network']
        dirObj = DirectoryObject(key=Callback(AddSeries, series=newSeries), title=title, summary='Network: %s Description: %s' % (network, overview))
        if 'remotePoster' in series:
            dirObj.thumb=Callback(GetThumb, url=series['remotePoster'])
        oc.add(dirObj)
    if not len(oc):
        return MessageContainer('Status', 'No results')
    return oc

@route('%s/series/add' % PREFIX, series=dict)
def AddSeries(series):
    url = Dict['apiUrl'] + 'series'
    try:
        r = requests.post(url, json=series, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer('Error', e.message)
    return MessageContainer('Success', 'Using Default Profile but NOT monitored. Change this in Series section.')

@route('%s/queue' % PREFIX)
def Queue():
    url = Dict['apiUrl']+'queue'
    try:
        r = requests.get(url, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer('Error', e.message)
    oc = ObjectContainer(title2='Queue')
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
        return MessageContainer('Empty', "Nothing in the queue")
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
        return MessageContainer('Error', e.message)
    oc = ObjectContainer(title2=L('HISTORY_TITLE'))
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
            summary = L('IMPORTED')
            thumb = R('download.png')
        elif event == "downloadFailed":
            summary = L('FAILED')
            thumb = R('cloud-download-failed.png')
        elif event == "grabbed":
            summary = L('GRABBED')
            thumb = R('cloud-download.png')
        elif event == "episodeFileDeleted":
            summary = L('DELETED')
            thumb = R('trash-o.png')
        else:
            summary = record['eventType']
            thumb = R('question-circle.png')
        title="%s - %dX%02d - %s" % (seriesTitle, seasonNbr, episodeNbr,
            PrettyDate(date))
        summary = "%s: %s  Quality: %s" % (summary, episodeTitle, episodeQuality)
        oc.add(DirectoryObject(key=Callback(EpisodeOptions, episodeId=episodeId), title=title, summary=summary,
            thumb=thumb))
    if not len(oc):
        return MessageContainer(L('HISTORY_TITLE'), L('HISTORY_NONE'))
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
        return MessageContainer('Error', e.message)
    monitored = r.json()['monitored']
    thumb = Monitored(monitored)
    oc = ObjectContainer(title2=title2)
    oc.add(DirectoryObject(key=Callback(Seasons, seriesId=seriesId),
        title='List seasons', summary='LIST SEASONS', thumb=R('th-list.png')))
    oc.add(PopupDirectoryObject(key=Callback(Monitor, seriesId=seriesId,
        setMonitor=(not monitored)), title='Toggle Monitoring', summary='Monitoring: %s' % monitored, thumb=thumb))
    oc.add(DirectoryObject(key=Callback(QualityProfile, seriesId=seriesId),
        title='Change Quality', summary='Set quality profile', thumb=R('wrench.png')))
    oc.add(DirectoryObject(key=Callback(Stub),
        title='Series Search', summary='Search for all episodes in this series', thumb=R('search.png')))
    oc.add(DirectoryObject(key=Callback(DeleteSeriesPopup, entityId=seriesId, title2=title2),
        title='Delete series', summary='DELETE SERIES', thumb=R('trash-o.png')))
    return oc

@route('%s/delete/popup' % PREFIX)
def DeleteSeriesPopup(entityId, title2):
    oc = ObjectContainer(title2=title2)
    oc.add(DirectoryObject(key=Callback(DeleteSeries, entityId=entityId), title='Confirm Deletion',
        summary='Warning: All files will be deleted from disk!', thumb=R('exclamation-triangle.png')))
    return oc

@route('%s/delete/execute' % PREFIX)
def DeleteSeries(entityId):
    url = Dict['apiUrl']+'series/%s' % entityId
    try:
        r = requests.delete(url, json={'deleteFiles': True }, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer('Error', e.message)
    return MessageContainer("Success", "Deleted")

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
        return MessageContainer('Error', e.message)
    oc = ObjectContainer(title2='Quality Profile')
    for profile in profiles:
        title = profile['name']
        qualityId = profile['id']
        if qualityId == series['profileId']:
            title += " (Current)"
            thumb = R('square.png')
        else:
            thumb = R('circle-o.png')
        Log.Debug('Adding profileId: %d' % qualityId)
        oc.add(DirectoryObject(key=Callback(QualityProfileSet, seriesId=seriesId,
            qualityId=qualityId), title=title,
            summary="Cutoff: %s" % profile['cutoff']['name'], thumb=thumb))
    if not len(oc):
        return MessageContainer("Quality Profile", "No profiles found")
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
        return MessageContainer('Error', e.message)
    return MessageContainer("Success", "Profile quality saved.")

@route('%s/monitor/popup' % PREFIX, setMonitor=bool, seasonNbr=int)
def Monitor(seriesId, setMonitor, seasonNbr=-1):
    oc = ObjectContainer()
    thumb = Monitored(setMonitor)
    oc.add(DirectoryObject(key=Callback(MonitorToggle, seriesId=seriesId, setMonitor=setMonitor, seasonNbr=seasonNbr), title='Set Monitoring: %s' % setMonitor,
        summary="Confirm changing monitoring to %s" % setMonitor, thumb=thumb))
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
        return MessageContainer('Error', e.message)
    return MessageContainer('Success', 'Monitor set to %s' % setMonitor)

@route('%s/series/seasons' % PREFIX)
def Seasons(seriesId):
    url = Dict['apiUrl']+'series/%s' % seriesId
    try:
        r = requests.get(url, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer('Error', e.message)
    title = r.json()['title']
    oc = ObjectContainer(title2=title)
    for season in reversed(r.json()["seasons"]):
        thumb = Monitored(season["monitored"])
        seasonNbr = season["seasonNumber"]
        seasonStr = "Season %s" % seasonNbr
        oc.add(DirectoryObject(key=Callback(SeasonsOptions, seriesId=seriesId,
            seasonId=seasonNbr, monitored=season["monitored"]), title=seasonStr,
                summary=seasonStr, thumb=thumb))
    if not len(oc):
        return MessageContainer(title2, "NO SEASONS FOUND")
    return oc

@route('%s/series/seasons/options' % PREFIX, monitored=bool)
def SeasonsOptions(seriesId, seasonId, monitored):
    oc = ObjectContainer(title2="Season %s" % seasonId)
    thumb = Monitored(monitored)
    oc.add(DirectoryObject(key=Callback(Episodes, seriesId=seriesId, seasonId=seasonId),
        title='List episodes', summary='List episodes for this season', thumb=R('th-list.png')))
    oc.add(DirectoryObject(key=Callback(Monitor, seriesId=seriesId,
        setMonitor=(not monitored), seasonNbr=int(seasonId)),
        title='Toggle Monitoring', summary='Current status is', thumb=thumb))
    oc.add(DirectoryObject(key=Callback(Stub),
        title='Season Search', summary='Automatic search for all episodes in this season', thumb=R('search.png')))
    oc.add(DirectoryObject(key=Callback(Stub),
        title='Delete Season', summary='Delete from disk and unmonitor this season', thumb=R('trash-o.png')))
    return oc

@route('%s/episodes' % PREFIX)
def Episodes(seriesId, seasonId):
    url = Dict['apiUrl']+'episode'
    try:
        r = requests.get(url, params={'seriesId': seriesId}, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer('Error', e.message)
    request = r.json()
    seriesTitle = request[0]['series']['title']
    oc = ObjectContainer(title2=seriesTitle)
    for episode in reversed(request):
        seasonNbr = str(episode['seasonNumber'])
        # TODO this is ugly, make this better
        if not seasonNbr == seasonId:
            continue
        thumb = Monitored(episode["monitored"])
        episodeNbr = episode["episodeNumber"]
        title = "%d - %s" % (episodeNbr, episode['title'])
        overview = "No overview provided."
        if 'overview' in episode:
            overview = episode['overview']
        summary = "Downloaded: %s - %s" % (episode['hasFile'], overview)
        episodeId = episode['id']
        oc.add(DirectoryObject(key=Callback(EpisodeOptions, episodeId=episodeId),
            title=title, summary=summary, thumb=thumb))
    if not len(oc):
        return MessageContainer("Error", "No episodes found.")
    return oc

@route('%s/episodes/options' % PREFIX)
def EpisodeOptions(episodeId):
    url = Dict['apiUrl']+"episode/%s" % episodeId
    try:
        r = requests.get(url, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer('Error', e.message)
    episode = r.json()
    title = episode['title']
    episodeId = episode['id']
    monitored = episode['monitored']
    thumb = Monitored(monitored)
    oc = ObjectContainer(title2=title)
    oc.add(DirectoryObject(key=Callback(EpisodeMonitorPopup, episodeId=episodeId, setMonitor=(not monitored)),
        title='Toggle Monitoring', summary='Current statsdfsd', thumb=thumb))
    oc.add(DirectoryObject(key=Callback(Stub),
        title='Episode Search %s' % episodeId, summary='Automatic search for this episode', thumb=R('search.png')))
    return oc

@route('%s/episodes/monitor/popup' % PREFIX, episodeId=int, setMonitor=bool)
def EpisodeMonitorPopup(episodeId, setMonitor):
    oc = ObjectContainer()
    thumb = Monitored(setMonitor)
    oc.add(DirectoryObject(key=Callback(EpisodeMonitorToggle, episodeId=episodeId, setMonitor=setMonitor), title='Set Monitoring: %s' % setMonitor,
        summary="Confirm changing monitoring to %s" % setMonitor, thumb=thumb))
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
        return MessageContainer('Error', e.message)
    return MessageContainer('Success', 'Monitor set to %s' % setMonitor)

@route('%s/thumb' % PREFIX)
def GetThumb(url, contentType='image/jpeg', timeout=15, cacheTime=120):
    Log.Debug("Image: %s" % url)
    data = HTTP.Request(url=url, timeout=timeout, cacheTime=cacheTime)
    return DataObject(data.content, contentType)

# TODO pretty future date
def PrettyDate(d):
    diff = Datetime.Now() - (d.replace(tzinfo=None)+Dict['utcOffset'])
    s = diff.seconds
    Log.Debug(str(diff))
    Log.Debug('Days: %d Hours: %d Min: %d Sec: %d' % (diff.days, s/3600, s/60, s))
    Log.Debug('Format: %s' % d.strftime('%a %d %b at %I:%M%p'))
    # Future
    if diff.days < 0:
        if diff.days == -1:
            pretty = d.strftime('Tomorrow at %I:%M%p')
        elif diff.days < -3:
            pretty = d.strftime('%a at %I:%M%p')
        else:
            pretty = d.strftime('%a %d %b')
    # Past
    else:
        if diff.days > 7:
            pretty = d.strftime('%d %b %Y')
        elif diff.days == 1:
            pretty = 'Yesterday'
        elif diff.days > 1:
            pretty = '{} days ago'.format(diff.days)
        elif s < 3600:
            pretty = '{} minutes ago'.format(s/60)
        elif s < 7200:
            pretty = '1 hour ago'
        else:
            pretty = '{} hours ago'.format(s/3600)
    Log.Debug('Pretty: %s' % pretty)
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
    start = TimeStampUTCString(datetime.utcnow()-Datetime.Delta(days=1))
    end = TimeStampUTCString(datetime.utcnow()+Datetime.Delta(weeks=1))

    url = Dict['apiUrl']+'calendar'
    try:
        r = requests.get(url, params={'start':start, 'end':end}, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer('Error', e.message)

    oc = ObjectContainer(title2="Calendar")
    for episode in r.json():
        seasonNbr = episode['seasonNumber']
        episodeNbr = episode['episodeNumber']
        episodeId = episode['id']
        dt = Datetime.ParseDate(episode['airDateUtc'])+Dict['utcOffset']
        episodeTitle = episode['title']
        episodeOverview = 'No information provided'
        Log.Debug(episodeTitle)
        if 'overview' in episode:
            episodeOverview = episode['overview']
        title="%s - %dX%02d - %s" % (episodeTitle, seasonNbr, episodeNbr,
            PrettyDate(dt))
        dirObj = DirectoryObject(key=Callback(EpisodeOptions, episodeId=episodeId), title=title, summary=episodeOverview)
        for coverType in episode['series']['images']:
            if coverType['coverType'] == "poster":
                dirObj.thumb=Callback(GetThumb, url=coverType['url'])
                break
        oc.add(dirObj)
    if not len(oc):
        return MessageContainer('WHAT?', "No Upcoming Episodes.")
    return oc

@route("%s/wanted" % PREFIX, page=int, pageSize=int)
def Wanted(page=1, pageSize=19):
    oc = ObjectContainer(title2='Wanted')

    url = Dict['apiUrl']+'missing'
    try:
        r = requests.get(url, params={'page':page, 'pageSize':pageSize,
            'sortKey':'airDateUtc', 'sortDir':'desc'}, headers=Dict['headers'])
        r.raise_for_status()
    except Exception as e:
        Log.Critical(e.message)
        return MessageContainer('Error', e.message)

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
        dirObj = DirectoryObject(key=Callback(EpisodeOptions, episodeId=episodeId), title=title, summary=summary)
        for coverType in record['series']['images']:
            if coverType['coverType'] == "poster":
                dirObj.thumb=Callback(GetThumb, url=coverType['url'])
                break
        oc.add(dirObj)
    if not len(oc):
        return MessageContainer('Congratz', 'No missing episodes')
    if page*pageSize < r.json()['totalRecords']:
        oc.add(NextPageObject(key=Callback(Wanted, page=page+1)))
    return oc
