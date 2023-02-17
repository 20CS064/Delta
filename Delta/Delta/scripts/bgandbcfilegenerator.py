#this script is used to create "bgandbctypes.dat"
import pickle
#libraries required for webscraping
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import Select   

import time #for time.speel()
list_of_components = []
list_of_bloodgroups = []
url = "https://www.eraktkosh.in/BLDAHIMS/bloodbank/stockAvailability.cnt" #url to be scraped
filename = "bgandbctypes.dat" 
options = Options()
options.headless = False  #wether to launch firefox in headless mode or not
driver = webdriver.Firefox(options = options)

driver.get(url)
time.sleep(10)
bloodGroupSelector = Select(driver.find_element_by_id("bgType"))
bgOptions = bloodGroupSelector.options
for bgOption in bgOptions:
    if bgOptions.index(bgOption) in [0,11]:
        continue
    list_of_bloodgroups.append(bgOption.text)
        
bCSelector = Select(driver.find_element_by_id("bcType"))
bCOptions = bCSelector.options

for option in bCOptions:
    if bCOptions.index(option) == 0:
        continue
    list_of_components.append(option.text)

with open(filename,"wb") as f:
    pickle.dump(list_of_bloodgroups,f)
    pickle.dump(list_of_components,f)        

driver.quit()