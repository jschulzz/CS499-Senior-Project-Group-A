from .models import User
from .models import Tweet
from .models import Hashtag
from .models import Url
from .models import HashtagLog
from .models import UrlLog
from .RelevancyModel import RelevancyModel

from django.shortcuts import redirect


from datetime import datetime, timedelta
from django.utils import timezone
import pytz
from threading import Thread

import tweepy
import os
import time
import random
import botometer
import textstat
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

consumer_key = os.environ["CONSUMER_KEY"]
consumer_secret = os.environ["CONSUMER_SECRET"]
access_token = os.environ["ACCESS_TOKEN"]
access_token_secret = os.environ["ACCESS_TOKEN_SECRET"]
rapidapi_key = os.environ["RAPIDAPI_KEY"]

twitter_app_auth = {
    "consumer_key": consumer_key,
    "consumer_secret": consumer_secret,
    "access_token": access_token,
    "access_token_secret": access_token_secret,
}

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

bom = botometer.Botometer(
    wait_on_ratelimit=True, rapidapi_key=rapidapi_key, botometer_api_url="https://botometer-pro.p.rapidapi.com", **twitter_app_auth 
)

sid_obj = SentimentIntensityAnalyzer()


# initial twitter search criteria
initialSearchDict = {}
initialSearchDict["hashtags"] = [
    "scotus",
    "supremecourt",
    "ussc",
    "court",
    "billofrights",
    "constitution",
    "firstamendment",
    "1a",
    "secondamendment",
    "2a",
    "rbg",
    "justice",
    "ussupremecourt",
    "kavanaugh",
    "chiefjustice",
    "scalia",
    "abortion",
    "justicekennedy",
    "decision",
    "highcourt",
]
initialSearchDict["accounts"] = [
    "stevenmazie",
    "JeffreyToobin",
    "DCCIR",
    "GregStohr",
    "AlisonFrankel",
    "ReutersLegal",
    "VerdictJustia",
    "scotusreporter",
    "AppellateDaily",
    "Profepps",
    "Dahlialitchwick",
    "Arianedevogue",
    "HarlanInstitute",
    "JanCBS",
    "richardjwolf",
    "JoanBiskupic",
    "SCOTUSblogposts",
    "JonathanTurley",
    "VolokhC",
    "LllCornell",
    "JessBravin",
    "NinaTotenberg",
    "FedcourtJunkie",
    "lylden",
    "SupremeHaiku",
    "joshgerstein",
    "sfw70",
    "AP_Courtside",
    "ZoeTillman",
    "sethstern",
    "rickhasen",
    "DCDicta",
    "SCOTUSOpinions",
    "eckholm",
    "shermancourt",
    "JustADCohen",
    "lawrencehurley",
    "adamliptak",
    "WSJlaw",
    "fordm",
    "kashhill",
    "stevenportnoy",
    "chrisgeidner",
    "atlblog",
    "DavidLBrownJr",
    "danabrams",
    "oyez",
    "Tonymauro",
    "ShannonBream",
    "Legal_Times",
    "joe_palazzolo",
    "USSupremeCourt",
    "SCOTUSblog",
    "LegalWeek",
    "ABAJournal",
    "DavidLat",
    "ryanjreilly",
    "AHow_eBlogger",
    "andrew_chung",
    "AndrewOReilly84",
    "DavidGSavage",
    "jackshafer",
    "KevinDaleyDC",
    "mjs_DC",
    "imillhiser",
    "jacq_thomsen",
    "jessicagresko",
    "PeteWilliamsNBC",
    "tuckerhiggins",
    "GreenhouseLinda",
    "WheelerLydia",
    "SchoolLawBlog",
    "RonnBlitzer",
    "Tierney_Megan",
]
initialSearchDict["notAccounts"] = ["John_Scotus", "ScotusCC"]
initialSearchDict["fromDate"] = datetime.strftime(
    timezone.now() - timedelta(1), "%Y-%m-%d"
)
initialSearchDict["toDate"] = datetime.strftime(timezone.now(), "%Y-%m-%d")
initialSearchDict["keywords"] = []

twitterSearchQueries = []

# dictionary with parameters to search twitter by in string form (to display in website)
pullParameters = {}

# true if gone through all results from search request, else false
done = False

