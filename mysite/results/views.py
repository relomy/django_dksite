import logging

from django.http import Http404
from django.shortcuts import render

from .models import DKContest, DKSalary

logger = logging.getLogger(__name__)

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
        logger.debug("contest.draft_groupid = %s", contest.draft_group_id)
        salary = DKSalary.objects.filter(draft_group_id__exact=contest.draft_group_id)
        salary_dict = {s.player.name: s.salary for s in salary}

        for row in ownership:
            if row.player.name in salary_dict:
                row.player.salary = salary_dict[row.player.name]
            else:
                row.player.salary = 0
    except contest.DoesNotExist:
        raise Http404("DKContest does not exist")
    return render(
        request,
        "results/detail.html",
        {"contest": contest, "results": results, "ownership": ownership},
    )
