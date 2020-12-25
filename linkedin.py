# -*- coding: utf-8 -*-
import pymongo
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium import webdriver
import re
import demjson
import pymongo
import hashlib
import redis
import random
import json
import sys
class Linkedin:

    __TOP_CARD = "pv-top-card"
    path = '/usr/local/bin/chromedriver'


    def __init__(self,cookies):

        client = pymongo.MongoClient(host='192.168.33.63', port=27017)
        db = client.spider  # 获得数据库的句柄
        self.coll = db.linkedin_chrome  # 获得collection的句柄


        pool = redis.ConnectionPool(host='192.168.33.160', port=6379, db=0)
        self.redis_client = redis.Redis(connection_pool=pool)
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')
        # options.add_argument('--disable-gpu')
        options.add_argument('lang=zh_CN.UTF-8')
        self.driver = webdriver.Chrome(executable_path=self.path, chrome_options=options)
        self.driver.maximize_window()
        self.driver.delete_all_cookies()

        self.driver.get('https://www.linkedin.com/')
        self.add_cookies(cookies)


    def saveimage_one(self,img_url, area):
        #下载图片
        try:
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Cache-Control": "max-age=0",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
            }
            if img_url:
                try:
                    html = requests.get(img_url,headers=headers,timeout=10)
                except:
                    time.sleep(3)
                    html= requests.get(img_url,headers=headers,timeout=10)

                name = hashlib.md5(img_url.encode('utf-8')).hexdigest()
                namelist= area + '/images/' + name + '.jpg'
                print 'namelist',namelist
                with open(namelist,'wb') as f:
                    f.write(html.content)
                if namelist:
                    return namelist
                else:
                    return ''
        except Exception,e:
            print e
            return ''

    def add_cookies(self,cooies):
        #添加cookies
        for k, v in re.findall('[\s]*(.*?)=(.*?);',str(cooies)):
            dic = {}
            dic['domain'] = 'www.linkedin.com'
            dic['httpOnly'] = False
            dic['path'] = '/'
            dic['name'] = k
            dic['value'] = v
            self.driver.add_cookie(cookie_dict=dic)


    def get_url(self,url):
        driver = self.driver
        driver.get(url)
        time.sleep(4)
        # 获取更多工作经历
        try:
            s = driver.find_element_by_xpath(
                '//button[@class="pv-profile-section__see-more-inline pv-profile-section__text-truncate-toggle link link-without-hover-state"]')
            s.click()
        except:
            pass
        #翻页
        driver.execute_script("window.scrollTo(0, Math.ceil(document.body.scrollHeight/1.5));")
        time.sleep(2)

        return driver.page_source,driver

    def save_item(self,url):
        try:
            body,driver = self.get_url(url)
            content = body.replace('&quot;', '"').replace('&#92;', '\\').replace('&#61;', '=').replace('amp;', '')
            profile_txt = ' '.join(re.findall('\{"countryUrn"([\s\S]*?)</code>', content))
            user_item={}
            try:
                img_content = re.search('\s*{"data":{"firstName":.*?"included"', content).group() + u':[]}'
                img_content = demjson.decode(img_content.strip())['data']['picture']
                img = img_content['artifacts']
                root_img = img_content['rootUrl']
                user_item['images_url'] = root_img + img[1]['fileIdentifyingUrlPathSegment']
            except:
                user_item['images_url']=''

            firstname = re.findall('"firstName":"(.*?)"', profile_txt)
            lastname = re.findall('"lastName":"(.*?)"', profile_txt)
            if firstname and lastname:
                user_item['name'] = lastname[0] + firstname[0]
                summary = re.findall('"summary":"(.*?)"', profile_txt)
                if summary:
                    user_item['summary'] = summary[0]

            occupation = re.findall('"headline":"(.*?)"', profile_txt)
            if occupation:
                user_item['occupation'] = occupation[0]
            locationName = re.findall('"locationName":"(.*?)"', profile_txt)
            if locationName:
                user_item['location'] = locationName[0]


            networkInfo_txt = ' '.join(re.findall('(\{[^\{]*?profile\.ProfileNetworkInfo"[^\}]*?\})', content))
            connectionsCount = re.findall('"connectionsCount":(\d+)', networkInfo_txt) #好友数
            if connectionsCount:
                user_item['friend_num'] = connectionsCount[0].decode('utf-8')
            user_item['url'] = url

            # 工作经历
            list_position = []
            more_position =[] # 一个公司多种工作经历
            try:
                _ = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.ID, "experience-section")))
                exp = driver.find_element_by_id("experience-section")
            except:
                exp = None

            if (exp is not None):
                for position in exp.find_elements_by_class_name("pv-position-entity"):

                    try:
                        position.find_element_by_tag_name('li')
                        more_position.append(position)
                    except:

                        dict_position = {}
                        try:
                            position_title = position.find_element_by_tag_name("h3").text.encode('utf-8').strip()
                        except:
                            position_title = None
                        try:
                            # company = position.find_elements_by_tag_name("p")[1].text.encode('utf-8').strip()
                            company = position.find_element_by_class_name("pv-entity__secondary-title").text.encode('utf-8').strip()
                        except:
                            company =None
                        try:
                            # times = str(position.find_elements_by_tag_name("h4")[0].find_elements_by_tag_name("span")[1].text.encode('utf-8').strip())
                            times = str(position.find_element_by_class_name("pv-entity__date-range").find_elements_by_tag_name("span")[1].text.encode('utf-8').strip())
                            print times
                        except:
                            times=''
                        try:
                            # location = position.find_elements_by_tag_name("h4")[2].find_elements_by_tag_name("span")[1].text.encode('utf-8').strip()
                            location = position.find_element_by_class_name("pv-entity__location").find_elements_by_tag_name("span")[1].text.encode('utf-8').strip()
                        except:
                            location = None
                        try: #'pv-entity__description t-14 t-black t-normal inline-show-more-text inline-show-more-text--is-collapsed ember-view
                            description = position.find_element_by_class_name("pv-entity__description").text.encode('utf-8').strip()
                        except:
                            description = None

                        if position_title:
                            dict_position['occupation'] = position_title
                            print 'position_title：',position_title
                        else:
                            dict_position['occupation'] =''
                        if company:
                            dict_position['company'] =company
                            # print 'company：',company
                        else:
                            dict_position['company'] =''
                        if times:
                            times = times.replace('-','～')
                            times = times.replace('年','-').replace('月','').replace(' ','')
                            dict_position['time_period'] =times
                            print 'times：',times
                        else:
                            dict_position['time_period'] =''
                        if location:
                            dict_position['location'] = location
                            print 'location：',location
                        else:
                            dict_position['location'] =''
                        if description:
                            dict_position['description']=description
                            print 'description：',description
                        else:
                            dict_position['description'] =''
                        print '------------'
                        list_position.append(dict_position)

                for _more in more_position:
                    try:
                        company = _more.find_element_by_xpath('//h3[@class="t-16 t-black t-bold"]').text
                        company = company.replace(u'公司名称','').strip()
                    except:
                        company =''

                    for x in _more.find_elements_by_xpath('//li[@class="pv-entity__position-group-role-item"]'):
                        dict_position={}
                        try:
                            occupation =  x.find_element_by_tag_name('h3').text
                        except:
                            occupation=''

                        if u'职位头衔' in occupation:
                            occupation = occupation.replace(u'职位头衔','').strip()
                        else:
                            occupation=''

                        try:
                            time_period =  x.find_element_by_class_name('pv-entity__date-range').text
                        except:
                            time_period=''

                        if u'入职日期' in time_period:
                            time_period = time_period.replace(u'入职日期','').strip()
                        else:
                            time_period=''
                        try:
                            location =  x.find_element_by_class_name('pv-entity__location').text
                        except:
                            location =''
                        if u'所在地点' in location:
                            location = location.replace(u'所在地点','').strip()
                        else:
                            location=''

                        dict_position['occupation'] = occupation
                        dict_position['time_period'] = time_period
                        dict_position['location'] = location
                        dict_position['company'] = company
                        dict_position['description'] = 's'
                        list_position.append(dict_position)
            # get education
            l_edu = []

            try:
                _ = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.ID, "education-section")))
                edu = driver.find_element_by_id("education-section")
            except:
                edu = None
            if (edu is not None):
                for school in edu.find_elements_by_class_name("pv-profile-section__list-item"):
                    dict_edu={}
                    try:
                        university = school.find_element_by_class_name("pv-entity__school-name").text.encode('utf-8').strip()
                    except:
                        university =None
                    try:
                        degree = school.find_element_by_class_name("pv-entity__degree-name").find_elements_by_tag_name("span")[1].text.encode('utf-8').strip()
                    except:
                        degree=None
                    try:
                        field_of_study = school.find_element_by_class_name("pv-entity__fos").find_elements_by_tag_name("span")[1].text.encode('utf-8').strip()
                    except:
                        field_of_study=None
                    try:
                        times = school.find_element_by_class_name("pv-entity__dates").find_elements_by_tag_name("span")[1].text.encode('utf-8').strip()
                    except:
                        times=None
                    # from_date, to_date = (times.split(" ")[0], times.split(" ")[2])

                    if university:
                        print 'university：',university
                        dict_edu['school_name'] = university
                    else:
                        dict_edu['school_name'] =''
                    if degree:
                        dict_edu['degree_name']=degree
                        print 'degree：',degree
                    else:
                        dict_edu['degree_name'] =''
                    if times:
                        times = times.replace('-','～')
                        times = times.replace('年','').replace('月','').replace(' ','')
                        dict_edu['time_period'] = times
                        print 'times：',times
                    else:
                        dict_edu['time_period']=''
                    if field_of_study:
                        dict_edu['field_of_study'] =field_of_study
                        print 'field_of_study：',field_of_study
                    else:
                        dict_edu['field_of_study'] = ''
                    l_edu.append(dict_edu)
            user_item['work_experience'] =list_position
            user_item['edu_experience'] = l_edu
            image_file = self.saveimage_one(user_item['images_url'], 'linkedin')
            user_item['image_file'] = image_file
            user_item['nick_name']=''
            user_item['website_name']='linkedin'
            user_item['regist_time']=''
            user_item['hobby']=''
            process_url = re.sub('\?.*','',url)
            process_url = process_url[:-1]
            account_id = re.findall('linkedin\.com/in/(.+)',process_url)
            print 'account_id',account_id

            if account_id:
                user_item['account_id'] = account_id[0]
            else:
                user_item['account_id']=''

            uchar=user_item['location']
            if (uchar >= u'\u0041' and uchar <= u'\u005a') or (uchar >= u'\u0061' and uchar <= u'\u007a'):
                user_item['language'] = 'zh_us'

            if u'香港' in body:
                user_item['language'] = 'zh_hk'

            if u'台湾地区' in body or u'臺灣地區' in body:
                user_item['language'] = 'zh_tw'

            self.coll.insert(user_item)
            self.redis_client.hset('repeat_url', url, 0)

            try:#获取香港台湾地区人的LinkedIn
                if u'台湾地区' in body or u'臺灣地區' in body or u'香港' in body:
                    for elem in driver.find_elements_by_xpath('//div[@class="pv-browsemap-section"]/ul/li/a'):
                        _href = elem.get_attribute('href')
                        if not self.redis_client.hexists('repeat_url', _href):
                            print '------------'*5
                            print '_href',_href
                            print '------------'*5
                            self.redis_client.lpush('spider_url',json.dumps({'url':_href}))
            except Exception,e:
                print e
        except:
            self.redis_client.lpush('spider_url',json.dumps({'url':url}))
            sys.exit(0)