# if user has started pulling tweets, dict (mutable) so it can be accessed from view.py
pulling = {"pulling": True}

# max before Twitter API errors bc of too complex query
MAX_PARAMETERS = 50

# calculate relevancy based on text statistics
# loads a pre-trained model
relevancyModel = RelevancyModel()
relevantStatistics = ['syllableCount', 'lexiconCount', 'sentenceCount', 'fleschReadingEase', 'fleschKincaidGrade',
                'gunningFog', 'smogIndex', 'automatedReadabilityIndex', 'colemanLiauIndex', 'linsearWriteFormula',
                'daleChallReadabilityScore']

def getRelevancyScore(text, textStats):
    lowerText = str(text).lower()
    if 'supreme court' in lowerText or 'scotus' in lowerText:
        return 1
    else:
        relevantStatValues = []
        for key in relevantStatistics:
            relevantStatValues.append(textStats[key])
        return relevancyModel.getRelevancy(relevantStatValues)

# calculate text statistics about given text for insertion to DB
# input: text to be analyzed
# output: object of text statistics
def getTextStats(text):
    if text is None:
        return {
            "syllableCount": None,
            "lexiconCount": None,
            "sentenceCount": None,
            "fleschReadingEase": None,
            "fleschKincaidGrade": None,
            "gunningFog": None,
            "smogIndex": None,
            "automatedReadabilityIndex": None,
            "colemanLiauIndex": None,
            "linsearWriteFormula": None,
            "daleChallReadabilityScore": None,
            "difficultWords": None,
            "textStandard": None,
            "negative_sentiment": None,
            "neutral_sentiment": None,
            "positive_sentiment": None,
            "overall_sentiment": None,
        }
    syllableCount = textstat.syllable_count(text, lang="en_US")
    lexiconCount = textstat.lexicon_count(text, removepunct=True)
    sentenceCount = textstat.sentence_count(text)
    fleschReadingEase = textstat.flesch_reading_ease(text)
    fleschKincaidGrade = textstat.flesch_kincaid_grade(text)
    gunningFog = textstat.gunning_fog(text)
    smogIndex = textstat.smog_index(text)
    automatedReadabilityIndex = textstat.automated_readability_index(text)
    colemanLiauIndex = textstat.coleman_liau_index(text)
    linsearWriteFormula = textstat.linsear_write_formula(text)
    daleChallReadabilityScore = textstat.dale_chall_readability_score(text)
    difficultWords = textstat.difficult_words(text)
    textStandard = textstat.text_standard(text, float_output=False)
    sentiment_dict = sid_obj.polarity_scores(text)

    return {
        "syllableCount": syllableCount,
        "lexiconCount": lexiconCount,
        "sentenceCount": sentenceCount,
        "fleschReadingEase": fleschReadingEase,
        "fleschKincaidGrade": fleschKincaidGrade,
        "gunningFog": gunningFog,
        "smogIndex": smogIndex,
        "automatedReadabilityIndex": automatedReadabilityIndex,
        "colemanLiauIndex": colemanLiauIndex,
        "linsearWriteFormula": linsearWriteFormula,
        "daleChallReadabilityScore": daleChallReadabilityScore,
        "difficultWords": difficultWords,
        "textStandard": textStandard,
        "negative_sentiment": sentiment_dict["neg"],
        "neutral_sentiment": sentiment_dict["neu"],
        "positive_sentiment": sentiment_dict["pos"],
        "overall_sentiment": sentiment_dict["compound"],
    }


# find twitter Botometer bot scores of a given user
# input: username of account in question
# output: tuple of english and universal scores
def getBotScores(username):
    english_score = -1
    universal_score = -1
    try:
        bot_scores = bom.check_account("@" + username)
        english_score = bot_scores["scores"]["english"]
        universal_score = bot_scores["scores"]["universal"]
        print(username, english_score, universal_score)
    except Exception as e:
        # sometimes recieve a 500 Error, an issue on botometer's end.
        # Might want to do something with it in the future
        pass
    return english_score, universal_score


# convert the array value of a given dictionary key to a string with elements separated by spaces
# input:dictionary and key in dictionary that should be converted
# output: the string
def searchListToString(d, key):
    string = ""
    for i in range(len(d[key])):
        if i == len(d[key]) - 1:
            string += d[key][i]
        else:
            string += d[key][i] + " "
    return string


