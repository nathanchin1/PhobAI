import os
import time
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
import json
import boto3


import urllib.request

# os.chdir('image_data')
#Selenium code to scroll to bottom of the page

# search_query = "jindo+dog"

def lambda_handler(event, context): 

    def null_count(l):
    #given a list l, find the number of null
        null_count = 0
        
        for element in l:
            if element == None:
                null_count += 1
                
        return null_count

    s3 = boto3.client('s3')
    bucket_name = 'phobai-calhacks'
    folder_prefix = 'Users/userid1/scrapedimages/'
    
    # folder_path = 'Users/ 'get user id here' / scrapedimages/'

    old_list_queries = ['lizards']

    # rerun_queries = ['athletic aesthetic outfit']

    # colors = ["soft pink", "forest green", "sage green", "creamy beige", "dusty lavender", 
    #           "pastel", "floral", "beige", "gray", "white", 
    #           "black", "pale pink", "light blue", "earthy", "monochrome", 
    #           "denim", "red", "blue", "black", "orange", 
    #           "olive", "navy", "pastel blue", "metallic", "brown", 
    #           "burgundy", "khaki", "yellow", "ivory", "mint green", 
    #           "hot pink", "neon green", "polka dots"]

    # color_codes = {
    #     0: [0, 1, 2, 3, 4],
    #     1: [5, 6, 0],
    #     2: [7, 8, 9, 10, 11, 12, 13, 14, 15], 
    #     3: [24, 21, 25, 10, 8, 20],
    #     4: [21, 9, 5, 16, 17, 26],
    #     5: [16, 17, 18, 19, 27], 
    #     6: [3, 20, 13],
    #     7: [9, 10, 8, 7, 21],
    #     8: [18, 8], 
    #     9: [0, 28, 12, 29],
    #     10: [10, 9, 8],
    #     11: [10, 30, 17],
    #     12: [15, 23, 5], 
    #     13: [13, 1, 26],
    #     14: [23, 31],
    #     15: [30, 0, 5], 
    #     16: [0, 2, 5, 6, 28],
    #     17: [30, 5],
    #     18: [7, 0], 
    #     19: [0, 5, 32, 6]
    # }

    # colored_old_list_queries = old_list_queries[:]
    # rerun_indexes = [5]
    # colored_old_list_queries = rerun_queries[:]
    # for i in range(len(old_list_queries)): 
    #     if i in rerun_indexes:
    #         for j in range(len(color_codes[i])): 
    #             color = colors[color_codes[i][j]]
    #             color_query_added = old_list_queries[i] + " " + color
    #             colored_old_list_queries.append(color_query_added)

    # p1_list_queries = [old.replace(' ', '+') for old in colored_old_list_queries]
    # new_list_queries = [old.replace('/', '%2F') for old in p1_list_queries]

    # print(new_list_queries)

    print(os.getcwd())
    # search_query = "skimpy+clothing"
    counter = 0
    max_count = 10

    geckodriver_path = os.path.join(os.getcwd(), 'geckodriver')
    # geckodriver_path = '/tmp/geckodriver'
    # firefox_binary_path = '/tmp/firefox-bin'
    # firefox_binary_path = os.path.join(os.getcwd(), 'firefox')


    # service = Service()
    # options = webdriver.FirefoxOptions()
    service = Service(executable_path=geckodriver_path)
    options = webdriver.FirefoxOptions()
    # options.binary_location = firefox_binary_path
    # options.add_argument('--no-sandbox')
    options.add_argument("-headless")


    # geckodriver_path = '/tmp/geckodriver'
    # firefox_binary_path = '/tmp/firefox-bin'

    for q in old_list_queries:

        # folder_path = colored_old_list_queries[counter] 
        # folder_path = "Test1"

        link = "https://www.google.com/search?q={}&udm=2".format(q)
        # link = "https://www.pinterest.com/search/pins/?q={}&tbm=isch".format(search_query)
        # DRIVER_PATH = "/Users/manuthakur/HYP/geckodriver"
        # Driver path not necessary if geckodriver zipped into lambda!

        # driver = webdriver.Chrome(executable_path=DRIVER_PATH)
        # driver = webdriver.Firefox(
        #     executable_path=DRIVER_PATH     # Use service option for Firefox
        # )
        driver = webdriver.Firefox(service=service, options=options)

        driver.get(link)

        SCROLL_PAUSE_TIME = 5

        # Get scroll height
        last_height = driver.execute_script("return document.body.scrollHeight")

        while True:
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait to load page
            time.sleep(SCROLL_PAUSE_TIME)

            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
            #break #insert press load more
                try:
                    element = driver.find_elements("class name", "mye4qd") #returns list
                    element[0].click()
                except:
                    break
            last_height = new_height
            
        print("Reached the end of page")

        # image_links = driver.find_elements_by_tag_name('img')
        # image_links = driver.find_elements("tag name", "img")
        image_links = driver.find_elements("xpath", "//img[contains(@class, 'YQ4gaf') and not(contains(@class, 'zr758c'))]")
        total = len(image_links)
        print(total)

        data_src_links = [image_links[i].get_attribute('data-src') for i in range(total)]
        src_links = [image_links[i].get_attribute('src') for i in range(total)]

        data_src_null_count = null_count(data_src_links)
        print(data_src_null_count) #117    

        src_null_count = null_count(src_links)
        print(src_null_count) #153

        print(len(src_links))

        for i,element in enumerate(data_src_links):
            # print(len(data_src_links))
            if element == None:
                data_src_links[i] = src_links[i]
        
        print("Nulls: {}, Length: {}".format(null_count(data_src_links), len(data_src_links)))

        # base_path = folder_path
        
        good_links = list(filter(None, data_src_links))
        
        for i,link in enumerate(good_links):

            if (counter < max_count): 
        
                # if (0 <= i <= 7) or (i % 2 != 0): 

                name = f'{q}{i}.png'

                # Download image
                image_data = urllib.request.urlopen(link).read()

                # Upload image to S3
                s3_key = folder_prefix + name  # Set S3 key including folder structure
                s3.put_object(Bucket=bucket_name, Key=s3_key, Body=image_data)

                counter += 1
                time.sleep(2)
            else: 
                return

        print(os.getcwd())
        
        driver.quit()
    