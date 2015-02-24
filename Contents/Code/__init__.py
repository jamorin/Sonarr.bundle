from datetime import datetime
import requests

PREFIX  = '/video/sonarr'
NAME   = 'Sonarr'

ICON = '256.png'
ART  =  'logo.png'

# Default thumb to question mark
# Migrate all api calls to requests


def Start():
    global NAME
    NAME = L('TITLE')
    ObjectContainer.art        =  R(ART)
    ObjectContainer.title1      = NAME
    ObjectContainer.title2      = NAME
    DirectoryObject.thumb  = R(ICON)
    Dict['utcOffset'] = Datetime.Now().replace(minute=0, second=0,
        microsecond=0) - datetime.utcnow().replace(minute=0, second=0,
        microsecond=0, tzinfo=None)
    Log.Debug('UTC offset: %s' % Dict['utcOffset'])
    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
    if Prefs['ssl']:
        protocol = 'https'
    else:
        protocol = 'http'
    Dict['url']  = '%s://%s:%s' % (protocol, Prefs['ip'], Prefs['port'])
    Log.Debug('Sonarr url: %s' % Dict['url'])
    Dict['apiUrl'] = "{}/api/".format(Dict['url']+Prefs['base'])
    Log.Debug('API Url: %s' % Dict['apiUrl'])
    # For Debug
    HTTP.ClearCache()

@handler(PREFIX, NAME, ICON, ART)
def MainMenu():
    oc = ObjectContainer(view_group="InfoList")
    oc.add(DirectoryObject(key=Callback(Series), title=L('SERIES_TITLE'),
        summary = 'View all series in your collection',  thumb=R('fa-play.png')))
    oc.add(DirectoryObject(key=Callback(Calendar), title=L('CALENDAR_TITLE'),
        summary = "Get this week's upcoming episodes", thumb=R('fa-calendar.png')))
    oc.add(DirectoryObject(key=Callback(Queue), title=L('QUEUE_TITLE'),
        summary = 'Display currently downloading info'))
    oc.add(DirectoryObject(key=Callback(History), title=L('HISTORY_TITLE'),
        summary = L('HISTORY_SUMMARY'), thumb=R('fa-history.png')))
    oc.add(DirectoryObject(key=Callback(Wanted), title=L('MISSING_TITLE'),
        summary = 'List missing episodes (episodes without files)', thumb=R('fa-exclamation-triangle.png')))
    oc.add(PrefsObject(title=L('SETTINGS_TITLE'), summary=L('SETTINGS_SUMMARY'),
        thumb=R('fa-cogs.png')))
    return oc

def ValidatePrefs():
    if Prefs['ssl']:
        protocol = 'https'
    else:
        protocol = 'http'
    Dict['url']  = '%s://%s:%s' % (protocol, Prefs['ip'], Prefs['port'])
    Log.Debug('Sonarr url: %s' % Dict['url'])
    Dict['apiUrl'] = "{}/api/".format(Dict['url']+Prefs['base'])
    Log.Debug('API Url: %s' % Dict['apiUrl'])
    return MessageContainer(L("SUCCESS"), L("PREFS_SAVED"))

@route('%s/stub' % PREFIX)
def Stub():
    return MessageContainer('Stub', 'Allan please add details')

def ApiRequest(endpoint, params={}):
    url = Dict['apiUrl'] + endpoint
    if len(params):
        url += '?'
        for key, value in params.items():
            url += "%s=%s&" % (key, value)
        url = url.rstrip('&')
    request = JSON.ObjectFromURL(url, headers={'X-Api-Key': Prefs['apiKey']})
    return request

