#Version : 1.9
#to calculate distance between cordinates
from geopy.distance import geodesic
#for logging
import logging
#for bing geocoding service
import geocoder

from datetime import datetime
#mongodb client
from pymongo import message, mongo_client

#selenium

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
#from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select   
from selenium.common.exceptions import TimeoutException
import time
import pymongo
from pymongo import MongoClient
from pymongo import collection
import ssl
#to read statelist.dat
import pickle
#for email notifications
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart





#declaring logger properties
logging.basicConfig(filename="scraper.log", format='%(asctime)s %(message)s', filemode='a')
logger=logging.getLogger()
logger.setLevel(logging.INFO)
#mongodb connection strings
userDBclient = MongoClient("mongodb://connectstring")
dbclient = MongoClient("mongodb://connectstring0")
#bing map api key
bing_map_key = "notbingkey"

#reading data from statelist.dat for stateList and list_of_all_district
stateListFileName = "statelist.dat"
list_of_all_district = []
stateList = []
with open(stateListFileName,"rb") as f:
    stateList = pickle.load(f)
    list_of_all_district = pickle.load(f)

#reading data from bgandbctypes.dat file for bcTypeList and bgTypeList using pickel
bgandbcListFilename = "bgandbctypes.dat"
bgTypelist = []
bcTypelist = []
with open(bgandbcListFilename,"rb") as f:
    bgTypelist = pickle.load(f)
    bcTypelist = pickle.load(f)


#to keep track of entery count
#was used in earlier versions to check when to change page but, currently only used for logging purposes
enterycount = 0
globalenterycount = 0



#eraktkosh stockavailability url to scrape
url = "https://www.eraktkosh.in/BLDAHIMS/bloodbank/stockAvailability.cnt"



