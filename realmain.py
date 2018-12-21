# -*- coding: utf-8 -*-
import json
import os
import re
import urllib.request
import time

# 쓰레드, 큐를 위한 라이브러리 추가
import multiprocessing as mp
from threading import Thread
from slacker import Slacker
from bs4 import BeautifulSoup
from slackclient import SlackClient
from flask import Flask, request, make_response, render_template
from selenium import webdriver

app = Flask(__name__)
menu = int()

# slack_token = "xoxb-"
# slack_client_id = ""
# slack_client_secret = ""
# slack_verification = ""
slack_token = 'xoxb-504131970294-508554322023-se0uipgMqrYq6rGjwFs8Pa8C'
slack_client_id = '504131970294.506896754497'
slack_client_secret = '7237e729f985f18a1ee5d2dd8a255185'
slack_verification = 'Z5PZGra13NyA3Gi7z6Wmz8BQ'
slack = Slacker('xoxb-504131970294-508554322023-se0uipgMqrYq6rGjwFs8Pa8C')

sc = SlackClient(slack_token)

def _crawl_movie_rank():
    url = 'https://movie.naver.com/movie/sdb/rank/rmovie.nhn'
    req = urllib.request.Request(url)
    sourcecode = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(sourcecode, "html.parser")
    keywords=[]
    for i, keyword in enumerate(soup.find_all('div',class_='tit3')):
        if i<10:
            keywords.append(str(i+1)+'위 '+keyword.get_text().strip())
    return u'\n'.join(keywords)

# 영화상세 페이지 찾기
def _crawl_movie_detail(title):
    driver = webdriver.Chrome()
    driver.implicitly_wait(3)
    url = 'https://movie.naver.com'
    driver.get(url)

    driver.find_element_by_id('ipt_tx_srch').send_keys(title)
    driver.find_element_by_xpath("""//*[@class="srch_field_on _view"]/button""").click()
    current_url = driver.current_url
    req = urllib.request.Request(current_url)
    sourcecode = urllib.request.urlopen(current_url).read()
    soup = BeautifulSoup(sourcecode, "html.parser")
    t = soup.find('ul', class_='search_list_1')
    movie_detail = t.find('a')['href']
    return url+movie_detail

#영화 상세페이지 에서 리뷰 (+점수)
def _crawl_movie_reple(title):
    url=_crawl_movie_detail(title)
    req = urllib.request.Request(url)
    sourcecode = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(sourcecode, "html.parser")

    reples=[]
    nums=[]
    keywords=[]
    for i, keyword in enumerate(soup.find_all('div', class_='score_result')):
        for j in keyword.find_all('div', class_='star_score'):
            d = (j.get_text().strip())
            nums.append(d)
        for j in keyword.find_all('div', class_='score_reple'):
            reple = j.find('p')
            reple = (reple.get_text().strip())
            reples.append(reple)
    #영화제목 먼저 띄우고 댓글이랑 점수 표시
    for i in range(len(nums)):
        keywords.append('\n'+reples[i]+'\t'+nums[i]+'점')
    return u'\n'.join(keywords)

#영화 줄거리
def _crawl_movie_summary(title):
    url = _crawl_movie_detail(title)
    req = urllib.request.Request(url)
    sourcecode = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(sourcecode, "html.parser")

    return soup.find('p',class_='con_tx').get_text()




# 현재 상영작 크롤링
def _crawl_naver_now_movie():
    url = 'https://movie.naver.com/movie/running/current.nhn'
    req = urllib.request.Request(url)

    sourcecode = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(sourcecode, "html.parser")

    keywords = []
    # 영화 제목
    titles = []
    # 영화 관람가
    ratings = []
    # 영화 카테고리
    categorys = []
    # 영화 평점
    nums = []

    for i, keyword in enumerate(soup.find_all("dl", class_='lst_dsc')):
        # print(keyword)
        if i < 10:
            # 영화제목
            title = keyword.find('dt', class_='tit')
            titles.append(title.find("a").get_text())
            # 관람연령 파싱
            new_rating = (str(title.select("span")))
            new_rating = new_rating.split('>')[1].split('<')[0]
            # print(new_rating)
            ratings.append(new_rating)

            # 평점 파싱
            nums.append(keyword.find('span', class_='num').get_text())
            # 카테고리 파싱
            tag = keyword.find('span', class_='link_txt')
            category_list = []
            for category in tag.get_text().split(','):
                # print(category.strip())
                category_list.append(category.strip())
                # print(category_tuple)
            categorys.append(category_list)

    for i in range(len(ratings)):
        keywords.append(
            '영화제목: ' + titles[i] + '\n관람연령: ' + ratings[i] + '\n평점: ' + nums[i] + '\n카테고리: ' + str(categorys[i]) + '\n')

    return u'\n'.join(keywords)

