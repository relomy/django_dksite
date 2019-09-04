import datetime
from results.models import DKContest


def get_datetime_yearless(datestr):
    """
    Return a date from a datestring. Make sure that it wraps around to the
    previous year if the datestring is greater than the current date (e.g.
    data for Dec 31 when 'today' is Jan 1).
    @param datestr [str]: [Month] [Date] (e.g. 'Nov 11')
    @return [datetime.date]
    """
    date = datetime.datetime.strptime(datestr, "%b %d").date()
    year = datetime.date.today().year
    date = date.replace(year=year)
    return (
        date
        if date <= datetime.date.today()
        else datetime.date(year - 1, date.month, date.day)
    )


def get_empty_contest_ids(sport):
    """
    Returns a list of contest ids for contests that are missing results data
    """
    contest_ids = []
    today = datetime.date.today()
    last = today - datetime.timedelta(days=7)
    contests = DKContest.objects.filter(date__gte=last, sport__exact=sport)
    for contest in contests:
        num_results = contest.results.count()
        print(
            f"{contest.entries} entries expected for [{contest.dk_id}] {contest.name} "
            f"[{contest.date}], {num_results} found"
        )
        if num_results == 0:
            contest_ids.append(contest.dk_id)
    print("Contest ids: {}".format(", ".join(contest_ids)))
    return contest_ids


def get_contest_ids(sport, limit=1, entry_fee=None):
    """
    Returns a list of contest ids for the last @limit days with an optional
    additional @entry_fee filter
    """
    contest_ids = []
    today = datetime.date.today()
    last = today - datetime.timedelta(days=limit)
    contests = (
        DKContest.objects.filter(
            sport__exact=sport, date__gte=last, entry_fee=entry_fee
        )
        if entry_fee
        else DKContest.objects.filter(sport__exact=sport, date__gte=last)
    )
    contest_ids = [contest.dk_id for contest in contests]
    print("Contest ids: {}".format(", ".join(contest_ids)))
    return contest_ids


# class Timer:
#     @classmethod
#     def log_elapsed_time(cls, s, prev_time):
#         curr_time = time.time()
#         print("[Elapsed time] {}: {}".format(s, curr_time - prev_time))
#         return curr_time