#infinite loop to keep running program endlessly
while True:
    #looping through all bloodcomponents one by one
    for bdcomponent in bcTypelist:
        #break #uncomment for testing campschedule only and skipping blood availability 
        #error control while loop
        #basic structure try scraping data if it fails try again if suceed,break the loop

        while True:
            try:
                #uncomment and comment options based on browser you are using
               
                options = Options()
                options.headless = False
                driver = webdriver.Firefox(options = options)
                """
                
                chrome_options = Options()
                chrome_prefs = {}
                chrome_options.experimental_options["prefs"] = chrome_prefs
                chrome_prefs["profile.default_content_settings"] = {"images": 2}
                chrome_prefs["profile.managed_default_content_settings"] = {"images": 2}
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--remote-debugging-port=9222")

                driver = webdriver.Chrome(options=chrome_options)
                 """
            
                
               #for a bug when chrome woud just timeout while loading
                while True:
                    try:
                        driver.get(url)
                    except TimeoutException:
                        logger.warning("Timeout, retrying...")
                        continue
                    else:
                        break

                enterycount = 0


                time.sleep(10)
                #number of result to be displayed to 100
                tablelengthSelector = Select(driver.find_element_by_name("example-table_length"))
                tablelengthSelector.select_by_visible_text("100")
                time.sleep(2)
                #selecting required 
                componentSelector = Select(driver.find_element_by_id("bcType"))
                componentSelector.select_by_visible_text(bdcomponent)
                time.sleep(3)
                #looping through all states in stateList
                for statelistelement in stateList:
                    #selecting currently rquired state and sleeping to let changes appear on page
                    stateselector = Select(driver.find_element_by_id("stateCode"))
                    stateselector.select_by_visible_text(statelistelement)
                    time.sleep(5)
                    #clicking search button
                    searchbutton = driver.find_element_by_xpath("//button[@id='searchButton' and not(@disabled)]")
                    searchbutton.click()
                    time.sleep(2)
                    #searchbutton = driver.find_element_by_xpath("//button[@id='searchButton' and not(@disabled)]")
                    #searchbutton.click()
                    #driver.find_element_by_id("searchButton").click
                    #print("clicked searchebutton")
                    #searchbutton = driver.find_element_by_xpath('//*[@id="searchButton"]')
                    time.sleep(7)
                    #print("clicked searchebutton")
                    #disctionary to stored scraped data
                    enteryDictionary = {}
                

                    #selecting mongodb to push data to based on current value of bdcomponent
                    db = dbclient[bdcomponent.replace(" ","")]
                    while True:
                        #if table is empty break the loop and continue with next state
                        if not len(driver.find_elements_by_class_name("dataTables_empty")) == 0:
                            #print("no rows skipping")
                            break
                        #find number of rows
                        rows = driver.find_elements_by_xpath("/html/body/div[3]/div[4]/div[3]/table/tbody/tr")
                        
                        number_of_rows = len(rows)
                        #print(number_of_rows)
                        #looping through each row
                        for i in range(1,(number_of_rows + 1)):
                            #putting data to enterycount dictionary from various colums of given row
                            bloodbankInfoFeild = driver.find_element_by_xpath("/html/body/div[3]/div[4]/div[3]/table/tbody/tr["+str(i)+"]/td[2]")
                            enterycount = enterycount + 1
                            #seprating address name and contact of bloodbank
                            bb_details = bloodbankInfoFeild.text.split("\n")
                            #finding out which state the bloodbank belongs based on its address
                            for state in stateList:
                                if state in bb_details[1]:
                                    collection = db[state.replace(" ","")]
                                    enteryDictionary["state"]=state
                                    #finding out which district bloodbank is located in based on its state and address
                                    for districtName in list_of_all_district[stateList.index(state)]:
                                        if districtName in bb_details[1]:
                                            enteryDictionary["district"]=districtName
                                
                            #dont push invalid enteries to database
                            if "null" in bb_details[1]: #to account for invalid enteries present in table
                                continue
                                            
                            enteryDictionary["bb_name"]=bb_details[0]
                            enteryDictionary["bb_address"]=bb_details[1]
                            enteryDictionary["bb_contact"]=bb_details[2]

                            category_feild = driver.find_element_by_xpath("/html/body/div[3]/div[4]/div[3]/table/tbody/tr["+str(i)+"]/td[3]")
                            Bloodbank_category = category_feild.text
                            enteryDictionary["bb_category"]=Bloodbank_category
                          
                            #if aavaibality is not available then set all blood group stock to zero
                            availability_feild = driver.find_element_by_xpath("/html/body/div[3]/div[4]/div[3]/table/tbody/tr["+str(i)+"]/td[4]")
                            if "Not Available" in availability_feild.text:
                                for bgroup in bgTypelist:
                                    enteryDictionary[bgroup+"_is_available"]=False
                                    enteryDictionary[bgroup+"_quantity"]=0
                                #print(enteryDictionary)
                                not_available = True


                                #logging.info("Not Available")

                            #blood stock phraser     
                            else:
                                availability_feild_text = availability_feild.text
                                availability_feild_text.replace("Available, ","")
                                availability_feild_list = availability_feild_text.split(",")
                                for bgstock in availability_feild_list:
                                    for bgroup in bgTypelist:
                                        if bgroup in bgstock:
                                            #fixed bug where AB group were counted for B also
                                            if bgTypelist.index(bgroup) in [4,5] and "A" in bgstock: 
                                                continue
                                            
                                            
                                
                                            quantity = bgstock.replace(bgroup+":","")
                                            enteryDictionary[bgroup+"_is_available"]=True
                                            enteryDictionary[bgroup+"_quantity"]=quantity
                            last_update_field = driver.find_element_by_xpath("/html/body/div[3]/div[4]/div[3]/table/tbody/tr["+str(i)+"]/td[5]")
                            #if last updated field is "" that is it doesnt have any text use current time
                            if last_update_field.text == "":
                                now = datetime.now()
                                
                                current_time = now.strftime("%H:%M:%S")

                                enteryDictionary["lastupdated"]=current_time
                            else:
                                enteryDictionary["lastupdated"]=last_update_field.text
                            instituteType = driver.find_element_by_xpath("/html/body/div[3]/div[4]/div[3]/table/tbody/tr["+str(i)+"]/td[6]")
                            enteryDictionary["instituteType"]=instituteType.text
                            #print(enteryDictionary)
                            #print(collection.find_one({"bb_name":bb_details[0],"bb_address":bb_details[1]}))
                            #time.sleep(1000)
                            
                            #find an replace enterydictionary in the mongodb
                            collection.find_one_and_replace({"bb_name":bb_details[0],"bb_address":bb_details[1]},enteryDictionary,upsert=True)
                            #print(collection.find_one({"bb_name":bb_details[0],"bb_address":bb_details[1]}))
                            #time.sleep(100)

                            
                            
                                            
                        #check how manyb bloodbanks are in state and how many are displayed used to go to next page if it exists   
                        table_info = driver.find_element_by_id("example-table_info")
                        table_info_list = table_info.text.split()
                            
                        if not table_info_list[3] == table_info_list[5]:
                            logger.warning("enterycount : "+str(enterycount))
                            driver.find_element_by_xpath('//*[@id="example-table_next"]').click()
                            time.sleep(4)
                        else:
                            logger.warning("finished state "+statelistelement)
                            break
            except Exception as e:
                #if an exception occurs log it in logs and try agains
                logger.warning("some error has occured retrying"+str(e))
                driver.quit()
                time.sleep(10)
                continue                
            #else break the loop and move on to next state        
            break
                
        #close driver after finishing catergory and sleep for 10 seconds before continuing    
        driver.quit()
        logger.warning("finished category : "+bdcomponent)
        time.sleep(10)
    