@route('%s/series' % PREFIX)
def Series():
    oc = ObjectContainer(title2="Series")
    request = ApiRequest('series')
    oc.add(InputDirectoryObject(key=Callback(SeriesSearch), title="Add Series", summary="SHIT", prompt="Add New Series"))
    for series in sorted(request, key=lambda x: x['sortTitle']):
        title = series['title']
        seriesId = series['id']
        summary = series['network']+str(seriesId)
        dirObj = DirectoryObject(key=Callback(SeriesOptions,
            seriesId=seriesId, title2=title), title=title, summary=summary)
        for coverType in series['images']:
            if coverType['coverType'] == "poster":
                dirObj.thumb=Callback(GetThumb, url=Dict['url']+coverType['url'])
                break
        oc.add(dirObj)
    return oc

@route('%s/series/search' % PREFIX)
def SeriesSearch(query):
    Log.Debug("Searching for [%s]" % query)
    request = ApiRequest('Series/lookup', params={'term':String.Quote(query)})
    oc = ObjectContainer(title2='Results')
    profile = ApiRequest('qualityprofile')[0]['id']
    rootFolderPath = ApiRequest('rootfolder')[0]['path']
    for series in request:
        title = '%s (%s)' % (series['title'], series['year'])
        tvdbId = series['tvdbId']
        title = series['title']
        titleSlug = series['titleSlug']
        seasons = series['seasons']
        seasonFolder = True
        newSeries = {'tvdbId': tvdbId, 'title': title, 'qualityProfileId': profile,
            'titleSlug': titleSlug, 'seasons': seasons, 'seasonFolder': seasonFolder, 'rootFolderPath': rootFolderPath}
        dirObj = DirectoryObject(key=Callback(AddSeries, series=newSeries), title=title, summary='wfwf')
        if 'remotePoster' in series:
            dirObj.thumb=Callback(GetThumb, url=series['remotePoster'])
        oc.add(dirObj)
    if not len(oc):
        return MessageContainer('No results', 'Search: %s' % query)
    return oc

@route('%s/series/add' % PREFIX, series=dict)
def AddSeries(series):
    url = Dict['apiUrl'] + 'series'
    request = requests.post(url, json=series,
        headers={'X-Api-Key': Prefs['apiKey']})
    Log.Debug(type(request.content))
    return MessageContainer('added', 'yo added')

@route('%s/queue' % PREFIX)
def Queue():
    oc = ObjectContainer(title2='Queue')
    if not len(oc):
        return MessageContainer('Empty', "Nothing in the queue")
    return oc

@route('%s/history' % PREFIX, page=int, pageSize=int)
def History(page=1, pageSize=19):
    oc = ObjectContainer(title2=L('HISTORY_TITLE'))
    request = ApiRequest('history', params=dict(page=page, pageSize=pageSize,
        sortKey='date', sortDir='desc'))
    for record in request['records']:
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
            thumb = R('fa-download.png')
        elif event == "downloadFailed":
            summary = L('FAILED')
            thumb = R('fa-cloud-download-failed.png')
        elif event == "grabbed":
            summary = L('GRABBED')
            thumb = R('fa-cloud-download.png')
        elif event == "episodeFileDeleted":
            summary = L('DELETED')
            thumb = R(ICON)
        else:
            summary = record['eventType']
            thumb = R(ICON)
        title="%s - %dX%02d %s" % (seriesTitle, seasonNbr, episodeNbr,
            prettydate(date))
        summary = "%s: %s %s" % (summary, episodeTitle, episodeQuality)
        oc.add(DirectoryObject(key=Callback(EpisodeOptions, episodeId=episodeId), title=title, summary=summary,
            thumb=thumb))
    if not len(oc):
        return MessageContainer(L('HISTORY_TITLE'), L('HISTORY_NONE'))
    if page*pageSize < request['totalRecords']:
        oc.add(NextPageObject(key=Callback(History, page=page+1)))
    return oc