def func2():
    time_index = 0
    cookies1 = 'bcookie="v=2&8e84aa80-7659-469f-8349-9b396c665b95"; bscookie="v=1&202006220332308e6c8efe-491e-4eb8-82c5-387b25689d53AQE94Sv_AsGrxhjvC63QRZ0HvHUic4L5"; lissc=1; _ga=GA1.2.1271888274.1592796757; _gat=1; G_ENABLED_IDPS=google; AMCVS_14215E3D5995C57C0A495C55%40AdobeOrg=1; li_at=AQEDATFHbnwDgDfwAAABctqRwhwAAAFy_p5GHFYALWJQw94zwMyfgdi5fS5A1dx_mfzRmY5cQkURWP_C205c5VTXnaQt0zpgL-B4tC9FcTvf1DiVxSjvmtmA_7O9A4VibgnKzkb5W8cZeCHNITpVTw-1; liap=true; JSESSIONID="ajax:5936819940503912346"; lang=v=2&lang=zh-cn; UserMatchHistory=AQJQVYJtQwuWRgAAAXLakdWjA_U_R_taHo1orLf9OBi79va4LC9eUWlmiiYXhx8aJSNgd2dtK56nrGe3natnzc8IGQ8mk-Y7pE1Rh8VzrYjJikBMGXT7AOEeiIbnS5oRpBvbT7MyscdYj8j6Z344sOqd1S37IpPisv4PT_gJM-U8R1buLqOuHmcCkjcU--cNbj2prhJdIRYIMC8LUdr6xXfHjqUOyltEajDI3JzHiLe5; _guid=762abf49-5509-4789-b49a-6802c7f87233; li_sugr=130b54c6-2827-4819-9d61-280ce93b5f97; UserMatchHistory=AQJoxLZznVB1iQAAAXLakdphk8NUOjvuSaA7Cga8JfOsbl0WCORCgvAruFCWNkQrQHyrxvdQ2LaxhrXEJiWrj_hVqWfxuoVkAQ9RejNxCLxN7w; li_oatml=AQH46Xkcn90BcAAAAXLakduR4k2Nt2G_dgouQOQfTJsbW_OM53P2ox8mNjvWU6hDPUrWMjP7V8XfdhprJPzSvoNw7L2ZONU-; aam_uuid=87622535595564856621029788676448666238; AMCV_14215E3D5995C57C0A495C55%40AdobeOrg=-408604571%7CMCIDTS%7C18436%7CvVersion%7C4.6.0%7CMCMID%7C87434308674696483411046423241620697525%7CMCOPTOUT-1592812091s%7CNONE%7CMCAAMLH-1593409691%7C3%7CMCAAMB-1593409691%7Cj8Odv6LonN4r3an7LhD3WZrU1bUpAkFkkiY1ncBR96t2PTI%7CMCCIDH%7C1333906894; lidc="b=OB24:s=O:r=O:g=3201:u=2:i=1592804892:t=1592891285:v=1:sig=AQGkM8fa04B9CDyx6LU4cuBb0u1DX3bl"'
    linkedin1 = Linkedin(cookies=cookies1)
    while True:
        data = linkedin1.redis_client.lpop('spider_url')
        if data:
            url = demjson.decode(data)['url']
            print('url:', url)
            linkedin1.save_item(url)
        else:
            linkedin1.driver.close()
            linkedin1.driver.quit()
            break

        time.sleep(15)
        print('10')
        time_index += 1
        if time_index == 15:
            print('--------time_index-----------:', time_index)
            time_index = 0
            time.sleep(300)

