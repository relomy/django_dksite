from django.core.management.base import BaseCommand

import results.parsers.dkcontests as dkcontests_parser
import results.parsers.dkresults as dkresults_parser
import results.parsers.dksalaries as dksalaries_parser
from results.utils import get_contest_ids, get_empty_contest_ids


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--dk-salaries",
            action="store_true",
            dest="dk_salaries",
            default=False,
            help="Fetch today's salary data from draftkings.com",
        )
        parser.add_argument(
            "--sport",
            "-s",
            required=True,
            action="store",
            dest="sport",
            help="Sport name to pass to run()",
        )
        parser.add_argument(
            "--dk-new-contests",
            "-nc",
            action="store_true",
            dest="dk_new_contests",
            default=False,
            help="Fetch today's new contests from draftkings.com",
        )
        parser.add_argument(
            "--update",
            "-u",
            action="store_true",
            dest="update",
            default=False,
            help="Update game, injury, and contest result data",
        )

    def handle(self, *args, **options):
        if options["update"]:
            # dksalaries_parser.find_new_contests()
            # injury_parser.run()
            # dksalaries_parser.run()
            dkresults_parser.run(
                contest_ids=get_empty_contest_ids(),
                contest=True,
                resultscsv=True,
                resultsparse=True,
            )
        else:
            if options["dk_salaries"]:
                dksalaries_parser.run(options["sport"])
            if options["dk_new_contests"]:
                dkcontests_parser.find_new_contests(options["sport"])
