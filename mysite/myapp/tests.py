# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from django.contrib.auth.models import User
from django.test import tag

# useful testing functions
def setupHeadlessWebdriver():
    options = Options()
    options.add_argument("--headless")
    executable_path = r'C:\Users\ofsk222\PycharmProjects\CS499-Senior-Project-Group-A\artifacts\geckodriver.exe'
    return webdriver.Firefox(executable_path=executable_path)

def setupUser(username, password):
    test_user = User.objects.create_user(username=username, password=password)
    return test_user


# Screen Tests
class ScreenTests(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super(ScreenTests, cls).setUpClass()
        cls.selenium = setupHeadlessWebdriver()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(ScreenTests, cls).tearDownClass()

    def setUp(self):
        self.selenium.get(self.live_server_url + '/login')

    @tag('run')
    def test_signup(self):
        signup = self.selenium.find_element_by_xpath("//a[@href='/signup/']")
        signup.click()
        assert (self.selenium.current_url == self.live_server_url + '/signup/')

    @tag('run')
    def test_adminlogin(self):
        setupUser('admin', 'password')
        username = self.selenium.find_element_by_xpath("//input[@name='username']")
        username.send_keys('admin')

        password = self.selenium.find_element_by_xpath("//input[@name='password']")
        password.send_keys('password')

        login = self.selenium.find_element_by_xpath("//button[@type='submit']")
        login.click()

        assert (self.selenium.current_url == self.live_server_url + '/scotustwitter/')

    # Tests expanding tweet details
    # Should confirm tweet details are shown
    def test_details(self):
        expand_button = self.selenium.find_element_by_xpath("//i[text()='more_vert']")
        expand_button.click()

        assert self.selenium.find_element_by_xpath("//div[@class='card-reveal'][@style='display: block; transform: translateY(-100%);']")

    # Tests link to user profile
    # Should open user's profile on Twitter
    def test_link(self):
        user_link = self.selenium.find_element_by_xpath("//a[@target='_blank']")
        user_link.click()

        self.selenium.switch_to.window(self.selenium.window_handles[1])
        assert 'twitter.com' in self.selenium.current_url

    # Tests clicking refresh function
    # Should return to homepage
    @tag('run')
    def test_refresh(self):
        url = self.selenium.current_url
        refresh_button = self.selenium.find_element_by_xpath("//a[@name='refreshButton']")
        refresh_button.click()

        assert (self.selenium.current_url == url)

    # Tests download csv file function
    # Should download a csv file of tweets
    def test_download(self):
        url = self.selenium.current_url
        download_button = self.selenium.find_element_by_xpath("//i[text()='file_download']")
        download_button.click()

        confirm_button = self.selenium.find_element_by_xpath("//button[@type='submit'][@name='download']")
        confirm_button.click()

        assert (self.selenium.current_url == url)

    # Tests pagination
    # Should click on 2 and go to second page, click on next page and go to third page
    def test_pagination(self):
        pagetwo = self.selenium.find_element_by_xpath("//a[@class='pagination-number'][@href='?page=2']")
        pagetwo.click()

        assert self.selenium.find_element_by_xpath("//span[@class='pagination-number pagination-current'][text()='2']")

        next_page = self.selenium.find_element_by_xpath("//a[@class='pagination-action'][@href='?page=3']")
        next_page.click()
        self.selenium.implicitly_wait(2)

        assert self.selenium.find_element_by_xpath("//span[@class='pagination-number pagination-current'][text()='3']")

    # Tests changing twitter search query
    # Should confirm new keyword is added to search query
    def test_edit(self):
        url = self.selenium.current_url

        change_button = self.selenium.find_element_by_xpath("//a[@id='change-query-btn']")
        change_button.click()

        keywords = self.selenium.find_element_by_xpath("//input[@name='pull-keywords']")
        keywords.clear()
        keywords.send_keys('Supreme Court')

        submit_button = self.selenium.find_element_by_xpath("//button[@name='change']")
        submit_button.click()

        assert (self.selenium.current_url == url)

        change_button = self.selenium.find_element_by_xpath("//a[@id='change-query-btn']")
        change_button.click()

        assert self.selenium.find_element_by_xpath("//input[@name='pull-keywords'][@value='Supreme Court']")

    @tag('run')
    def test_logout(self):
        logout = self.selenium.find_element_by_xpath("//a[@name='logoutButton']")
        logout.click()

        assert (self.selenium.current_url == self.live_server_url + '/login/')

    @tag('run')
    def test_userlogin(self):
        setupUser('test', 'cs499rocks')
        username = self.selenium.find_element_by_xpath("//input[@name='username']")
        username.send_keys('test')

        password = self.selenium.find_element_by_xpath("//input[@name='password']")
        password.send_keys('cs499rocks')

        login = self.selenium.find_element_by_xpath("//button[@type='submit']")
        login.click()

        assert (self.selenium.current_url == self.live_server_url + '/scotustwitter/')

# Filtering Tests
class FilteringTests(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super(FilteringTests, cls).setUpClass()
        cls.selenium = setupHeadlessWebdriver()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(FilteringTests, cls).tearDownClass()

    def setUp(self):
        self.selenium.get(self.live_server_url + '/login')

    # Test search function with AND selected
    # Should return tweets including all search queries
    def test_andsearch(self):
        and_button = self.selenium.find_element_by_xpath("//span[text()='AND']")
        and_button.click()

        users = self.selenium.find_element_by_xpath("//input[@name='users']")
        users.send_keys('malbertnews')

        hashtag = self.selenium.find_element_by_xpath("//input[@name='hashtags']")
        hashtag.send_keys('SCOTUS')

        keywords = self.selenium.find_element_by_xpath("//input[@name='keywords']")
        keywords.send_keys('Supreme Court')

        ''''date_from = self.selenium.find_element_by_xpath("//input[@name='from']")
        date_from.click()
        day = self.selenium.find_element_by_xpath("//button[@data-day='1']")
        day.click()
        ok_button = self.selenium.find_element_by_xpath("//button[text()='OK']")
        ok_button.click()'''

        search_button = self.selenium.find_element_by_xpath("//button[@name='search']")
        search_button.click()

        assert (self.selenium.find_element_by_xpath("//h6[contains(text(), '#SCOTUS')]") and self.selenium.find_element_by_xpath("//h6[contains(text(), 'Supreme Court')]") and self.selenium.find_element_by_xpath("//a[@href='http://www.twitter.com/malbertnews']"))


    # Tests search function with OR selected
    # Should return tweets with at least one of the search queries
    def test_orsearch(self):
        or_button = self.selenium.find_element_by_xpath("//span[text()='OR']")
        or_button.click()

        users = self.selenium.find_element_by_xpath("//input[@name='users']")
        users.send_keys("malbertnews")

        hashtag = self.selenium.find_element_by_xpath("//input[@name='hashtags']")
        hashtag.send_keys("SCOTUS")

        keywords = self.selenium.find_element_by_xpath("//input[@name='keywords']")
        keywords.send_keys("Supreme Court")

        '''date_from = self.selenium.find_element_by_xpath("//input[@name='from']")
        date_from.click()
        day = self.selenium.find_element_by_xpath("//button[@data-day='1']")
        day.click()
        ok_button = self.selenium.find_element_by_xpath("//button[text()='OK']")
        ok_button.click()'''

        search_button = self.selenium.find_element_by_xpath("//button[@name='search']")
        search_button.click()

        assert (self.selenium.find_element_by_xpath("//h6[contains(text(), '#SCOTUS')]") or self.selenium.find_element_by_xpath("//h6[contains(text(), 'Supreme Court')]") or self.selenium.find_element_by_xpath("//a[@href='http://www.twitter.com/malbertnews']"))