from django.conf.urls import url
from . import views

app_name = "feedUpdate"
urlpatterns = [
    url(r'^$', views.feedUpdateDefaultIndexView.as_view(), name="index"),  # main fU feed with modes
    url(r'^(?P<feed>(index|other|all)):(?P<mode>(index|force|more))$', views.feedUpdateIndexView.as_view(), name="feed"),
    url(r'^(?P<feed>([0-9|а-я|ё|А-Я|Ё|a-z|A-Z|_|+|—])*):(?P<mode>(index|more|force))?$', views.feedUpdateIndexView.as_view(), name="filter"),

    # pages
    url(r'^feeds:(?P<mode>(index|other|all))$', views.feedIndexView.as_view(), name="feeds"),  # list feeds
    url(r'^rss$', views.feedUpdateFeed(), name="rss"),  # RSS feed
    url(r'^tests$', views.feedTestsView.as_view(), name="tests"),  # testing page
    
]