# set the pull parameters dictionary (to display on website)
# input: a search dictionary of paramters to search twitter by
# output: none
def getPullParametersAsStrings(searchDict):
    fromDateVal = 0
    fromDateString = ""
    toDateVal = 0
    toDateString = ""
    # get number of days between today and given from date
    if searchDict["fromDate"] != "":
        delta = timezone.now() - datetime.strptime(
            searchDict["fromDate"], "%Y-%m-%d"
        ).replace(tzinfo=pytz.UTC)
        fromDateVal = delta.days
        if fromDateVal > 0:
            fromDateString = str(fromDateVal) + " days ago"
        elif fromDateVal == 0:
            fromDateString = "Today"

    # get number of days between today and given to date
    if searchDict["toDate"] != "":
        delta = timezone.now() - datetime.strptime(
            searchDict["toDate"], "%Y-%m-%d"
        ).replace(tzinfo=pytz.UTC)
        toDateVal = delta.days
        if toDateVal > 0:
            toDateString = str(toDateVal) + " days ago"
        elif toDateVal == 0:
            toDateString = "Today"
        else:
            toDateString = "Tomorrow"

    # set dictionary to string conversions of dict array values (and # days between today and from/to dates)
    return {
        "usersString": searchListToString(searchDict, "accounts"),
        "notUsersString": searchListToString(searchDict, "notAccounts"),
        "hashtagsString": searchListToString(searchDict, "hashtags"),
        "keywordsString": searchListToString(searchDict, "keywords"),
        "fromDateVal": fromDateVal,
        "toDateVal": toDateVal,
        "fromDateString": fromDateString,
        "toDateString": toDateString,
    }


# builds queries for twitter search api based on input dictionary
# input:search dict
# output: None
def buildTwitterSearchQuery(searchDict):
    # global so that the pull function always uses the most up to date queries
    global twitterSearchQueries
    global done
    global pullParameters

    # clear previous queries
    twitterSearchQueries = []
    keywordParameters = []
    hashtagParameters = []
    accountParameters = []

    for keyword in searchDict["keywords"]:
        keywordParameters.append(keyword)
    for hashtag in searchDict["hashtags"]:
        hashtagParameters.append("#" + hashtag)
    for account in searchDict["accounts"]:
        accountParameters.append("to:" + account)
        accountParameters.append("from:" + account)
        accountParameters.append("@" + account)

    numDates = 0  # number of dates to append to end of each query

    if searchDict["fromDate"] != "":
        numDates += 1
    if searchDict["toDate"] != "":
        numDates += 1

    # build queries with randomly selected keywords, hashtags, and accounts until there are no more parameters or the query has gotten too complex (then start new one)
    while len(keywordParameters) + len(hashtagParameters) + len(accountParameters) != 0:
        query = ""
        while (
            len(query.split(" "))
            < MAX_PARAMETERS - len(searchDict["notAccounts"]) - numDates - 1
            and len(keywordParameters) + len(hashtagParameters) + len(accountParameters)
            != 0
        ):
            if keywordParameters:
                parameter = random.choice(keywordParameters)
                query += parameter + " OR "
                keywordParameters.remove(parameter)
            if hashtagParameters:
                parameter = random.choice(hashtagParameters)
                query += parameter + " OR "
                hashtagParameters.remove(parameter)
            if accountParameters:
                parameter = random.choice(accountParameters)
                query += parameter + " OR "
                accountParameters.remove(parameter)

        # eliminate last OR
        if numDates + len(searchDict["notAccounts"]) != 0:
            query = query[: len(query) - 3]
        else:
            query = query[: len(query) - 4]

        # add accounts to be excluded from search parameter to query
        for i in range(len(searchDict["notAccounts"])):
            query += "-from:" + searchDict["notAccounts"][i]
            if i != len(searchDict["notAccounts"]) - 1:
                query += " "

        # add to and from dates parameters to query
        if searchDict["fromDate"] != "":
            query += " since:" + searchDict["fromDate"]
        if searchDict["toDate"] != "":
            query += " until:" + searchDict["toDate"]
        twitterSearchQueries.append(query)

    pullParameters = getPullParametersAsStrings(searchDict)
    done = False  # so new queries will immediately be searched for

    # if any queries are too long, return False
    for query in twitterSearchQueries:
        if len(query.split(" ")) >= MAX_PARAMETERS:
            return False
    return True


