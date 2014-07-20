from datetime import datetime

PREFIX  = '/video/nzbdrone'
NAME   = 'NzbDrone'

ICON = '256.png'
PLAY = 'fa-play.png'
ART  =  'logo.png'
CALENDAR = 'fa-calendar.png'
HISTORY = 'fa-history.png'
PREFS_ICON = 'fa-cogs.png'
WANTED = 'fa-exclamation-triangle.png'
MONITORED = 'fa-bookmark-monitored.png'
NOTMONITORED = 'fa-bookmark.png'

IMPORTED = 'fa-download.png'
GRABBED = 'fa-cloud-download.png'
FAILED = 'fa-cloud-download-failed.png'

def Start():
    ObjectContainer.art        =  R(ART)
    ObjectContainer.title1      = NAME
    #ObjectContainer.thumb       = R(ICON)
    PopupDirectoryObject.thumb  = R(ICON)
    # 3600*3x
    #HTTP.CacheTime=0
    Dict['UTCOffset'] = Datetime.Now() - datetime.utcnow().replace(tzinfo=None) + Datetime.Delta(seconds=1)

@handler(PREFIX, NAME, ICON , ART)
def MainMenu():
    oc = ObjectContainer(no_cache=True)

    if not Prefs['API_Key']:
        return oc
    oc.add(DirectoryObject(key=Callback(SeriesList), title="Series",
    summary = "View and edit your exisiting TV Shows", thumb=R(PLAY)))
    oc.add(DirectoryObject(key=Callback(Calendar), title="Calendar",
    summary = "See which shows that you follow have episodes airing soon", thumb=R(CALENDAR)))
    oc.add(DirectoryObject(key=Callback(History), title="History",
        summary = "Recently downloaded history", thumb=R(HISTORY)))
    #oc.add(DirectoryObject(key=Callback(Wanted), title="Wanted",
        #summary = "Missing from NzbDrone", thumb=R(WANTED)))
    oc.add(PrefsObject(title="Settings", summary="Set plugin preferences", thumb=R(PREFS_ICON)))
    return oc

@route(PREFIX+"/validate")
def ValidatePrefs():
    pass

@route(PREFIX+"/series")
def SeriesList():
    oc = ObjectContainer(title2="Series")
    shows = API_Request(endUrl='/series')
    if shows == None:
        return Invalid()
    for s in sorted(shows, key=lambda x: x['titleSlug']):
        for coverType in s['images']:
            if coverType['coverType'] == "poster":
                image = coverType['url']
        thumb=Callback(GetThumb, image=Url()+image)
        show=dict(key=Callback(SeasonList, seriesId=s['id'], seasons=s['seasons'], title2=s['title']), title=s['title'], summary=s['overview'], thumb=thumb)
        oc.add(DirectoryObject(**show))
    if len(oc) == 0:
        return ObjectContainer(header=NAME, message="No shows found.")
    return oc

@route(PREFIX+"/seasonlist",seriesId=int, seasons=list)
def SeasonList(seriesId, seasons, title2='Seasons'):
    oc = ObjectContainer(title2=title2)
    for s in seasons:
        title='Season '+str(s['seasonNumber'])
        if s['seasonNumber']  == 0: title='Specials'
        thumb=R(NOTMONITORED)
        summary='Not monitored'
        if s['monitored']:
            thumb=R(MONITORED)
            summary='Monitored'
        season=dict(key=Callback(EpisodeList, seriesId=seriesId, season=s['seasonNumber'], title2=title2), title=title, thumb=thumb, summary=summary)
        oc.add(DirectoryObject(**season))
    if len(oc) == 0:
        return ObjectContainer(header=NAME, message='No seasons found.')
    return oc

@route(PREFIX+"/episodelist",seriesId=int, season=int)
def EpisodeList(seriesId,season,title2='Episodes'):
    oc = ObjectContainer(title2=title2)
    episodes = API_Request(endUrl='/episode', params=dict(seriesId=seriesId))
    if episodes == None:
        Invalid()
    for e in episodes:
        if e['seasonNumber'] == season:
            number = str(e['episodeNumber'])
            if len(number) == 1: number = '0'+number
            title=number+' - '+e['title']
            oc.add(DirectoryObject(key=Callback(Stub), title=title,summary=e['overview']))
    if len(oc) == 0:
        return ObjectContainer(header=NAME, message='No episodes found.')
    return oc

@route(PREFIX+"/calendar")
def Calendar(past=dict(days=0),delta=dict(weeks=1)):
    start = TimeStampUTCString(datetime.utcnow()-Datetime.Delta(**past))
    end = TimeStampUTCString(datetime.utcnow()+Datetime.Delta(**delta))
    oc = ObjectContainer(title2="Calendar")
    events = API_Request(endUrl='/calendar', params=dict(start=start,end=end))
    if events == None:
        return Invalid()
    for e in events:
        season = str(e['seasonNumber'])
        episode = str(e['episodeNumber'])
        dt = Datetime.ParseDate(e['airDateUtc'])+Dict['UTCOffset']
        if len(episode) ==  1: episode = '0'+episode
        title=PrettyDate(offset=dt)+' - '+e['series']['title']+' - '+season+'x'+episode
        e_title=e['title']
        e_overview=e['overview']
        summary=''
        if not e_title and not e_overview: summary = 'No information provided'
        elif not e_title: summary=e_overview
        elif not e_overview: summary=e_title
        else: summary=e_title+' - '+e_overview
        for coverType in e['series']['images']:
            if coverType['coverType'] == 'poster':
                image = coverType['url']
        show=dict(key=Callback(Stub), title=title, summary=summary, thumb=Callback(GetThumb, image=image))
        oc.add(DirectoryObject(**show))
    if len(oc) == 0:
        return ObjectContainer(header=NAME, message="No shows airing this week.")
    return oc

