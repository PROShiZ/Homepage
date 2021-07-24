import json
import random
import requests
import ssl
import string
import urllib
import feedparser  # for rss only
from datetime import datetime
from dateutil  # adding custom timezones
from os.path import join

from bs4 import BeautifulSoup, SoupStrainer

from django.db import models
from Dashboard.models import keyValue


class feed(models.Model):
    class Meta:
        ordering = ['title']
    title = models.CharField(max_length=42)
    title_full = models.CharField(max_length=140, null=True)
    href = models.CharField(max_length=420)
    href_title = models.CharField(max_length=420, null=True)
    emojis = models.CharField(max_length=14, default='')  # using emojis as tags: 💎🏮📮
    # 💎 - parse each time and show in main feed
    # 🏮 - hidden from main feed
    # 📮 - parse less and show in main feed
    filter = models.CharField(max_length=140, null=True)
    delay = models.IntegerField(null=True)

    # to string
    def __str__(self):
        result = "["+self.title+"]"
        if self.title_full is not None:
            result += ": "+self.title_full
        if self.emojis is not None:
            result += " e: "+self.emojis
        if self.filter is not None:
            result += " f: "+self.filter
        if self.delay is not None:
            result += " d: "+str(self.delay)
        if self.href is not None:
            result += " href: "+self.href
        if self.href_title is not None:
            result += " href_title: "+self.href_title
        return result

    # return <feed> by feed.title
    @staticmethod
    def find(searched_title):
        return list(feed.objects.filter(title=searched_title))[0]

    # return List<feed> by emoji
    @staticmethod
    def feeds_by_emoji(emoji_filter='💎'):
        return list(feed.objects.filter(emojis__icontains=emoji_filter))

    # return List<feed> from feedUpdate/feeds.py
    def feeds_from_file():
        from .feeds import feeds
        return feeds

    def UserAgent_random():
        useragent = keyValue.objects.filter(key='UserAgentLen')[0]  # get UserAgent length
        useragent = random.randint(1, int(useragent.value))  # generate random value within length

        with open(join("static", "feedUpdate", 'user-agents.txt')) as useragent_file:
            return useragent_file.read().split('\n')[useragent-1]  # get UserAgent string

    @staticmethod
    def parse_reduce(emojis='', reduce=False):
        if not reduce:
            return True
        
        # higher is less requests
        rarity = 20_000
        if '💎' in emojis:
            rarity = rarity / 100
        elif '📮' in emojis:
            rarity = rarity / 20

        if not random.randint(0, int(rarity)):
            return True  # continue parsing

        return False  # break parse(), return []

    # return List<feedUpdate> parsed from source by <feed> (self)
    def parse(self, proxy=False, reduce=False):
        result = []

        # avoiding blocks
        headers = {
            'user-agent': feed.UserAgent_random().lstrip(),
            'referer': 'https://www.google.com/search?newwindow=1&q='+self.href
        }
        if proxy != False:
            proxyDict = {
                "http": "http://" + proxy, 
                "https": "https://" + proxy,
            }
        else:
            proxyDict = {}

        # custom ранобэ.рф API import
        if 'http://xn--80ac9aeh6f.xn--p1ai/' in self.href:
            request = f"https://xn--80ac9aeh6f.xn--p1ai/api/v2/books/{ self.href[31:-1] }/chapters"
            request = requests.get(request).json()  # (request, headers=headers, proxies=proxyDict)

            for each in request['items']:
                # ignoring payed chapters
                if each['availabilityStatus'] == 'free':
                    result.append(feedUpdate(
                        name=each["title"],
                        href="http://xn--80ac9aeh6f.xn--p1ai"+each["url"],
                        datetime=datetime.strptime(each["publishTime"], '%Y-%m-%d %H:%M:%S'),
                        title=self.title))

        # custom instagram import
        elif 'https://www.instagram.com/' in self.href:
            if not feed.parse_reduce(self.emojis, reduce):
                return []
            try:
                request = requests.get(self.href, headers=headers, proxies=proxyDict)
                request = BeautifulSoup(request.text, "html.parser")

                for each in request.find_all('script'):
                    data = 'window._sharedData = '
                    if str(each).find(data) != -1:
                        # preparing JSON
                        data = str(each).find(data) + len(data)  # data start position
                        data = str(each)[data:-10]  # -1 is for removing ; in the end
                        data = json.loads(data)

                        # selecting data from JSON
                        data = data['entry_data']['ProfilePage'][0]['graphql']
                        data = data['user']['edge_owner_to_timeline_media']['edges']

                        # parsing data from JSON
                        for each in data:
                            # avoiding errors caused by empty titles
                            try:
                                result_name = each['node']['edge_media_to_caption']['edges'][0]['node']['text']
                            except IndexError:
                                result_name = 'no title'

                            result.insert(0, feedUpdate(
                                name=result_name,
                                href="http://instragram.com/p/"+each['node']['shortcode'],
                                datetime=datetime.fromtimestamp(each['node']['taken_at_timestamp']),
                                title=self.title))
            except (KeyError, requests.exceptions.ProxyError, requests.exceptions.SSLError):
                return []

        # custom tiktok import
        elif 'https://www.tiktok.com/@' in self.href:
            if not feed.parse_reduce(self.emojis, reduce):
                return []

            request = requests.get(self.href, headers=headers, proxies=proxyDict)
            request = BeautifulSoup(request.text, "html.parser")

            data = str(request.find('script', attrs={'id': '__NEXT_DATA__'}))
            data_start = data.find('>') + 1
            data_end = data.find('</script>')

            data = data[data_start:data_end]
            data = json.loads(data)
            
            for each in data['props']['pageProps']['items']:
                # if each['isAd']:
                #     continue

                result.insert(0, feedUpdate(
                    name=each['desc'],
                    href=f"{ self.href }/video/{ each['id'] }",
                    # href=each['video']['playAddr'],
                    datetime=datetime.fromtimestamp(each['createTime']),
                    title=self.title))

        # custom RSS YouTube converter (link to feed has to be converted manually)
        elif 'https://www.youtube.com/channel/' in self.href:
            self.href_title = self.href[:]
            # 32 = len('https://www.youtube.com/channel/')
            # 7 = len('/videos')
            self.href = "https://www.youtube.com/feeds/videos.xml?channel_id=" + self.href[32:-7]
            result = feed.parse(self)

        # custom RSS readmanga converter (link to feed has to be converted manually to simplify feed object creation)
        elif 'http://readmanga.me/' in self.href and self.href.find('readmanga.me/rss/manga') == -1 and self.href_title == None:
            # 20 = len('http://readmanga.me/')
            self.href = "feed://readmanga.me/rss/manga?name=" + self.href[20:]
            result = feed.parse(self)

        # custom RSS mintmanga converter (link to feed has to be converted manually to simplify feed object creation)
        elif 'http://mintmanga.com/' in self.href and self.href.find('mintmanga.com/rss/manga') == -1 and self.href_title == None:
            # 21 = len('http://mintmanga.com/')
            self.href = "feed://mintmanga.com/rss/manga?name=" + self.href[21:]
            result = feed.parse(self)

        # custom RSS deviantart converter (link to feed has to be converted manually to simplify feed object creation)
        elif 'https://www.deviantart.com/' in self.href:
            self.href_title = self.href[:]
            # 27 = len('https://www.deviantart.com/')
            # 9 = len('/gallery/')
            self.href = self.href[27:-9]
            self.href = "http://backend.deviantart.com/rss.xml?q=gallery%3A" + self.href
            result = feed.parse(self)

        # custom fantasy-worlds.org loader
        elif 'https://fantasy-worlds.org/series/' in self.href:
            strainer = SoupStrainer('div', attrs={'class': 'rightBlock'})

            request = requests.get(self.href, headers=headers, proxies=proxyDict)
            request = BeautifulSoup(request.text, "html.parser", parse_only=strainer)

            for each in request.find('ul').find('li').find('ul').find('li').find('ul').find_all('li'):
                result.append(feedUpdate(
                    name=f"{self.title} {each.text[:each.text.find(' // ')]}",
                    href=each.find('a')['href'],
                    datetime=datetime.now(),  # <=== fake date
                    title=self.title))

        # custom pikabu import
        elif 'pikabu.ru/@' in self.href:
            # try:
            strainer = SoupStrainer('div', attrs={'class': 'stories-feed__container'})

            try:
                request = requests.get(self.href, headers=headers, proxies=proxyDict)
            except requests.exceptions.SSLError:
                return []
            request = BeautifulSoup(request.text, "html.parser", parse_only=strainer)

            for each in request.find_all('article'):
                try:
                    result_datetime = each.find('time')['datetime'][:-3]+"00"
                    result_datetime = datetime.strptime(result_datetime, '%Y-%m-%dT%H:%M:%S%z')

                    result.append(feedUpdate(
                        name=each.find('h2', {'class': "story__title"}).find('a').getText(),
                        href=each.find('h2', {'class': "story__title"}).find('a')['href'],
                        datetime=result_datetime,
                        title=self.title))

                except (TypeError, AttributeError) as err:
                    # advertisement, passing as no need to save it
                    pass
            # except (requests.exceptions.ConnectionError, requests.exceptions.SSLError) as err:
            #     # failed connection, hope it works from time to time
            #     return []

        # # custom fanserials parser
        # elif self.href.find('http://fanserial.net/') != -1 and self.filter is not None:
        #     strainer = SoupStrainer('ul', attrs={'id': 'episode_list'})
        #
        #     request = requests.get(self.href, headers=headers, proxies=proxyDict)
        #     request = BeautifulSoup(request.text, "html.parser", parse_only=strainer)
        #     print(request)
        #
        #     for each in request.find_all('li'):
        #         print(each)
        #         result_href = ''
        #         for each_span in each.find('div').find('div', attrs={'class': 'serial-translate'}).find_all('span'):
        #             result_href = 'http://fanserial.tv' + each_span.find('a').get('href')
        #
        #         result.append(feedUpdate(
        #             name=each.find('div', attrs={'class': 'field-description'}).find('a').text,
        #             href=result_href,
        #             datetime=datetime.now(),  # <=== fake date
        #             title=self.title))

        # custom onlyfans import
        elif 'https://onlyfans.com/' in self.href:
            return []
        
        # custom patreon import
        elif 'https://www.patreon.com/' in self.href:
            return []

        # default RSS import
        else:
            proxyDict = urllib.request.ProxyHandler(proxyDict)

            try:
                request = feedparser.parse(self.href, request_headers=headers, handlers=[proxyDict])
            except urllib.error.URLError:
                ssl._create_default_https_context = ssl._create_unverified_context
                request = feedparser.parse(self.href, request_headers=headers, handlers=[proxyDict])

            for each in request["items"]:
                result_href = each["links"][0]["href"]

                # DATE RESULT: parsing dates
                if "published" in each:
                    result_datetime = each["published"]
                elif "updated" in each:
                    result_datetime = each["updated"]
                else:
                    print(f"result_datetime broke for { self.title }")
                
                tzinfos = {
                    'PDT': dateutil.tz.gettz("America/Los_Angeles"),
                    'PST': dateutil.tz.gettz("America/Juneau"),
                }
                if not isinstance(result_datetime, datetime):
                    result_datetime = dateutil.parser.parse(result_datetime, tzinfos=tzinfos)

                # APPEND RESULT
                result.append(feedUpdate(
                    name=each["title_detail"]["value"],
                    href=result_href,
                    datetime=result_datetime,
                    title=self.title))

        # universal postfixes
        result_filtered = []
        for each in result:
            # FILTERING: passing item cycle if filter does not match
            if self.filter is not None:
                if each.name.find(self.filter) == -1 and each.href.find(self.filter) == -1:
                    continue

            # DATETIME fixes
            # fix timezone unaware
            # if each.datetime.tzinfo is not None and each.datetime.tzinfo.utcoffset(each.datetime) is not None:
            #     each_dt = localtime(each.datetime)
            #     each.datetime = datetime(each_dt.year, each_dt.month, each_dt.day,
            #          each_dt.hour, each_dt.minute, each_dt.second)
                     
            # if each.datetime.tzinfo is not None and each.datetime.tzinfo.utcoffset(each.datetime) is not None:
            #     print("!!!! WARNING !!!!")
            # # add DELAY
            # if type(self.delay) is not type(None):
            #     each.datetime += timedelta(hours=self.delay)

            # NAME fixes
            each.name = ' '.join(each.name.split())
            each.name = each.name[:140]  # SQLite does not support max-length
            # extra symbols
            if each.title == 'Shadman':
                each.name = each.name[:each.name.find('(')-1]
            elif each.title == 'Apple' and each.name[-len('Apple'):] == 'Apple':
                # - symbol can be a variety of different symbols
                # 8 = len(' - Apple')
                each.name = each.name[:-8]
            elif each.title == 'LastWeekTonight':
                end = each.name.find(': Last Week Tonight with John Oliver (HBO)')
                if end != -1:
                    each.name = each.name[:end]

            result_filtered.append(each)

        return result_filtered


class feedUpdate(models.Model):
    class Meta:
        ordering = ['-datetime']
    name = models.CharField(max_length=140)
    href = models.CharField(max_length=420)
    datetime = models.DateTimeField()
    title = models.CharField(max_length=42)

    def __str__(self):
        return "["+self.title+"]: "+self.name+" d: "+str(self.datetime)+" with link "+self.href