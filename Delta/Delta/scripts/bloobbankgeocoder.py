

"""
This script is used to generate geodb database


"""




import pymongo
from pymongo import MongoClient
from pymongo import collection
import geocoder
import time
import pickle
userDBclient = MongoClient("mongodb://connectstring")
dbclient = MongoClient("mongodb://conectstring")
db =dbclient["WholeBlood"]
stateList = []
stateListFileName = "statelist.dat"
with open(stateListFileName,"rb") as f:
    stateList = pickle.load(f)
geodb = userDBclient["geocodes"]
bing_map_key = "thisisnotbingkey"
for state in stateList:
    geocol = geodb[state]
    geocol.drop()


for state in stateList:
    col = db[state]
    for result in col.find():
        geodict = {}
        geodict["state"] = result["state"]
        geodict["district"]= result["district"]
        geodict["bb_categort"] = result["bb_category"]
        geodict["bb_address"] = result["bb_address"]
        geodict["bb_name"] = result["bb_name"]
        geodict["bb_contact"] = result["bb_contact"]
        geosearch = geocoder.bing(result['bb_address'],key=bing_map_key)
        try:
            geodict["coordinates"] = geosearch.json["raw"]["point"]["coordinates"]
            print(geodict)
            time.sleep(0.4)
            geocol = geodb[state]
            geocol.insert_one(geodict)
        except:
            print("error occured at")
            print(geodict)
            continue
