# from django.shortcuts import render
from .models import feedUpdate, feed
from django.views.generic import ListView
from django.contrib.syndication.views import Feed
# import socket
# from django.shortcuts import redirect
# from django.urls import reverse
from django.db.models import Count
import re


# TODO: exchange with normal testing
class feedTestsView(ListView):
    model = feedUpdate
    template_name = "feedUpdate/tests.html"
    context_object_name = "fromView"

    def get_queryset(self):
        # constants
        header = "Результаты тестирования"
        # TODO: good testing page

        # calculations
        feed_list = feed.objects.all()

        # feed testing
        errors_regexp = []
        pattern = re.compile("^([0-9|а-я|ё|А-Я|Ё|a-z|A-Z|_|+|—])+$")
        for each in feed_list:
            if not pattern.match(each.title):
                errors_regexp.append(each.title)

        errors_duplicates = []
        for each in feed.objects.values('title').annotate(name_count=Count('title')).filter(name_count__gt=1):
            errors_duplicates.append(each['title'] + " x" + str(each['name_count']) + "; ")

        # results
        return {
            'page': {
                'title': header,
            },
            'errors': {
                'regexp': errors_regexp,
                'duplicates': errors_duplicates,
            }
        }


# shows List<Feed> with modes: index (SFW) / other (NSFW) / all (SFW+NSFW)
class feedIndexView(ListView):
    model = feedUpdate
    template_name = "feedUpdate/feeds.html"
    context_object_name = "fromView"

    def get_queryset(self):
        # constants
        header = "Ленты обновлений"

        # calculations
        if self.kwargs.get('mode', False) == "index":
            feed_list = feed.objects.exclude(emojis__contains='🏮')
        elif self.kwargs.get('mode', False) == "other":
            feed_list = feed.objects.filter(emojis__contains='🏮')
        elif self.kwargs.get('mode', False) == "all":
            feed_list = feed.objects.all()

        # results
        return {
            'page': {
                'title': header,
            },
            'feed_list': list(feed_list),
        }


# shows List<FeedUpdate>: index:index
class feedUpdateDefaultIndexView(ListView):
    model = feedUpdate
    template_name = "feedUpdate/index.html"
    context_object_name = "fromView"

    def get_queryset(self):
        # constants
        page_title = "Обновления"
        page_display_titles = True
        result_size_limit = 140

        # calculations
        feeds = feed.objects.filter(emojis__icontains='💎').exclude(emojis__icontains='🏮')
        feed_list = [ x.title for x in feeds ]
        
        feedUpdate_list = feedUpdate.objects.filter(title__in=feed_list)[:result_size_limit]

        # results
        return {
            'page': {
                'title': page_title,
                'display_titles': page_display_titles,
            },
            'feedUpdate_list': feedUpdate_list,
        }


# shows List<FeedUpdate>
# filters: index (SFW) / other (NSFW) / all (SFW+NSFW)
# modes: index (parsed) / more (index, but more items) / force (parse)
class feedUpdateIndexView(ListView):
    model = feedUpdate
    template_name = "feedUpdate/index.html"
    context_object_name = "fromView"

    def get_queryset(self):
        # constants
        page_display_titles = True
        result_size_limit = 140

        # page_title
        title_feed = self.kwargs.get('feed')
        title_mode = self.kwargs.get('mode')

        # feed_list
        feed_list = []
        if self.kwargs.get('feed', False) == 'index':
            feed_list = feed.objects.filter(emojis__icontains='💎').exclude(emojis__icontains='🏮')
        elif self.kwargs.get('feed', False) == 'other':
            feed_list = feed.objects.filter(emojis__icontains='💎').filter(emojis__icontains='🏮')
        elif self.kwargs.get('feed', False) == 'all':
            feed_list = feed.objects.filter(emojis__icontains='💎')
        else:
            feed_list = self.kwargs['feed'].split("+")
            feed_list = feed.objects.filter(title__in=feed_list)
            
            title_feed = "+".join([ x.title for x in feed_list ])
            # page_title += ":"+ title_mode
            
            feed_list_len = len(feed_list)
            if feed_list_len == 0:
                raise Exception("Manual error. No correct filter indicated")
            elif feed_list_len == 1:
                page_display_titles = False

        feed_list = [ x.title for x in feed_list ]
        
        # feedUpdate_list
        feedUpdate_list = []
        if self.kwargs.get('mode', False) == 'index':
            feedUpdate_list = feedUpdate.objects.filter(title__in=feed_list)[:result_size_limit]
        elif self.kwargs.get('mode', False) == 'more':
            feedUpdate_list = feedUpdate.objects.filter(title__in=feed_list)[:result_size_limit*10]
        elif self.kwargs.get('mode', False) == 'force':
            for each in feed_list:
                each = feed.objects.get(title=each)
                each = each.parse()
                feedUpdate_list.extend( each )

            feedUpdate_list.sort(key=lambda feedUpdate_list_item: str(feedUpdate_list_item.datetime), reverse=True)

        # results
        return {
            'page': {
                'title': title_feed +":"+ title_mode,
                'display_titles': page_display_titles,
            },
            'feed_name': title_feed,
            'feedUpdate_list': feedUpdate_list,
        }


# RSS feed
class feedUpdateFeed(Feed):
    title = "Обновления RSS"
    link = "/feedUpdate/rss"
    description = "RSS feed of items shown at feedUpdate main page"

    def items(self):
        items_limit = 42

        feed_titles = []

        for each in feed.feeds_by_emoji():
            feed_titles.append(each.title)
        feedUpdate_list = list(feedUpdate.objects.filter(title__in=feed_titles)[:items_limit])

        return feedUpdate_list

    def item_title(self, item):
        return item.title + ": " + item.name

    def item_description(self, item):
        result = item.title + ": " + item.name
        return result

    def item_link(self, item):
        return item.href
