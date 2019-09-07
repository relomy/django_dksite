import datetime
import logging
import re

import browsercookie
import requests
from django.utils.timezone import make_aware

from results.models import DKContest

logger = logging.getLogger(__name__)

COOKIES = browsercookie.chrome()
HEADERS = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Host": "www.draftkings.com",
    "Pragma": "no-cache",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/48.0.2564.97 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
}


class Contest:
    def __init__(self, contest):
        self.start_date = contest["sd"]
        self.name = contest["n"]
        self.id = contest["id"]
        self.draft_group = contest["dg"]
        self.total_prizes = contest["po"]
        self.entries = contest["m"]
        self.entry_fee = contest["a"]
        self.entry_count = contest["ec"]
        self.max_entry_count = contest["mec"]
        self.is_guaranteed = False
        self.is_double_up = False

        self.start_dt = self.get_dt_from_timestamp(self.start_date)

        if "IsDoubleUp" in contest["attr"]:
            self.is_double_up = contest["attr"]["IsDoubleUp"]

        if "IsGuaranteed" in contest["attr"]:
            self.is_guaranteed = contest["attr"]["IsGuaranteed"]

    @staticmethod
    def get_dt_from_timestamp(timestamp: str):
        timestamp = float(re.findall(r"[^\d]*(\d+)[^\d]*", timestamp)[0])
        return datetime.datetime.fromtimestamp(timestamp / 1000)

    def __str__(self):
        # return f"{vars(self)}"
        return f"{self.name} [{self.id}] [{self.start_dt}]"


def get_largest_contest(contests, entry_fee=25, query=None, exclude=None):
    """Return largest contest from a list of Contests."""
    logger.debug("contests size: %d", len(contests))

    # add contest to list if it matches criteria
    contest_list = [
        c for c in contests if match_contest_criteria(c, entry_fee, query, exclude)
    ]

    logger.debug("number of contests meeting requirements: %d", len(contest_list))

    # sorted_list = sorted(contest_list, key=lambda x: x.entries, reverse=True)
    if contest_list:
        return max(contest_list, key=lambda x: x.entries)

    return None


def match_contest_criteria(contest, entry_fee=25, query=None, exclude=None):
    """Use arguments to filter contest criteria.
    """
    if (
        contest.max_entry_count == 1
        and contest.entry_fee == entry_fee
        and contest.is_double_up
        and contest.is_guaranteed
    ):
        # if exclude is in the name, return false
        if exclude and exclude in contest.name:
            return False

        # if query is not in the name, return false
        if query and query not in contest.name:
            return False

        return True

    return False


def get_contests(url):
    logger.info("url: %s", url)

    response = requests.get(url, headers=HEADERS, cookies=COOKIES).json()
    response_contests = {}
    if isinstance(response, list):
        response_contests = response
    elif "Contests" in response:
        response_contests = response["Contests"]
    else:
        raise Exception("response isn't a dict or a list???")

    return response_contests


def find_new_contests(sport):
    """
    Maybe this belongs in another module
    """

    # def get_pst_from_timestamp(timestamp_str):
    #     timestamp = float(re.findall("[^\d]*(\d+)[^\d]*", timestamp_str)[0])
    #     return datetime.datetime.fromtimestamp(
    #         timestamp / 1000, timezone("America/Los_Angeles")
    #     )

    url = f"https://www.draftkings.com/lobby/getcontests?sport={sport}"

    # response = requests.get(url, headers=HEADERS, cookies=COOKIES).json()
    response_contests = get_contests(url)

    # create list of Contest objects
    contests = [Contest(c) for c in response_contests]
    # contests = [
    #     get_largest_contest(response["Contests"], 3),
    #     get_largest_contest(response["Contests"], 0.25),
    #     get_largest_contest(response["Contests"], 27),
    # ] + get_contests_by_entries(response["Contests"], 3, 50000)
    target_contests = []
    entry_fees = []
    if sport == "NFL":
        entry_fees = [5, 10, 25, 50]
    else:
        entry_fees = [10, 25]

    for entry_fee in entry_fees:
        largest_contest = get_largest_contest(contests, entry_fee=entry_fee)
        # check if largest_contest is None
        if largest_contest is not None:
            logger.debug("Appending contest %s", largest_contest)
            target_contests.append(largest_contest)

    for contest in target_contests:
        date_time = contest.start_dt
        # make naive datetime aware based on django settings
        aware_datetime = make_aware(date_time)
        dkcontest, created = DKContest.objects.update_or_create(
            dk_id=contest.id,
            defaults={
                "date": aware_datetime.date(),
                "datetime": aware_datetime,
                "sport": sport,
                "name": contest.name,
                "draft_group_id": contest.draft_group,
                "total_prizes": contest.total_prizes,
                "entries": contest.entries,
                "entry_fee": contest.entry_fee,
            },
        )
        if created:
            logger.info("Creating DKContest %s", dkcontest)
