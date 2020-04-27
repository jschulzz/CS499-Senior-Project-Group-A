# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth.models import User as account
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from .tokens import account_activation_token
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import EmailMessage
from django.contrib.auth import login
from .tasks import *
from .forms import SignUpForm, ProfileForm
from datetime import datetime, timedelta
import pytz
import csv
import os
import pprint
import textstat
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


currentTwitterSearchDict = (
    {}
)  # dictionary with parameters to search twitter by in array form
tweetsList = []  # list of tweets to dispaly on website
dbSearchDict = (
    {}
)  # dictioanry of search fields parameters (so they can be saved and redisplayed when user changes pages or downloads)
pullParameters = (
    {}
)  # dictionary with parameters to search twitter by in string form (to display in website)

# define lambda functions for custom sorting
sortingFunctions = {
        'Date Created': lambda k: k.createdAt,
        'Retweets': lambda k: k.numRetweetsNew if k.numRetweetsNew else k.numRetweetsOriginal,
        'Favorites': lambda k: k.numFavoritesNew if k.numFavoritesNew else k.numFavoritesOriginal
}

# the search field is for users, hashtags, and keywords, so we will split those up
def splitSearch(keywords):
    if keywords is None:
        return [], [], []
    terms = [x.strip() for x in keywords.split(",")]
    users = [x.split("@")[1] for x in terms if "@" in x]
    hashtags = [x.split("#")[1] for x in terms if "#" in x]
    keywords = [x for x in terms if "@" not in x if "#" not in x]
    return users, hashtags, keywords


def pagify(tweetsList, limit, request):
    # only display x tweets per page
    paginator = Paginator(tweetsList, limit)
    page = request.GET.get("page")
    return paginator.get_page(page)


def renderIndexPage(request, tweets, pullStatus, error=None, warning=None):
    global pullParameters, dbSearchDict

    if dbSearchDict["keywords"] == ['']:
        dbSearchDict["keywords"] = None
    return render(
        request,
        "index.html",
        {
            "tweets": tweets,
            "twitterSearchDict": pullParameters,
            "dbSearchDict": dbSearchDict,
            "sortFields": sortingFunctions.keys(),
            "pulling": pullStatus,
            "warning": warning,
            "error": error,
        },
    )