@route(PREFIX+"/history", page=int, pageSize=int)
def History(page=1,pageSize=19):
    oc = ObjectContainer(title2='History')
    history = API_Request(endUrl='/history', params=dict(page=page,pageSize=pageSize,sortKey='date',sortDir='desc'))
    if history == None:
        return Invalid()
    for r in history['records']:
        season = str(r['episode']['seasonNumber'])
        episode = str(r['episode']['episodeNumber'])
        dt = Datetime.ParseDate(r['date'])+Dict['UTCOffset']
        if len(episode) ==  1: episode = '0'+episode
        title=PrettyDate(offset=dt)+' - '+r['series']['title']+' - '+season+'x'+episode
        if r['eventType'] == 'downloadFolderImported':
            summary = 'Imported: '
            thumb=R(IMPORTED)
        elif r['eventType'] == 'downloadFailed':
            summary = 'Failed: '
            thumb=R(FAILED)
        elif r['eventType'] == 'grabbed':
            summary = 'Grabbed: '
            thumb=R(GRABBED)
        summary += r['episode']['title']
        record=dict(key=Callback(Stub), title=title, summary=summary, thumb=thumb)
        oc.add(DirectoryObject(**record))
    if len(oc) == 0:
        return ObjectContainer(header=NAME, message="No history")
    if page*pageSize < int(history['totalRecords']):
        oc.add(NextPageObject(key=Callback(History, page=page+1)))
    return oc

# NOT USED - Can't figure out what the REST API url is for 'missing'
@route(PREFIX+"/wanted", page=int, pageSize=int)
def Wanted(page=1,pageSize=19):
    oc = ObjectContainer(title2='Wanted')
    wanted = API_Request(endUrl='/missing', params=dict(page=page,pageSize=pageSize,sortKey='date',sortDir='desc'))
    if wanted == None:
        return Invalid()
    for r in wanted['records']:
        title=r['title']
        summary=PrettyHistory(datetime.utcnow(),Datetime.ParseDate(r['airDateUtc']).replace(tzinfo=None))
        record=dict(key=Callback(Stub), title=title, summary=summary)
        oc.add(DirectoryObject(**record))
    if len(oc) == 0:
        return ObjectContainer(header=NAME, message="No wanted items.")
    if page*pageSize < int(history['totalRecords']):
        oc.add(NextPageObject(key=Callback(Wanted, page=page+1)))
    return oc

@route(PREFIX+"/api")
def API_Request(endUrl,method='GET',params={}):
    headers = {'X-Api-Key': Prefs['API_Key']}
    request_url = Url()+'/api'+endUrl
    if len(params) > 0:
        request_url += "?"
        for k in params.keys():
            request_url += "%s=%s&" % (k, params[k])
        request_url = request_url.strip('&')
    try:
        data = JSON.ObjectFromURL(request_url, timeout=20, headers=headers)
    except:
        return None
    #data = JSON.ObjectFromURL(request_url, timeout=30, cacheTime=0, headers=headers)
    #Log.Info(str(data))
    return data

@route(PREFIX+'/url')
def Url():
    if Prefs['https']:
        protocol='https://'
    else:
        protocol='http://'
    return protocol+Prefs['IP']+':'+Prefs['Port']

@route(PREFIX+'/stub')
def Stub():
    return ObjectContainer(header=NAME, message="Stub method.")

@route(PREFIX+'/invalid')
def Invalid():
    return ObjectContainer(header=NAME, message="A problem occurred! Invalid API Key?")

# Convert a datetime to ISO-8601 formatted in UTC to send to NzbDrone
def TimeStampUTCString(time=datetime.utcnow()):
    return str(time.isoformat('T')).split('.')[0]+'Z'

# Nice relative dates
def PrettyDate(offset, date=Datetime.Now()):
    diff = offset.replace(tzinfo=None) - date
    if diff.days == 0:
        return 'Today'
    if diff.days == 1:
        return 'Tomorrow at ' + offset.strftime('%I:%M %p').lstrip('0')
    if diff.days > 1 and diff.days < 7:
        return offset.strftime('%A')+ ' at '+offset.strftime('%I:%M %p').lstrip('0')
    if diff.days == -1:
        return 'Yesterday'
    if diff.days < -1 and diff.days > -7:
        return offset.strftime('Last %A')
    else:
        return offset.strftime('%B %d')

@route(PREFIX+'/thumb')
def GetThumb(image):
    try:
        data = HTTP.Request(url=image, timeout=20, cacheTime=3600)
    except:
        pass
    return DataObject(data.content, 'image/jpeg')

