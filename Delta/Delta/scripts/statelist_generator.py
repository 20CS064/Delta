#this script is used to create "statelist.dat"
import pickle
#libraries required for webscraping
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import Select   

import time #for time.speel()

#empty lists to be used later
stateList = []
list_of_all_district = []



url = "https://www.eraktkosh.in/BLDAHIMS/bloodbank/stockAvailability.cnt" #url to be scraped
filename = "statelist.dat" #filename for saving data

options = Options()
options.headless = False  #wether to launch firefox in headless mode or not
driver = webdriver.Firefox(options = options)

driver.get(url)
time.sleep(10)

#finding state list selector 
stateListSelector = Select(driver.find_element_by_id("stateCode"))

#geting options form stateListSelector

stateListOptions = stateListSelector.options
for stateOption in stateListOptions:
    if stateListOptions.index(stateOption) in [0,1]:
        continue
    stateList.append(stateOption.text)
    stateListSelector.select_by_visible_text(stateOption.text)
    time.sleep(3)
    distListSelector = Select(driver.find_element_by_id("distList"))
    distOptions = distListSelector.options
    distList = []
    for dist in distOptions:
        if distOptions.index(dist) in [0]:
            continue
        distList.append(dist.text)
    list_of_all_district.append(distList)


#writing lists to statelist.dat
with open(filename,"wb") as f:
    pickle.dump(stateList,f)
    pickle.dump(list_of_all_district,f)
'''
code used to verify data written to statelist.data

in this version it prints list_of_all_district[11]
k = []
with open(filename,"rb") as f:
    k = pickle.load(f)
    k = pickle.load(f)


print(k[11])


'''

driver.quit()#closing browser window