# home page controller
def index(request):
    global currentTwitterSearchDict, tweetsList, pullParameters
    if not request.user.is_authenticated:
        return redirect("/login")
        # refresh
    if request.GET.get("refresh"):  # refresh page aka display all tweets from db again
        if request.GET.get("refresh") == "true":
            return redirect("/scotustwitter")

    # get what users entered into search bars (so we can redisplay them in the search bars when a download occurs)
    if request.GET.get("keywords"):
        users, hashtags, keywords = splitSearch(request.GET.get("keywords"))
        dbSearchDict["users"] = users
        dbSearchDict["hashtags"] = hashtags
        dbSearchDict["keywords"] = keywords

    # bot criteria
    if request.GET.get("botMax"):
        dbSearchDict["botMax"] = request.GET.get("botMax")
    if bool(request.GET.get("showUnscoredUsers", False)):
        dbSearchDict["showUnscoredUsers"] = True

    # sort criteria
    if request.GET.get("sortBy"):
        dbSearchDict["sortBy"] = request.GET.get("sortBy")
    if request.GET.get("sortOrder"):
        dbSearchDict["sortOrder"] = request.GET.get("sortOrder")
    else:
        dbSearchDict["sortOrder"] = None

    # date criteria
    if request.GET.get("to"):
        dbSearchDict["to"] = request.GET.get("to")
    if request.GET.get("from"):
        dbSearchDict["from"] = request.GET.get("from")

    # get list of all tweets in db most recent to least
    tweetsList = Tweet.objects.all().order_by(
        "-createdAt"
    )

    if request.GET.get("page"):
        tweets = pagify(tweetsList, 24, request)
        return renderIndexPage(request, tweets, pulling["pulling"])

    # get entries from form as list (parse entries by space)
    if (
        request.GET.get("pull-users")
        or request.GET.get("pull-not-users")
        or request.GET.get("pull-hashtags")
        or request.GET.get("pull-keywords")
    ):
        currentTwitterSearchDict["accounts"] = list(
            part for part in request.GET["pull-users"].split(" ") if part != ""
        )
        currentTwitterSearchDict["notAccounts"] = list(
            part for part in request.GET["pull-not-users"].split(" ") if part != ""
        )
        currentTwitterSearchDict["hashtags"] = list(
            part for part in request.GET["pull-hashtags"].split(" ") if part != ""
        )
        currentTwitterSearchDict["keywords"] = list(
            part for part in request.GET["pull-keywords"].split(" ") if part != ""
        )

        currentTwitterSearchDict["fromDate"] = request.GET["pull-since"]
        # get date of x number of days ago from today as specified user in form
        if request.GET["pull-since"] != "":
            currentTwitterSearchDict["fromDate"] = datetime.strftime(
                timezone.now() - timedelta(int(request.GET["pull-since"])), "%Y-%m-%d"
            )

        currentTwitterSearchDict["toDate"] = request.GET["pull-until"]
        if request.GET["pull-until"] != "":
            # if user entered "tomorrow" get date of tomorrow
            if int(request.GET["pull-until"]) == 8:
                currentTwitterSearchDict["toDate"] = datetime.strftime(
                    timezone.now() + timedelta(1), "%Y-%m-%d"
                )
            else:
                currentTwitterSearchDict["toDate"] = datetime.strftime(
                    timezone.now() - timedelta(int(request.GET["pull-until"])),
                    "%Y-%m-%d",
                )

        # set twitter search query and string
        pullParameters = getPullParametersAsStrings(currentTwitterSearchDict)

        paginator = Paginator(tweetsList, 24)  # only display 24 tweets per page
        page = request.GET.get("page")
        tweets = paginator.get_page(page)

        if (
            not currentTwitterSearchDict["accounts"]
            and not currentTwitterSearchDict["hashtags"]
            and not currentTwitterSearchDict["keywords"]
        ):
            return renderIndexPage(
                request,
                tweets,
                pulling["pulling"],
                warning="No tweets will be pulled. Must search by at least on of the user, hashtag, or keyword fields.",
            )

        if (
            currentTwitterSearchDict["fromDate"] == currentTwitterSearchDict["toDate"]
            and currentTwitterSearchDict["fromDate"] != ""
        ):

            return renderIndexPage(
                request,
                tweets,
                pulling["pulling"],
                warning="No tweets will be pulled. From and to dates cannot be the same.",
            )

        if buildTwitterSearchQuery(currentTwitterSearchDict):
            return redirect("/scotustwitter")
        else:
            return renderIndexPage(
                request,
                tweets,
                pulling["pulling"],
                error="Too many search parameters. Must be fixed before moving on!",
            )

    # refresh fields so that old search queries won't show up
    users, hashtags, keywords = splitSearch(request.GET.get("keywords"))
    dbSearchDict["users"] = users
    dbSearchDict["hashtags"] = hashtags
    dbSearchDict["keywords"] = keywords
    dbSearchDict["to"] = request.GET.get("to")
    dbSearchDict["from"] = request.GET.get("from")
    dbSearchDict["botMax"] = request.GET.get("botMax")
    dbSearchDict["showUnscoredUsers"] = bool(request.GET.get("showUnscoredUsers", False))

    # get tweets to display
    tweetsList = Tweet.objects.all().order_by(
        "-createdAt"
    )  # get list of all tweets in db most recent to least
    tweets = pagify(tweetsList, 24, request)

    # search
    userQueries = []
    keywordQueries = []
    hashtagResults = []

    fromDate = None
    toDate = None
    botMax = None
    botFilter = None
    showUnscoredUsersFilter = None

    # get entries from search form
    if dbSearchDict["from"]:
        fromDate = datetime.strptime(request.GET.get("from"), "%b %d, %Y").replace(
            tzinfo=pytz.UTC
        )
    if dbSearchDict["to"]:
        toDate = datetime.strptime(request.GET.get("to"), "%b %d, %Y").replace(
            tzinfo=pytz.UTC
        )
    
    if not dbSearchDict["showUnscoredUsers"]:
        showUnscoredUsersFilter = Q(originalUser__botScoreEnglish__gte=0, originalUser__botScoreUniversal__gte=0)
    if dbSearchDict["botMax"]:
        botMax = int(dbSearchDict["botMax"]) / 100
        botFilter = Q(originalUser__botScoreEnglish__lte=botMax, originalUser__botScoreUniversal__lte=botMax)
    if dbSearchDict["users"]:
        userQueries = [Q(originalUser__username=user) for user in dbSearchDict["users"]]
    if dbSearchDict["hashtags"]:
        for hashtag in list(part for part in dbSearchDict["hashtags"] if part != ""):
            hashtagResults += [
                r.tweet
                for r in HashtagLog.objects.all()
                .select_related("tweet")
                .select_related("hashtag")
                .filter(hashtag__hashtagText=hashtag)
            ]
    if dbSearchDict["keywords"]:
        keywordQueries = [
            Q(originalText__icontains=keyword) for keyword in dbSearchDict["keywords"]
        ]

    # Filters
    query_filter = Q()
    if botFilter is not None:
        query_filter &= botFilter
    if showUnscoredUsersFilter is not None:
        query_filter &= showUnscoredUsersFilter

    
    # OR fields
    if request.GET.get("ANDOR") == "OR" or request.GET.get("ANDOR") == None:
        # join all queries together
        queries = userQueries + keywordQueries
        or_filter = Q()
        for q in queries:
            or_filter |= q

        # combine OR filter with our other filters
        query_filter &= or_filter
        if queries:
            # put result of filter in list, and add hashtag results
            tweetsList = list(Tweet.objects.filter(query_filter))  
            tweetsList += hashtagResults 

        # if no user or keyword entries but hashtag entries
        elif hashtagResults:
            tweetsList = hashtagResults
        else:
            tweetsList = []

    # AND fields
    else:
        user_query = Q()
        keyword_query = Q()

        # get results of user filter
        for q in userQueries:
            user_query |= q
        query_filter &= user_query 

        # get results of keyword filter
        for q in keywordQueries:
            keyword_query |= q
        query_filter &= keyword_query 

        print(query_filter)
        if hashtagResults:
            filtered_tweets = list(Tweet.objects.filter(query_filter))
            tweetsList = list(set.intersection(set(filtered_tweets), set(hashtagResults)))
        elif not hashtagResults:
            tweetsList = list(Tweet.objects.filter(query_filter))

    print(len(list(tweetsList)))
    if fromDate and toDate:
        tweetsList = [
            x for x in tweetsList if x.createdAt >= fromDate and x.createdAt <= toDate
        ]
    elif fromDate:
        tweetsList = [x for x in tweetsList if x.createdAt >= fromDate]
    elif toDate:
        tweetsList = [x for x in tweetsList if x.createdAt <= toDate]

    # find the correct sorting function and order
    if request.GET.get("sortBy"):
        sortFunc = sortingFunctions[request.GET.get("sortBy")]
    else:
        sortFunc = sortingFunctions['Date Created']
    sortOrder = False if request.GET.get("sortOrder") else True

    # get sorted tweets, paginate them, and return them
    tweetsList = sorted(tweetsList, key=sortFunc, reverse=sortOrder)
    tweets = pagify(tweetsList, 24, request)
    return renderIndexPage(request, tweets, pulling["pulling"])


