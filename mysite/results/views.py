from django.http import Http404
from django.shortcuts import render

from .models import DKContest


# Create your views here.
def index(request):
    contests = DKContest.objects.order_by("-date")
    context = {"contests": contests}
    return render(request, "results/index.html", context)


def detail(request, contest_id):
    try:
        contest = DKContest.objects.get(pk=contest_id)
        results = contest.results.order_by("rank")
        ownership = contest.ownership.order_by("-ownership")
    except contest.DoesNotExist:
        raise Http404("DKContest does not exist")
    return render(
        request,
        "results/detail.html",
        {"contest": contest, "results": results, "ownership": ownership},
    )