def func1():
    #朱文塔
    time_index = 0
    cookies1 = 'lissc=1; bcookie="v=2&19ba00dc-b30a-47b9-8f23-0b11758bf7c4"; bscookie="v=1&2020062205494663ce3668-c862-42d9-88b9-5b547ccb4ac2AQGY-RLtpuDtLyp7UsfUyxSxR1dIUnIq"; _ga=GA1.2.906817325.1592804988; _gat=1; li_rm=AQE7hUBE9SYMoQAAAXLak14BCmrkMSzlwfJ9PPlg97anlL1Qh2n6uipb2Iehgf3byxNY9vTzn1k75KObsSv-w0qsihLZ0qhCAg7GyEDukk3oOVqSHy3Pf5Lv; liap=true; li_at=AQEDATFHhGQEbhKuAAABctqTa5wAAAFy_p_vnFYAuRbo4aKk1P5Le4OSD_JPVfndLJwqKloaVJ5uMvtT0LfP2wdRW37lpy3o2mNduepfpAxytXREy1E3CSsYdIUNhl0nmScdheJyE_m7vlwhu9jqmjOn; JSESSIONID="ajax:6976259105379592431"; lang=v=2&lang=zh-cn; UserMatchHistory=AQJpqoK10dYdPgAAAXLak3YocDRKdx4pGXyswq4y0g-OPHxX3Dt_5gw88XveG5UbDeHUJOQiTAUW_Baa2Rg5IwON8hnscYXwWmDxj2mXaedP4xJbI4ZQXgoJ2aBNfZxCEXEHRzelBd3n2nLYbHRAfW7De6WWAYSqcEY22nd0yZAP0LRXpxeuFF34d4YOGDPBYX6LujtkmuIywWerfRs0ItCYu3LkBXaQhJ9p3iRhbYMp; li_sugr=4dbc4759-1292-4884-ad5d-01fdf3f758b1; _guid=b1d69494-8a55-492a-8648-9a3e1332aab3; UserMatchHistory=AQKnEDmk8fR03gAAAXLak3kgNhMFiO2b2-gfweDxKWVdHf-zddNo5J8qO1MJwkBiUoJIPiBewvtPpN67EEkBfjz75pLLXZlCZqaAtiiv6qhnsQ; li_oatml=AQHIgCCIivtIlQAAAXLak3pkpvcOzXyUHHm0i4p5xPfPSj9YOXcmgavp5gX9xbcjIMexUdLjiSYCUUuZg8N9IKyy3EGdRLm_; AMCVS_14215E3D5995C57C0A495C55%40AdobeOrg=1; AMCV_14215E3D5995C57C0A495C55%40AdobeOrg=-408604571%7CMCIDTS%7C18436%7CMCMID%7C53703146757728967611993109130623758504%7CMCAAMLH-1593409798%7C3%7CMCAAMB-1593409798%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1592812198s%7CNONE%7CMCCIDH%7C1673198207%7CvVersion%7C4.6.0; aam_uuid=53525628010312678901974790011636695907; lidc="b=OB32:g=2911:u=2:i=1592805001:t=1592891394:s=AQHdnnHw-DbPqDjdOMQCuVLtMaMeosi4"'
    linkedin1 = Linkedin(cookies=cookies1)
    while True:
        data = linkedin1.redis_client.lpop('spider_url')
        if data:
            url = demjson.decode(data)['url']

            if not linkedin1.redis_client.hexists('repeat_url', url):
                print('url:', url)
                linkedin1.save_item(url)
                time.sleep(15)
            else:
                print('url 存在')
        else:
            linkedin1.driver.close()
            linkedin1.driver.quit()
            break

        time_index += 1
        if time_index == 15:
            print('--------time_index-----------:', time_index)
            time_index = 0
            time.sleep(300)

if __name__ == '__main__':
    import multiprocessing
    p1 = multiprocessing.Process(target = func1)
    p2 = multiprocessing.Process(target = func2)
    p1.daemon = True
    p2.daemon = True
    p1.start()
    p2.start()
    p1.join()
    p2.join()
    print("end!")