#start of camp schedule scraper
#mongodb database and collection to store camps data
    campdb = dbclient["camps"]
    campcols = campdb["campcols"]
    #get a all the camps present in database
    camps_present = campcols.find()
    already_scraped_camps = []
    for campdata in camps_present:
        already_scraped_camps.append(campdata)
     #delete the campcols
    campcols.drop()

    try:
        
        #uncomment below lines of code based on browser you are using
        
        options = Options()
        options.headless = False
        driver = webdriver.Firefox(options = options)
        """
        
        chrome_options = Options()
        chrome_prefs = {}
        chrome_options.experimental_options["prefs"] = chrome_prefs
        chrome_prefs["profile.default_content_settings"] = {"images": 2}
        chrome_prefs["profile.managed_default_content_settings"] = {"images": 2}
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--remote-debugging-port=9222")
        driver = webdriver.Chrome(options=chrome_options)
       """
       #open campschedule page in driver
        driver.get("https://www.eraktkosh.in/BLDAHIMS/bloodbank/campSchedule.cnt")
        time.sleep(10)
        #select show all option
        entryselector = Select(driver.find_element_by_xpath("/html/body/div[3]/div[4]/div[2]/div[1]/label/select"))
        entryselector.select_by_visible_text("All")
        #get number of rows present in table
        rows = driver.find_elements_by_xpath("/html/body/div[3]/div[4]/div[2]/table/tbody/tr")
        for i in range(1,len(rows)+1):
            is_previous_camp = False
            #if the camp data was already present in database just insert it back and continue
            for previous_camp in already_scraped_camps:
                if previous_camp["camp_address"] == driver.find_element_by_xpath('/html/body/div[3]/div[4]/div[2]/table/tbody/tr['+str(i)+']/td[5]').text:
                    campcols.insert_one(previous_camp)
                    #logger.warning("camp already scraped")
                    is_previous_camp = True
                    break

            if is_previous_camp == True:
                continue
            else:
                #else scrape data regarding new camp
                campdict = {}
                campdict["camp_date"]=driver.find_element_by_xpath('/html/body/div[3]/div[4]/div[2]/table/tbody/tr['+str(i)+']/td[2]').text
                campdict["camp_time"]=driver.find_element_by_xpath('/html/body/div[3]/div[4]/div[2]/table/tbody/tr['+str(i)+']/td[3]').text  
                campdict["camp_name"]=driver.find_element_by_xpath('/html/body/div[3]/div[4]/div[2]/table/tbody/tr['+str(i)+']/td[4]').text  
                campdict["camp_address"]=driver.find_element_by_xpath('/html/body/div[3]/div[4]/div[2]/table/tbody/tr['+str(i)+']/td[5]').text  
                campdict["state"]=driver.find_element_by_xpath('/html/body/div[3]/div[4]/div[2]/table/tbody/tr['+str(i)+']/td[6]').text  
                campdict["district"]=driver.find_element_by_xpath('/html/body/div[3]/div[4]/div[2]/table/tbody/tr['+str(i)+']/td[7]').text 
                campdict["camp_contact"]=driver.find_element_by_xpath('/html/body/div[3]/div[4]/div[2]/table/tbody/tr['+str(i)+']/td[8]').text 
                campdict["camp_conducted_by"]=driver.find_element_by_xpath('/html/body/div[3]/div[4]/div[2]/table/tbody/tr['+str(i)+']/td[9]').text
                campdict["camp_organized_by"]=driver.find_element_by_xpath('/html/body/div[3]/div[4]/div[2]/table/tbody/tr['+str(i)+']/td[10]').text
                #using geocoder to geocode address into cordinates
                geosearch = geocoder.bing(campdict['camp_address'],key=bing_map_key)
                campdict["coordinates"] = geosearch.json["raw"]["point"]["coordinates"]
                #short_camp_url = urlshortner.tinyurl.short("https://www.google.com/maps/search/?api=1&query="+campdict["camp_address"])
                googlemap_camp_url = ("https://www.google.com/maps/search/?api=1&query="+campdict["camp_address"])
                
                #email notification
                #geting list of all the user that are subscribed to maillist
                campUserdb = userDBclient["campemaildb"]
                usercols = campUserdb["maillist"]
                #print(campdict)
                mailList = []
                for userDetails in usercols.find():
                    mailList.append(userDetails)
                #for every user if distance between user and camp is less than decided value send email to user regarding the camp
                for mailSub in mailList:
                    if mailSub["notify_distance"] > geodesic(campdict["coordinates"],mailSub["coordinates"]).km:
                        message = MIMEMultipart("alternative")
                        message["Subject"] = "New BloodCamp organised near you"
                        message["From"] = "notify@delta.tarang.ovh"
                        message["To"] = mailSub["email"]
                        html_emailbody = """\
<html>
  <body>
    <p>A New BloodCamp is being Organised near your area<br>
    Camp Details:<br>
    Camp Name : """+campdict["camp_name"]+"""<br>
    Camp Date : """+campdict["camp_date"] +"""<br>
    At : """+campdict["camp_time"]+"""<br>
    Address : """+campdict["camp_address"]+"""<br>
    Contact : """+campdict["camp_contact"]+"""<br>
    Organised by : """+campdict["camp_conducted_by"]+"""<br>


       
       <a href=" """+googlemap_camp_url+ """ ">click here to view it on Google map</a> 
       <br><br>    <br><br>
    Want to stop recieving emails like this?<a href="http://delta.tarang.ovh/unsubscribe/"""+mailSub["unsub"]+""" ">Click here to unsubscribe</a>
    </p>
  </body>
</html>
"""
                                                
                        
                        
                        
                        
                        
                        
                        part_email = MIMEText(html_emailbody, "html")
                        message.attach(part_email)
                        #login to smtp server with credentials and send email
                        with smtplib.SMTP_SSL("box.tarang.ovh", 465) as server:
                            server.login("notify@delta.tarang.ovh","raspberry")
                            server.sendmail(
                                "notify@delta.tarang.ovh", mailSub["email"], message.as_string()
                            )
                        logger.warning("Email sent")
                         
                        time.sleep(5)
                        







                
                #finally insert the camp details in mongodb
                campcols.insert_one(campdict)
                
        
        
        
        #exit browser
        driver.quit()
        logger.warning("Camp schedule scraped")
        #time.sleep(1000)






    except:
        driver.quit()
        time.sleep(10)
        