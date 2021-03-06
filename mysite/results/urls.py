from django.urls import path

from . import views

urlpatterns = [
    # ex: /results/
    path("", views.index, name="results-index"),
    # ex /results/dkcontests
    # path("dkcontests", views.index, name="index"),
    # ex: /polls/5/
    path("<int:contest_id>/", views.detail, name="detail"),
    # # ex: /polls/5/results/
    # path("<int:question_id>/results/", views.results, name="results"),
    # # ex: /polls/5/vote/
    # path("<int:question_id>/vote/", views.vote, name="vote"),
]