def search_theater(search):
    search_text=search
    keyword=list()
    keyword.append(search_text)
    keyword.append(" 영화관")
    next_button = webdriver.Chrome()

    next_button.get("https://search.naver.com")
    next_button.find_element_by_name("query").send_keys(keyword)

    next_button.find_element_by_xpath("//span[@class='ico_search_submit']").click()

    # URL 주소에 있는 HTML 코드를 soup에 저장합니다.
    soup = BeautifulSoup(urllib.request.urlopen(next_button.current_url).read(), "html.parser")
    keywords=list()
    theater=list()
    theater_list = soup.find("div", class_="_wrap_theater_list")
    kk = theater_list.find("tbody", class_="_theater_list")
    for i in kk.find_all('span',class_='map_pst'):
        temp=i.get_text().split('\n')
        temp=temp[0][1:]
        theater.append(temp)
    for num,i in enumerate(kk.find_all("span", class_="els")):
        keywords.append(theater[num]+'\t'+ i.get_text())
    return u'\n'.join(keywords)

def home(channel):
    slack.chat.post_message(channel, "메뉴를 선택해주세요")
    slack.chat.post_message(channel, "1. 상영영화")
    slack.chat.post_message(channel, "2. 영화순위")
    slack.chat.post_message(channel, "3. 영화평점")
    slack.chat.post_message(channel, "4. 영화줄거리")
    slack.chat.post_message(channel, "5. 근처영화관")
    return

# threading function
def processing_event(queue):

    while True:
        # 큐가 비어있지 않은 경우 로직 실행
        if not queue.empty():
            slack_event = queue.get()
            print('gueue get')
            global menu
            # Your Processing Code Block gose to here
            channel = slack_event["event"]["channel"]
            text = slack_event["event"]["text"]

            if '메뉴' in text:
                home(channel)


            elif '1' in text:
                sc.api_call(
                    "chat.postMessage",
                    channel=channel,
                    text=_crawl_naver_now_movie()
                )
            elif '2' in text:
                sc.api_call(
                    "chat.postMessage",
                    channel=channel,
                    text=_crawl_movie_rank()
                )

            elif menu == 3:
                sc.api_call(
                    "chat.postMessage",
                    channel=channel,
                    text=_crawl_movie_reple(text.split()[1])
                )
                menu = 0

            elif '3' in text:
                menu = 3
                slack.chat.post_message(channel, "영화명을 입력해주세요")

            elif menu == 4:
                sc.api_call(
                    "chat.postMessage",
                    channel=channel,
                    text=_crawl_movie_summary(text.split()[1])
                )
                menu = 0

            elif '4' in text:
                menu = 4
                slack.chat.post_message(channel, "영화명을 입력해주세요")

            elif menu == 5:
                sc.api_call(
                    "chat.postMessage",
                    channel=channel,
                    text=search_theater(text.split()[1])
                )
                menu = 0

            elif '5' in text:
                menu = 5
                slack.chat.post_message(channel, "주소를 입력해주세요")





# 이벤트 핸들하는 함수
def _event_handler(event_type, slack_event):

    if event_type == "app_mention":
        event_queue.put(slack_event)
        return make_response("App mention message has been sent", 200, )


@app.route("/listening", methods=["GET", "POST"])
def hears():
    slack_event = json.loads(request.data)

    if "challenge" in slack_event:
        return make_response(slack_event["challenge"], 200, {"content_type":
                                                                 "application/json"
                                                             })

    if slack_verification != slack_event.get("token"):
        message = "Invalid Slack verification token: %s" % (slack_event["token"])
        make_response(message, 403, {"X-Slack-No-Retry": 1})

    if "event" in slack_event:
        event_type = slack_event["event"]["type"]
        return _event_handler(event_type, slack_event)

    # If our bot hears things that are not events we've subscribed to,
    # send a quirky but helpful error response
    return make_response("[NO EVENT IN SLACK REQUEST] These are not the droids\
                        you're looking for.", 404, {"X-Slack-No-Retry": 1})


@app.route("/", methods=["GET"])
def index():
    return "<h1>Server is ready.</h1>"


if __name__ == '__main__':
    event_queue = mp.Queue()

    p = Thread(target=processing_event, args=(event_queue,))
    p.start()
    print("subprocess started")

    app.run('0.0.0.0', port=8080)
    p.join()