@route('%s/series/options' % PREFIX)
def SeriesOptions(seriesId, title2):
    oc = ObjectContainer(title2=title2)
    oc.add(DirectoryObject(key=Callback(Stub), title='Toggle Monitored', summary='Toggle shit'))
    oc.add(DirectoryObject(key=Callback(Stub),
        title='Change Quality', summary='Set quality profile', thumb=R(ICON)))
    oc.add(DirectoryObject(key=Callback(SearchEpisodeSeries, seriesId=seriesId, title2=title2),
        title='Series Search', summary='Search for all episodes in this series', thumb=R(ICON)))
    oc.add(DirectoryObject(key=Callback(DeleteSeries, seriesId=seriesId, title2=title2),
        title='Delete series', summary='DELETE SERIES', thumb=R(ICON)))
    oc.add(DirectoryObject(key=Callback(Seasons, seriesId=seriesId),
        title='List seasons', summary='LIST SEASONS', thumb=R(ICON)))
    return oc

@route('%s/series/seasons' % PREFIX)
def Seasons(seriesId):
    request = ApiRequest('series/%s' % seriesId)
    title = request['title']
    oc = ObjectContainer(title2=title)
    for season in reversed(request["seasons"]):
        if season["monitored"]:
            thumb = R('fa-bookmark-monitored.png')
            summary = "Monitored"
        else:
            thumb = R('fa-bookmark.png')
            summary = "Not Monitored"
        seasonNbr = season["seasonNumber"]
        oc.add(DirectoryObject(key=Callback(SeasonsOptions, seriesId=seriesId,
            seasonId=seasonNbr), title="Season %s" % seasonNbr,
            summary = summary, thumb=thumb))
    if not len(oc):
        return MessageContainer(title2, "NO SEASONS FOUND")
    return oc

@route('%s/series/seasons/options' % PREFIX)
def SeasonsOptions(seriesId, seasonId):
    oc = ObjectContainer(title2="Season %s" % seasonId)
    oc.add(DirectoryObject(key=Callback(Stub),
        title='Toggle Monitored Status', summary='Current status is: STUB', thumb=R(ICON)))
    oc.add(DirectoryObject(key=Callback(Stub),
        title='Season Search', summary='Automatic search for all episodes in this season', thumb=R(ICON)))
    oc.add(DirectoryObject(key=Callback(Stub),
        title='Delete Season', summary='Delete this season from disk', thumb=R(ICON)))
    oc.add(DirectoryObject(key=Callback(Episodes, seriesId=seriesId, seasonId=seasonId),
        title='List episodes', summary='List episodes for this season', thumb=R(ICON)))
    return oc

@route('%s/episodes' % PREFIX)
def Episodes(seriesId, seasonId):
    request = ApiRequest("episode", {'seriesId': seriesId})
    seriesTitle = request[0]['series']['title']
    oc = ObjectContainer(title2=seriesTitle)
    for episode in reversed(request):
        seasonNbr = str(episode['seasonNumber'])
        if not seasonNbr == seasonId:
            continue
        episodeNbr = episode["episodeNumber"]
        title = "%d %s" % (episodeNbr, episode['title'])
        summary = "Monitored: %s\nFile: %s" % (episode["monitored"], episode['hasFile'])
        episodeId = episode['id']
        oc.add(DirectoryObject(key=Callback(EpisodeOptions, episodeId=episodeId), title=title, summary=summary))
    if not len(oc):
        return MessageContainer("Error", "No episodes found.")
    return oc

@route('%s/episodes/options' % PREFIX)
def EpisodeOptions(episodeId):
    request = ApiRequest("episode/%s" % episodeId)
    title = request['title']
    oc = ObjectContainer(title2=title)
    oc.add(DirectoryObject(key=Callback(Stub),
        title='Toggle Monitored Status', summary='Current status is: STUB', thumb=R(ICON)))
    oc.add(DirectoryObject(key=Callback(Stub),
        title='Episode Search %s' % episodeId, summary='Automatic search for this episode', thumb=R(ICON)))
    oc.add(DirectoryObject(key=Callback(Stub),
        title='Delete Episode', summary='Delete this episode from disk', thumb=R(ICON)))
    return oc

@route('%s/searchepisodeseries' % PREFIX)
def SearchEpisodeSeries(seriesId, title2):
    return MessageContainer(title2, 'Searching for episodes in seriesId:%s' % seriesId)

