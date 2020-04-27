# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User as account
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(account, on_delete=models.CASCADE, primary_key=True)
    reason = models.TextField(max_length=500)
    # other fields...


@receiver(post_save, sender=account)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()


# Create your models here.


class User(models.Model):
    # Twitter usernames can be no longer than 15 characters
    username = models.CharField(max_length=20)
    # Twitter screen names can be no longer than 50 characters
    screenName = models.CharField(max_length=100)
    # Twitter bios can be no longer than 160 characters
    location = models.CharField(max_length=200)
    isVerified = models.BooleanField()
    botScoreEnglish = models.FloatField(default=-1)
    botScoreUniversal = models.FloatField(default=-1)


class Hashtag(models.Model):
    hashtagText = models.TextField(max_length=500)  # Tweet that is just a hashtag


class Url(models.Model):
    urlText = models.TextField()  # Tweet that is just a hashtag


class Tweet(models.Model):
    originalUser = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="originalUser"
    )
    newUser = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="newUser", null=True
    )
    createdAt = models.DateTimeField()
    isRetweet = models.BooleanField()

    # if retweet - text of original tweet, else - text of the tweet
    # Tweets can be no longer than 246 characters
    originalText = models.TextField(
        max_length=500
    )  # Tweets can be no longer than 246 characters

    # if comment retweet - text of comment, else - null
    commentText = models.TextField(max_length=500, null=True)

    # if retweet - metric of original tweet, else - metric of the tweet
    numRetweetsOriginal = models.IntegerField()
    numRetweetsNew = models.IntegerField(null=True)
    numFavoritesOriginal = models.IntegerField()
    numFavoritesNew = models.IntegerField(null=True)
    lastUpdated = models.DateTimeField()

    # text stats
    original_syllable_count = models.FloatField(null=True)
    original_lexicon_count = models.FloatField(null=True)
    original_sentence_count = models.FloatField(null=True)
    original_flesch_reading_ease = models.FloatField(null=True)
    original_flesch_kincaid_grade = models.FloatField(null=True)
    original_gunning_fog = models.FloatField(null=True)
    original_smog_index = models.FloatField(null=True)
    original_automated_readability_index = models.FloatField(null=True)
    original_coleman_liau_index = models.FloatField(null=True)
    original_linsear_write_formula = models.FloatField(null=True)
    original_dale_chall_readability_score = models.FloatField(null=True)
    original_difficult_words = models.FloatField(null=True)
    original_text_standard = models.TextField(max_length=30, null=True)
    comment_syllable_count = models.FloatField(null=True)
    comment_lexicon_count = models.FloatField(null=True)
    comment_sentence_count = models.FloatField(null=True)
    comment_flesch_reading_ease = models.FloatField(null=True)
    comment_flesch_kincaid_grade = models.FloatField(null=True)
    comment_gunning_fog = models.FloatField(null=True)
    comment_smog_index = models.FloatField(null=True)
    comment_automated_readability_index = models.FloatField(null=True)
    comment_coleman_liau_index = models.FloatField(null=True)
    comment_linsear_write_formula = models.FloatField(null=True)
    comment_dale_chall_readability_score = models.FloatField(null=True)
    comment_difficult_words = models.FloatField(null=True)
    comment_text_standard = models.TextField(max_length=30, null=True)
    combined_syllable_count = models.FloatField(null=True)
    combined_lexicon_count = models.FloatField(null=True)
    combined_sentence_count = models.FloatField(null=True)
    combined_flesch_reading_ease = models.FloatField(null=True)
    combined_flesch_kincaid_grade = models.FloatField(null=True)
    combined_gunning_fog = models.FloatField(null=True)
    combined_smog_index = models.FloatField(null=True)
    combined_automated_readability_index = models.FloatField(null=True)
    combined_coleman_liau_index = models.FloatField(null=True)
    combined_linsear_write_formula = models.FloatField(null=True)
    combined_dale_chall_readability_score = models.FloatField(null=True)
    combined_difficult_words = models.FloatField(null=True)
    combined_text_standard = models.TextField(max_length=30, null=True)

    original_negative_sentiment = models.FloatField(null=True)
    original_neutral_sentiment = models.FloatField(null=True)
    original_positive_sentiment = models.FloatField(null=True)
    original_overall_sentiment = models.FloatField(null=True)
    comment_negative_sentiment = models.FloatField(null=True)
    comment_neutral_sentiment = models.FloatField(null=True)
    comment_positive_sentiment = models.FloatField(null=True)
    comment_overall_sentiment = models.FloatField(null=True)
    combined_negative_sentiment = models.FloatField(null=True)
    combined_neutral_sentiment = models.FloatField(null=True)
    combined_positive_sentiment = models.FloatField(null=True)
    combined_overall_sentiment = models.FloatField(null=True)

    # what twitter search query resulted in this tweet
    twitterQueryUsers = models.TextField(max_length=5000)
    twitterQueryNotUsers = models.TextField(max_length=5000)
    twitterQueryHashtags = models.TextField(max_length=5000)
    twitterQueryKeywords = models.TextField(max_length=5000)
    twitterQueryFromDate = models.TextField(max_length=5000)
    twitterQueryToDate = models.TextField(max_length=5000)


class HashtagLog(models.Model):
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE)
    hashtag = models.ForeignKey(Hashtag, on_delete=models.CASCADE)


class UrlLog(models.Model):
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE)
    url = models.ForeignKey(Url, on_delete=models.CASCADE)