# performs language processing and downloads all tweets currently being displayed in all pages into a csv file
# input:name of csv to download to
# output: None
def download(request):
    global tweetsList

    filename = "".join(
        ["tweets_", datetime.now().strftime("%Y-%m-%d_%H.%M.%S"), ".csv"]
    )
    response = HttpResponse(content_type="application/x-download")
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)
    response.write("\ufeff".encode("utf8"))

    # set headers of csv
    fieldnames = [
        "datetime",
        "last updated",
        "original username",
        "original screen name",
        "original user location",
        "original user verified",
        "original user english bot score",
        "original user universal bot score",
        "retweet",
        "retweeter username",
        "retweeter screen name",
        "retweeter location",
        "retweeter verified",
        "retweeter english bot score",
        "retweeter universal bot score",
        "text",
        "comment",
        # 'hashtags', 'urls', '#retweets','#favorites', '#retweets of retweet',
        "hashtags",
        "urls",
        "#retweets",
        "#favorites",
        "#favorites of retweet",
        "original syllable count",
        "original lexicon count",
        "original sentence count",
        "original flesch reading ease score",
        "original flesch-kincaid grade level",
        "original fog scale",
        "original smog index",
        "original automated readability index",
        "original coleman-liau index",
        "original linsear write level",
        "original dale-chall readability score",
        "original difficult words",
        "original readability consensus",
        "original neg sentiment",
        "original neu sentiment",
        "original pos sentiment",
        "original overall sentiment",
        "comment syllable count",
        "comment lexicon count",
        "comment sentence count",
        "comment flesch reading ease score",
        "comment flesch-kincaid grade level",
        "comment fog scale",
        "comment smog index",
        "comment automated readability index",
        "comment coleman-liau index",
        "comment linsear write level",
        "comment dale-chall readability score",
        "comment difficult words",
        "comment readability consensus",
        "comment neg sentiment",
        "comment neu sentiment",
        "comment pos sentiment",
        "comment overall sentiment",
        "combined syllable count",
        "combined lexicon count",
        "combined sentence count",
        "combined flesch reading ease score",
        "combined flesch-kincaid grade level",
        "combined fog scale",
        "combined smog index",
        "combined automated readability index",
        "combined coleman-liau index",
        "combined linsear write level",
        "combined dale-chall readability score",
        "combined difficult words",
        "combined readability consensus",
        "combined neg sentiment",
        "combined neu sentiment",
        "combined pos sentiment",
        "combined overall sentiment",
        "twitter users query",
        "twitter excluded users query",
        "twitter hashtags query",
        "twitter keywords query",
        "twitter from date query",
        "twitter to date query",
    ]

    # set headers of csv
    writer = csv.writer(
        response,
        dialect="excel",
        delimiter=",",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
    )
    writer.writerow(fieldnames)

    for tweet in tweetsList:
        # combine hashtags of tweet into string separated by commas
        hashtagString = ""
        tweetHashtags = HashtagLog.objects.filter(tweet__id=tweet.id)
        for i in range(len(tweetHashtags)):
            if i == 0:
                hashtagString += tweetHashtags[i].hashtag.hashtagText
            else:
                hashtagString += ", " + tweetHashtags[i].hashtag.hashtagText

        # combine urls of tweet into string separated by commas
        urlString = ""
        tweetUrls = UrlLog.objects.filter(tweet__id=tweet.id)
        for i in range(len(tweetUrls)):
            if i == 0:
                urlString += tweetUrls[i].url.urlText
            else:
                urlString += ", " + tweetUrls[i].url.urlText

        # display yes or no in verified column for original user
        if tweet.originalUser.isVerified:
            originalVerifiedString = "yes"
        else:
            originalVerifiedString = "no"

        # if not a retweet, new user fields should be empty
        newUsername = None
        newScreenName = None
        newLocation = None
        newVerifiedString = None
        newBotScoreEnglish = None
        newBotScoreUniversal = None

        # if retweet:
        # display yes or no in verified column for new user
        if tweet.newUser:
            if tweet.newUser.isVerified:
                newVerifiedString = "yes"
            else:
                newVerifiedString = "no"

            # set retweet fields
            newUsername = tweet.newUser.username
            newScreenName = tweet.newUser.screenName
            newLocation = tweet.newUser.location
            newBotScoreEnglish = tweet.newUser.botScoreEnglish
            newBotScoreUniversal = tweet.newUser.botScoreUniversal

        # display yes or no in retweet column
        if tweet.isRetweet:
            isRetweetString = "yes"
        else:
            isRetweetString = "no"

        # get sentiment scores of original text
        # combine comment text and original tezt and get sentiment scores for the combination
        commentText = ""
        if tweet.commentText:
            commentText = tweet.commentText

        # write all information about the tweet, and its language processing stats to row in csv
        writer.writerow(
            [
                tweet.createdAt,
                tweet.lastUpdated,
                tweet.originalUser.username,
                tweet.originalUser.screenName,
                tweet.originalUser.location,
                originalVerifiedString,
                tweet.originalUser.botScoreEnglish,
                tweet.originalUser.botScoreUniversal,
                isRetweetString,
                newUsername,
                newScreenName,
                newLocation,
                newVerifiedString,
                newBotScoreEnglish,
                newBotScoreUniversal,
                "".join(filter(None, ["'", tweet.originalText])),
                "".join(filter(None, ["'", tweet.commentText])),
                hashtagString,
                urlString,
                tweet.numRetweetsOriginal,
                # tweet.numFavoritesOriginal, tweet.numRetweetsNew, tweet.numFavoritesNew,
                tweet.numFavoritesOriginal,
                tweet.numFavoritesNew,
                tweet.original_syllable_count,
                tweet.original_lexicon_count,
                tweet.original_sentence_count,
                tweet.original_flesch_reading_ease,
                tweet.original_flesch_kincaid_grade,
                tweet.original_gunning_fog,
                tweet.original_smog_index,
                tweet.original_automated_readability_index,
                tweet.original_coleman_liau_index,
                tweet.original_linsear_write_formula,
                tweet.original_dale_chall_readability_score,
                tweet.original_difficult_words,
                tweet.original_text_standard,
                tweet.original_negative_sentiment,
                tweet.original_neutral_sentiment,
                tweet.original_positive_sentiment,
                tweet.original_overall_sentiment,
                tweet.comment_syllable_count,
                tweet.comment_lexicon_count,
                tweet.comment_sentence_count,
                tweet.comment_flesch_reading_ease,
                tweet.comment_flesch_kincaid_grade,
                tweet.comment_gunning_fog,
                tweet.comment_smog_index,
                tweet.comment_automated_readability_index,
                tweet.comment_coleman_liau_index,
                tweet.comment_linsear_write_formula,
                tweet.comment_dale_chall_readability_score,
                tweet.comment_difficult_words,
                tweet.comment_text_standard,
                tweet.comment_negative_sentiment,
                tweet.comment_neutral_sentiment,
                tweet.comment_positive_sentiment,
                tweet.comment_overall_sentiment,
                tweet.combined_syllable_count,
                tweet.combined_lexicon_count,
                tweet.combined_sentence_count,
                tweet.combined_flesch_reading_ease,
                tweet.combined_flesch_kincaid_grade,
                tweet.combined_gunning_fog,
                tweet.combined_smog_index,
                tweet.combined_automated_readability_index,
                tweet.combined_coleman_liau_index,
                tweet.combined_linsear_write_formula,
                tweet.combined_dale_chall_readability_score,
                tweet.combined_difficult_words,
                tweet.combined_text_standard,
                tweet.combined_negative_sentiment,
                tweet.combined_neutral_sentiment,
                tweet.combined_positive_sentiment,
                tweet.combined_overall_sentiment,
                tweet.twitterQueryUsers,
                tweet.twitterQueryNotUsers,
                tweet.twitterQueryHashtags,
                tweet.twitterQueryKeywords,
                tweet.twitterQueryFromDate,
                tweet.twitterQueryToDate
            ]
        )

    return response