@route('%s/deleteseries' % PREFIX)
def DeleteSeries(seriesId, title2):
    return MessageContainer(title2, 'Deleting  seriesId:%s' % seriesId)

@route('%s/thumb' % PREFIX)
def GetThumb(url, contentType='image/jpeg', timeout=10, cacheTime=10):
    Log.Debug(url)
    data = HTTP.Request(url=url, timeout=timeout, cacheTime=cacheTime)
    return DataObject(data.content, contentType)

def prettydate(d):
    """ http://stackoverflow.com/a/5164027 """
    diff = Datetime.Now() - (d.replace(tzinfo=None)+Dict['utcOffset'])
    s = diff.seconds
    if diff.days > 7 or diff.days < 0:
        return d.strftime('%d %b %y')
    elif diff.days == 1:
        return '1 day ago'
    elif diff.days > 1:
        return '{} days ago'.format(diff.days)
    elif s < 3600:
        return '{} minutes ago'.format(s/60)
    elif s < 7200:
        return '1 hour ago'
    else:
        return '{} hours ago'.format(s/3600)

# Convert a datetime to ISO-8601 formatted in UTC to send to Sonarr
def TimeStampUTCString(time=datetime.utcnow()):
    return str(time.isoformat('T')).split('.')[0]+'Z'

@route("%s/calendar" % PREFIX)
def Calendar():
    start = TimeStampUTCString(datetime.utcnow()-Datetime.Delta(days=-1))
    end = TimeStampUTCString(datetime.utcnow()+Datetime.Delta(weeks=1))

    request = ApiRequest('calendar', params={'start':start, 'end':end})

    oc = ObjectContainer(title2="Calendar")
    for episode in request:
        seasonNbr = episode['seasonNumber']
        episodeNbr = episode['episodeNumber']
        episodeId = episode['id']
        dt = Datetime.ParseDate(episode['airDateUtc'])+Dict['utcOffset']
        episodeTitle = episode['title']
        episodeOverview = 'No information provided'
        if 'overview' in episode:
            episodeOverview = episode['overview']
        dirObj = DirectoryObject(key=Callback(EpisodeOptions, episodeId=episodeId), title=title, summary=episodeOverview)
        for coverType in episode['series']['images']:
            if coverType['coverType'] == "poster":
                dirObj.thumb=Callback(GetThumb, url=coverType['url'])
                break
        title="%s - %dX%02d %s" % (episodeTitle, seasonNbr, episodeNbr,
            prettydate(dt))
        oc.add(dirObj)
    if not len(oc):
        return MessageContainer('WHAT?', "No Upcoming Episodes.")
    return oc

@route("%s/wanted" % PREFIX, page=int, pageSize=int)
def Wanted(page=1, pageSize=19):
    oc = ObjectContainer(title2='Wanted')
    request = ApiRequest('missing', params={'page':page, 'pageSize':pageSize,
        'sortKey':'airDateUtc', 'sortDir':'desc'})
    for record in request['records']:
        seasonNbr = record['seasonNumber']
        episodeNbr = record['episodeNumber']
        seriesTitle = record['series']['title']
        episodeTitle = record['title']
        date = Datetime.ParseDate(record['airDateUtc'])
        episodeId = record['episodeId']
        title="%s - %dX%02d %s" % (seriesTitle, seasonNbr, episodeNbr,
            prettydate(date))
        episodeTitle = episode['title']
        episodeOverview = 'No information provided'
        summary = "%s: %s" % (episodeOverview, episodeTitle)
        dirObj = DirectoryObject(key=Callback(EpisodeOptions, episodeId=episodeId), title=title, summary=summary)
        for coverType in episode['series']['images']:
            if coverType['coverType'] == "poster":
                dirObj.thumb=Callback(GetThumb, url=coverType['url'])
                break
        oc.add(dirObj)
    if not len(oc):
        return MessageContainer('Congratz', 'No missing episodes')
    if page*pageSize < request['totalRecords']:
        oc.add(NextPageObject(key=Callback(Wanted, page=page+1)))
    return oc
