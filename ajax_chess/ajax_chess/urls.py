"""
URL configuration for ajax_chess project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from chess_application import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('about/',views.about,name="about"),
    path('rules/',views.rules,name='rules'),
    path('history',views.history,name='history'),
    path('join/', views.join, name='join'),
    path('login/', views.login, name='login'),
    path('logout/',views.logout, name='logout'),
    path('home/',views.home, name='home'),
    

    path('home/get_available_users/',views.get_available_users,name="get_available_users"),
    path('game/<int:game_id>/revoke/',views.revoke_invitation,name='revoke_invitation'),
    path('home/get_pending_invitations/',views.get_pending_invitations,name="get_pending_invitations"),
    path('home/get_sent_invitations/', views.get_sent_invitations, name='get_sent_invitations'),
    path('game/<int:game_id>/',views.game, name='game'),
    path('home/respond/<int:game_id>',views.respond_invitation, name='respond_invitation'),
    # path('game/<int:game_id>/edit_game/', views.edit_game, name='edit_game'),
    path('game/<int:game_id>/journal/edit/', views.edit_game,name='edit_game'),
    # path('game/<int:game_id>/journal/delete/',views.delete_journal,name='delete_journal'),
    path('game/<int:game_id>/delete/',views.delete_game, name='delete_game'),
    path('game/<int:game_id>/resign/',views.resign_game, name='resign_game'),

    path('make_move/<int:game_id>/',views.makeMove, name='make_move'),
    path('game/check_game_status/<int:game_id>/',views.check_game_status,name="check_game_status"),
    # path('gameHistory/',views.gameHistory, name='gameHistory'),


    path("",views.default,name='default')
    # path('',views.default,name='default')

]
