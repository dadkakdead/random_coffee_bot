from django.urls import path

from django.conf.urls import url

from . import views
from django.views.generic import RedirectView

from rest_framework.urlpatterns import format_suffix_patterns

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from django.contrib.auth import views as auth_views


urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico')),

    path('', RedirectView.as_view(url='/schedule')),
    path('schedule/', views.schedule, name='Schedule'),

    url(r'^api/shuffle_meetings', views.shuffle_meetings, name='Shuffle'),
    url(r'^api/resend_invitation', views.resend_invitation, name='Re-invite'),
    url(r'^api/connect_participants', views.connect_participants, name='Broadcast'),
    url(r'^api/collect_feedback', views.collect_feedback, name='Make survey'),

    url(r'^accounts/login/$', auth_views.LoginView.as_view()),
    url(r'^accounts/logout/$', auth_views.LogoutView.as_view()),
    url(r'^accounts/profile/$', RedirectView.as_view(url='/home')),

    url(r'(?P<bot_token>.+?)/$', views.webhook, name='webhook'),
]

handler404 = 'connector.views.handler404'
handler500 = 'connector.views.handler500'

# Returns a URL pattern list which includes format suffix patterns appended to each of the URL patterns provided.
# Only userful for API
urlpatterns = format_suffix_patterns(urlpatterns)