def signup(request):
    if request.method == "POST":
        userForm = SignUpForm(request.POST)
        profileForm = ProfileForm(request.POST)
        if userForm.is_valid() and profileForm.is_valid():
            user = userForm.save(commit=False)
            user.is_active = False
            user.save()
            profile = profileForm.save(commit=False)
            profile.user = account.objects.get(id=user.id)
            profile.save()
            current_site = get_current_site(request)
            subject = "Activate SCOTUS Twitter Website Account"
            message = render_to_string(
                "account_activation_email.html",
                {
                    "user": user,
                    "domain": current_site.domain,
                    "reason": profile.reason,
                    "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                    "token": account_activation_token.make_token(user),
                },
            )

            email = EmailMessage(
                subject, message, to=os.environ["ADMIN_EMAILS"].split(",")
            )
            email.send()
            return HttpResponse(
                "Your access request has been sent to an administrator.\nYou will be emailed once you accound has been approved.\nAfter that you will be able to sign into the website."
            )
    else:
        userForm = SignUpForm()
        profileForm = ProfileForm(request.POST)
    return render(
        request, "signup.html", {"userForm": userForm, "profileForm": profileForm}
    )


def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = account.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, account.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        current_site = get_current_site(request)
        subject = "Your SCOTUS Twitter website account has been activated"
        message = (
            user.first_name
            + " "
            + user.last_name
            + ",\n\nYour SCOTUS Twitter accout has been activated. You can now login to the website.\n\nhttp://"
            + current_site.domain
            + "/login"
        )

        email = EmailMessage(subject, message, to=[user.email])
        email.send()
        return HttpResponse(
            "Thank you for your email confirmation. The new user can now login to their account."
        )
    else:
        return HttpResponse("Activation link is invalid!")


def error(request):
    return render(request, "error.html")


pullParameters = getPullParametersAsStrings(initialSearchDict)
