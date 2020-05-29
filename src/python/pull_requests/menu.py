import itertools
from typing import List, Dict

from .config import PullRequestsConstants
from .domain import PullRequest, PullRequestSort, PullRequestStatus, PullRequestsOverview, PullRequestException
from .notification import send_notification_pr
from ..common.config import get_logger
from ..common.icons import Icon, Icons
from ..common.util import get_absolute_path_to_repo_file

logger = get_logger(__name__)
open_multiple_urls = get_absolute_path_to_repo_file('src/open-multiple-urls.sh')


def sort_pull_requests(pull_requests: List[PullRequest], sort_on: PullRequestSort):
    return sorted(pull_requests, key=lambda p: p.activity,
                  reverse=True) if sort_on == PullRequestSort.ACTIVITY else sorted(pull_requests,
                                                                                   key=lambda p: p['title'])


def determine_repo_status(prs_list: List[PullRequest]):
    statuses = [_pr.overall_status for _pr in prs_list]

    if PullRequestStatus.REJECTED in statuses:
        return PullRequestStatus.REJECTED
    elif PullRequestStatus.UNAPPROVED in statuses or PullRequestStatus.NO_VOTE in statuses:
        return PullRequestStatus.UNAPPROVED
    elif PullRequestStatus.NEEDS_WORK in statuses or PullRequestStatus.WAITING_FOR_AUTHOR in statuses:
        return PullRequestStatus.NEEDS_WORK
    else:  # Approved / Approved with suggestions
        return PullRequestStatus.APPROVED


def print_prs(
        pr_type,
        pull_requests: List[PullRequest],
        sort_on: PullRequestSort,
        section_icon: Icon,
        status_icons: Dict[PullRequestStatus, Icon]):
    print(f"{pr_type} | templateImage={section_icon.base64_image}")
    print("---")

    prs_sorted_by_slug = sorted(pull_requests, key=lambda p: p.slug)

    for repo, repo_prs in itertools.groupby(prs_sorted_by_slug, key=lambda p: p.slug):
        repo_prs_list: List[PullRequest] = list(repo_prs)
        repo_status = determine_repo_status(repo_prs_list)
        repo_href = repo_prs_list[0].all_prs_href
        print(f"{repo} ({str(len(repo_prs_list))}) | href={repo_href} image={status_icons[repo_status].base64_image}")

        prs_sorted_by_to_ref = sorted(repo_prs_list, key=lambda p: p.to_ref)

        pr_urls = list()

        for to_ref, to_ref_prs in itertools.groupby(prs_sorted_by_to_ref, key=lambda p: p.to_ref):
            to_ref_prs_list: List[PullRequest] = sort_pull_requests(list(to_ref_prs), sort_on)
            print(f"--{to_ref}")

            for _pr in to_ref_prs_list:
                print(f"--{_pr.from_ref} -- {_pr.title} (#{_pr.id}) - {_pr.time_ago}" +
                      f"|href={_pr.href} image={status_icons[_pr.overall_status].base64_image}")

                pr_urls.append(_pr.href)

        # Alternate click (option click to open all)
        print(
            (f"{repo} (open {str(len(repo_prs_list))} PRs) |"
             "alternate=true "
             f"image={status_icons[repo_status].base64_image} "
             f"bash={open_multiple_urls} param1='{' '.join(pr_urls)}' "
             "terminal=false"
             )
        )


def print_bitbar_pull_request_menu(
        pr_overview: PullRequestsOverview,
        pr_statuses: Dict[PullRequestStatus, Icon],
        sort_on: PullRequestSort,
        cache_file: str,
        notifications_enabled: bool
):
    total_prs_to_review = len(pr_overview.prs_to_review)
    total_prs_authored_with_work = len(pr_overview.prs_authored_with_work)
    total_prs = total_prs_to_review + total_prs_authored_with_work

    if total_prs > 0:
        print(f"{str(total_prs)} | templateImage={Icons.PULL_REQUEST.base64_image}")

        if total_prs_to_review > 0:
            print("---")
            print_prs("Reviewing", pr_overview.prs_to_review, sort_on, Icons.REVIEW, pr_statuses)

        if total_prs_authored_with_work > 0:
            print("---")
            print_prs("Authored", pr_overview.prs_authored_with_work, sort_on, Icons.AUTHORED, pr_statuses)

        if len(pr_overview.exceptions) > 0:
            print_and_log_exceptions(pr_overview.exceptions)

        if notifications_enabled:
            previous_pr_status = PullRequestsOverview.load_cached(cache_file)
            new, changed = pr_overview.determine_new_and_changed_pull_requests_to_review(previous_pr_status)
            for pr in new:
                send_notification_pr("New", pr.slug, pr.from_ref, pr.to_ref, pr.title, pr.href)

            for pr in changed:
                send_notification_pr("Changed", pr.slug, pr.from_ref, pr.to_ref, pr.title, pr.href)

        pr_overview.store(cache_file)
    elif total_prs == 0 and len(pr_overview.exceptions) == 0:
        print(f"0 | templateImage={Icons.PULL_REQUEST.base64_image}")
        print("---")
        print(f"Nothing to review 🎉 | templateImage={PullRequestsConstants.NO_PULL_REQUESTS.base64_image}")
        pr_overview.store(cache_file)
    else:
        print(f"? | templateImage={Icons.PULL_REQUEST.base64_image}")
        print_and_log_exceptions(pr_overview.exceptions)


def print_and_log_exceptions(exceptions: List[PullRequestException]):
    for exception in exceptions:
        logger.error(exception.exception)
        logger.error(exception.traceback)
        print("---")
        print(f"{exception.source} error: {exception.message}")