# retrieves and stores only relevant information from tweepy tweet responses
# input: tweepy response from search api call
# output: list of all tweets from response stored as dictionaries with only relevant information about the tweet
def parseTwitterResponse(response):
    tweets = []
    for t in response:
        # set tweet information that will depend on whether the tweet is a retweet
        isRetweet = False
        commentText = None
        originalText = t.full_text
        h = t.entities.get("hashtags")
        u = t.entities.get("urls")
        numRetweetsNew = None
        numFavoritesNew = None
        numRetweetsOriginal = t.retweet_count
        numFavoritesOriginal = t.favorite_count
        originalUsername = t.user.screen_name
        originalScreenName = t.user.name
        originalLocation = t.user.location
        originalVerified = t.user.verified
        newUsername = None
        newScreenName = None
        newLocation = None
        newVerified = None

        # if tweet is a retweet
        if hasattr(t, "retweeted_status"):
            isRetweet = True
            originalText = t.retweeted_status.full_text
            h = t.retweeted_status.entities.get("hashtags")
            u = t.retweeted_status.entities.get("urls")
            numRetweetsOriginal = t.retweeted_status.retweet_count
            numFavoritesOriginal = t.retweeted_status.favorite_count
            # numRetweetsNew = t.retweet_count
            # numFavoritesNew = t.favorite_count

            originalUsername = t.retweeted_status.user.screen_name
            originalScreenName = t.retweeted_status.user.name
            originalLocation = t.retweeted_status.user.location
            originalVerified = t.retweeted_status.user.verified
            newUsername = t.user.screen_name
            newScreenName = t.user.name
            newLocation = t.user.location
            newVerified = t.user.verified

        # if tweet is quote tweet
        elif hasattr(t, "quoted_status"):
            isRetweet = True
            originalText = t.quoted_status.full_text
            commentText = t.full_text
            h = t.quoted_status.entities.get("hashtags")
            u = t.quoted_status.entities.get("urls")
            numRetweetsOriginal = t.quoted_status.retweet_count
            numFavoritesOriginal = t.quoted_status.favorite_count
            # numRetweetsNew = t.retweet_count
            numFavoritesNew = t.favorite_count

            originalUsername = t.quoted_status.user.screen_name
            originalScreenName = t.quoted_status.user.name
            originalLocation = t.quoted_status.user.location
            originalVerified = t.quoted_status.user.verified
            newUsername = t.user.screen_name
            newScreenName = t.user.name
            newLocation = t.user.location
            newVerified = t.user.verified

        # get hashtags in tweet
        hashtags = []
        for hDict in h:
            hashtags.append(hDict["text"])

        # get urls in tweet
        urls = []
        for uDict in u:
            urls.append(uDict["url"])

        # create tweet dictionary storing only relevant information
        tweet = {}
        tweet["originalUsername"] = originalUsername
        tweet["originalScreenName"] = originalScreenName
        tweet["originalLocation"] = originalLocation
        tweet["originalIsVerified"] = originalVerified

        tweet["newUsername"] = newUsername
        tweet["newScreenName"] = newScreenName
        tweet["newLocation"] = newLocation
        tweet["newIsVerified"] = newVerified

        # tweet['createdAt'] = datetime.strptime(t.created_at, '%a %b %d %H:%M:%S +0000 %Y').replace(tzinfo=pytz.UTC)
        tweet["createdAt"] = t.created_at.replace(tzinfo=pytz.UTC)
        tweet["isRetweet"] = isRetweet

        tweet["originalText"] = originalText
        tweet["commentText"] = commentText
        if commentText != None:
            tweet["commentText"] = tweet["commentText"]
        tweet["hashtags"] = hashtags
        tweet["urls"] = urls
        tweet["numRetweetsOriginal"] = numRetweetsOriginal

        tweet["numRetweetsNew"] = numRetweetsNew
        tweet["numFavoritesOriginal"] = numFavoritesOriginal
        tweet["numFavoritesNew"] = numFavoritesNew

        tweets.append(tweet)

    return tweets


# inserts tweet into db
# input: tweet dictionary
# output: None
def insert(tweet):
    global pullParameters

    textStatsOriginal = getTextStats(tweet["originalText"])
    textStatsComment = getTextStats(tweet["commentText"])

    # combine possibly None strings
    combined_text = "".join(filter(None, [tweet["originalText"], tweet["commentText"]]))
    textStatsCombined = getTextStats(combined_text)

    # calculate the relevancy score
    relevancyScore = getRelevancyScore(combined_text, textStatsCombined)
    newUser = None
    # if user is not already in db, add them to db
    if not User.objects.filter(username=tweet["originalUsername"]).exists():
        english_score, universal_score = -1, -1
        if relevancyScore > 0.6:
            english_score, universal_score = getBotScores(tweet["originalUsername"])
        originalUser = User(
            username=tweet["originalUsername"],
            screenName=tweet["originalScreenName"],
            location=tweet["originalLocation"],
            isVerified=tweet["originalIsVerified"],
            botScoreEnglish=english_score,
            botScoreUniversal=universal_score,
        )
        originalUser.save()
    else:
        originalUser = User.objects.filter(username=tweet["originalUsername"])[0]

    if tweet["newUsername"] != None:
        if not User.objects.filter(username=tweet["newUsername"]).exists():
            english_score, universal_score = -1, -1
            if relevancyScore > 0.6:
                english_score, universal_score = getBotScores(tweet["originalUsername"])
            newUser = User(
                username=tweet["newUsername"],
                screenName=tweet["newScreenName"],
                location=tweet["newLocation"],
                isVerified=tweet["newIsVerified"],
                botScoreEnglish=english_score,
                botScoreUniversal=universal_score,
            )
            newUser.save()

        else:
            if User.objects.filter(username=tweet["newUsername"]).exists():
                newUser = User.objects.filter(username=tweet["newUsername"])[0]

    # if hashtag not already in db, add it to db
    # TODO: make case insensitive??
    hashtags = []
    for h in tweet["hashtags"]:
        if not Hashtag.objects.filter(hashtagText=h).exists():
            hashtag = Hashtag(hashtagText=h)
            hashtag.save()
        else:
            hashtag = Hashtag.objects.filter(hashtagText=h)[0]
        hashtags.append(hashtag)

    # if url not already in db, add it to db
    urls = []
    for u in tweet["urls"]:
        if not Url.objects.filter(urlText=u).exists():
            url = Url(urlText=u)
            url.save()
        else:
            url = Url.objects.filter(urlText=u)[0]
        urls.append(url)



    # create tweet object and add to db
    t = Tweet(
        originalUser=originalUser,
        newUser=newUser,
        createdAt=tweet["createdAt"],
        isRetweet=tweet["isRetweet"],
        relevancy=relevancyScore,
        originalText=tweet["originalText"],
        commentText=tweet["commentText"],
        numRetweetsOriginal=tweet["numRetweetsOriginal"],
        numRetweetsNew=tweet["numRetweetsNew"],
        numFavoritesOriginal=tweet["numFavoritesOriginal"],
        numFavoritesNew=tweet["numFavoritesNew"],
        lastUpdated=timezone.now().strftime("%Y-%m-%d %H:%M"),
        twitterQueryUsers=pullParameters["usersString"],
        twitterQueryNotUsers=pullParameters["notUsersString"],
        twitterQueryHashtags=pullParameters["hashtagsString"],
        twitterQueryKeywords=pullParameters["keywordsString"],
        twitterQueryFromDate=pullParameters["fromDateString"],
        twitterQueryToDate=pullParameters["toDateString"],
        original_syllable_count=textStatsOriginal["syllableCount"],
        original_lexicon_count=textStatsOriginal["lexiconCount"],
        original_sentence_count=textStatsOriginal["sentenceCount"],
        original_flesch_reading_ease=textStatsOriginal["fleschReadingEase"],
        original_flesch_kincaid_grade=textStatsOriginal["fleschKincaidGrade"],
        original_gunning_fog=textStatsOriginal["gunningFog"],
        original_smog_index=textStatsOriginal["smogIndex"],
        original_automated_readability_index=textStatsOriginal[
            "automatedReadabilityIndex"
        ],
        original_coleman_liau_index=textStatsOriginal["colemanLiauIndex"],
        original_linsear_write_formula=textStatsOriginal["linsearWriteFormula"],
        original_dale_chall_readability_score=textStatsOriginal[
            "daleChallReadabilityScore"
        ],
        original_difficult_words=textStatsOriginal["difficultWords"],
        original_text_standard=textStatsOriginal["textStandard"],
        original_negative_sentiment=textStatsOriginal["negative_sentiment"],
        original_neutral_sentiment=textStatsOriginal["neutral_sentiment"],
        original_positive_sentiment=textStatsOriginal["positive_sentiment"],
        original_overall_sentiment=textStatsOriginal["overall_sentiment"],
        comment_syllable_count=textStatsComment["syllableCount"],
        comment_lexicon_count=textStatsComment["lexiconCount"],
        comment_sentence_count=textStatsComment["sentenceCount"],
        comment_flesch_reading_ease=textStatsComment["fleschReadingEase"],
        comment_flesch_kincaid_grade=textStatsComment["fleschKincaidGrade"],
        comment_gunning_fog=textStatsComment["gunningFog"],
        comment_smog_index=textStatsComment["smogIndex"],
        comment_automated_readability_index=textStatsComment[
            "automatedReadabilityIndex"
        ],
        comment_coleman_liau_index=textStatsComment["colemanLiauIndex"],
        comment_linsear_write_formula=textStatsComment["linsearWriteFormula"],
        comment_dale_chall_readability_score=textStatsComment[
            "daleChallReadabilityScore"
        ],
        comment_difficult_words=textStatsComment["difficultWords"],
        comment_text_standard=textStatsComment["textStandard"],
        comment_negative_sentiment=textStatsComment["negative_sentiment"],
        comment_neutral_sentiment=textStatsComment["neutral_sentiment"],
        comment_positive_sentiment=textStatsComment["positive_sentiment"],
        comment_overall_sentiment=textStatsComment["overall_sentiment"],
        combined_syllable_count=textStatsCombined["syllableCount"],
        combined_lexicon_count=textStatsCombined["lexiconCount"],
        combined_sentence_count=textStatsCombined["sentenceCount"],
        combined_flesch_reading_ease=textStatsCombined["fleschReadingEase"],
        combined_flesch_kincaid_grade=textStatsCombined["fleschKincaidGrade"],
        combined_gunning_fog=textStatsCombined["gunningFog"],
        combined_smog_index=textStatsCombined["smogIndex"],
        combined_automated_readability_index=textStatsCombined[
            "automatedReadabilityIndex"
        ],
        combined_coleman_liau_index=textStatsCombined["colemanLiauIndex"],
        combined_linsear_write_formula=textStatsCombined["linsearWriteFormula"],
        combined_dale_chall_readability_score=textStatsCombined[
            "daleChallReadabilityScore"
        ],
        combined_difficult_words=textStatsCombined["difficultWords"],
        combined_text_standard=textStatsCombined["textStandard"],
        combined_negative_sentiment=textStatsCombined["negative_sentiment"],
        combined_neutral_sentiment=textStatsCombined["neutral_sentiment"],
        combined_positive_sentiment=textStatsCombined["positive_sentiment"],
        combined_overall_sentiment=textStatsCombined["overall_sentiment"],
    )

    t.save()

    # add tweet and all of its hashtags to log in db
    for hashtag in hashtags:
        hlog = HashtagLog(tweet=t, hashtag=hashtag)
        hlog.save()

    # add tweet and all of its urls to log in db
    for url in urls:
        ulog = UrlLog(tweet=t, url=url)
        ulog.save()


# updates tweet in db with new information (only updates retweet and favorites metrics
# input: existing tweet, tweet object with potentially new information
# output: None
def update(oldTweet, newTweet):
    #if number of retweets or favorites is different between existing and new, update

    if oldTweet.numRetweetsOriginal != newTweet["numRetweetsOriginal"]:
        oldTweet.numRetweetsOriginal = newTweet["numRetweetsOriginal"]

    if oldTweet.numRetweetsNew != newTweet["numRetweetsNew"]:
        oldTweet.numRetweetsNew = newTweet["numRetweetsNew"]

    if oldTweet.numFavoritesOriginal != newTweet["numFavoritesOriginal"]:
        oldTweet.numFavoritesOriginal = newTweet["numFavoritesOriginal"]

    if oldTweet.numFavoritesNew != newTweet["numFavoritesNew"]:
        oldTweet.numFavoritesNew = newTweet["numFavoritesNew"]

    oldTweet.lastUpdated = timezone.now().strftime("%Y-%m-%d %H:%M")
    oldTweet.save()


# inserts new tweets and updates existing tweets in db
# input: list of distinct tweet dictionaries
# output: None
def addToDatabase(tweets):
    inserted, updated = 0, 0
    for tweet in tweets:

        #if tweet is retweet exists in db or original tweet exists in db, update it in the db
        if tweet['newUsername']:
            if Tweet.objects.filter(newUser__username=tweet['newUsername'], createdAt=tweet['createdAt']).exists():
                t = Tweet.objects.get(newUser__username=tweet['newUsername'], createdAt=tweet['createdAt'])
                update(t, tweet)
                updated += 1
        elif Tweet.objects.filter(originalUser__username=tweet['originalUsername'], createdAt=tweet['createdAt']).exists():
            t = Tweet.objects.get(originalUser__username=tweet['originalUsername'], createdAt=tweet['createdAt'])
            update(t, tweet)
            updated += 1
        # otherwise (neither exist in db) add to db
        else:
            insert(tweet)
            inserted += 1

    return inserted, updated


# for each search query, uses tweepy to make twitter api search request,
# goes through all pages of result, and adds results to db appropriately
# input: None
# output: None
def searchTwitter():
    global twitterSearchQueries, api, done, pulling
    done = False
    for idx, query in enumerate(twitterSearchQueries):
        # handle escaping
        if done or not pulling["pulling"]:
            break

        retries = 0
        inserted, updated = 0, 0

        # If results only below a specific ID are, set max_id to that ID.
        # else default to no upper limit, start from the most recent tweet matching the search query.
        max_id = -1

        resultsSize = 1
        while resultsSize:
            try:
                if max_id >= 0:
                    results = api.search(q=query, count=100,tweet_mode='extended', max_id=str(max_id - 1))
                else:
                    results = api.search(q=query, count=100, tweet_mode='extended')

                # update number of results, break if needed
                resultsSize = len(results)
                if not resultsSize or done or not pulling["pulling"]:
                    break

                # parse relevant information from response
                searchResults = []
                tweets = parseTwitterResponse(results)
                for tweetDict in [
                    i for n, i in enumerate(tweets) if i not in tweets[n + 1 :]
                ]:  # only add unique tweet to results
                    searchResults.append(tweetDict)

                # add results to db for every page so that db gets updated with new tweets to display often
                newIns, newUpd = addToDatabase(searchResults)
                inserted += newIns
                updated += newUpd

                # sleeper to avoid 180 requests per 15 minute rate limit
                time.sleep(24)

                # update loop variable max_id
                max_id = results[-1].id

            except tweepy.TweepError as e:
                print(e)
                if retries > 2:
                    pulling["pulling"] = False
                    redirect("error")
                retries += 1

        print("Inserted %d tweets for Query %d" % (inserted, idx))
        print("Updated %d tweets for Query %d" % (updated, idx))

    # if this was stopped via startStopPull(), set done to False. Otherwise, we're done and we'll sleep in pull()
    if not pulling["pulling"]:
        done = False
    else:
        done = True

# pulls relevant tweets from twitter by searching twitter and adding results to db (runs as bg task)
# input: None
# output: None
def pull():
    global done, pulling
    while True:
        while pulling["pulling"]:
            if not done:
                print("Pulling new tweets")
                searchTwitter()
                print("Finished pulling new tweets")

            #if done with searching, wait 12 hours and try again
            else:
                time.sleep(60 * 60 * 12)
                done = False


def startStopPull(request):
    global pulling
    pulling["pulling"] = not pulling["pulling"]
    return redirect("/")

# start pulling tweets initially with initial search dictionary parameters
pullParameters = getPullParametersAsStrings(initialSearchDict)
buildTwitterSearchQuery(initialSearchDict)
pullThread = Thread(target=pull) #pull tweets asynchronously so that main thread isn't blocked
pullThread.start()
