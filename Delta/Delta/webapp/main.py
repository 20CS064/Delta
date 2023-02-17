#version 1.23
#for flask app
from flask import Flask
import os
#mongodb client
from pymongo import MongoClient
from pymongo import collection
from flask import request,redirect
#for prasing data to json format for petite vue
from bson import json_util, ObjectId
import json
#for url formating
import urllib
#for reading statelist.dat and bcandbgtypelist.dat
import pickle
from flask import render_template

from operator import itemgetter
from flask import jsonify
#to measure distance betwenn cordinates
from geopy.distance import geodesic
import random
import string
#for email notifications
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread
import time
from datetime import datetime

#generates a random string of given length N
def randomstring(N):
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(N))

#reading stateList and list_of_all_district from statelist.dat using pickle
stateListFileName = "statelist.dat"
list_of_all_district = []
stateList = []


with open(stateListFileName,"rb") as f:
    stateList = pickle.load(f)
    list_of_all_district = pickle.load(f)
#reading bgTypelist and bcTypelist from bgandbctypes.dat using pickle
bgandbcListFilename = "bgandbctypes.dat"
bgTypelist = []
bcTypelist = []
with open(bgandbcListFilename,"rb") as f:
    bgTypelist = pickle.load(f)
    bcTypelist = pickle.load(f)

#to store login sessions
bb_logins = []
sessions = [{"email":"testbb@delta.tarang.ovh","ID":"aa"}]
requests_list = []

#mongodb connection string
userDBclient = MongoClient("mongodb://admin:raspbianraspberryraspberry@140.238.224.19:2700")
emaildb = userDBclient["bbaccounts"]
emailcol = emaildb["emailcol"]

dbclient = MongoClient("mongodb://admin:raspbianraspberryraspberry@140.238.224.19:2700")
#dictionary to be used if a entery doesent exist in mongodb for blood stock
no_result_dict = {}
for bg in bgTypelist:
    no_result_dict[bg+"_quantity"]=0




#the flask app
app = Flask(__name__)

#get api to send otp for bloodbank see documentation for more information

@app.route('/api/sendotpbb/<path:subpath>')
def sendotpbb(subpath):
    login_email = subpath
    #generate 128 char long string for url ids
    generated_id = randomstring(128)
    #generate 6  digit otp
    otp = ''.join(random.SystemRandom().choice(string.digits) for _ in range(6))
    #sending otp to user
    #creating email object
    message = MIMEMultipart("alternative")
    message["Subject"] = "OTP to login into detla dashboard"
    message["From"] = "notify@delta.tarang.ovh"
    message["To"] = login_email
    html_emailbody = """\
<html>
  <body>
   Use this otp to sign into your delta dashboad : <br>
    """+otp+"""<br>
    if it was not you simply ignore this email 
  </body>
</html>
"""
    part_email = MIMEText(html_emailbody, "html")
    message.attach(part_email)
    #loging into smtp server
    with smtplib.SMTP_SSL("box.tarang.ovh", 465) as server:
        server.login("notify@delta.tarang.ovh","raspberry")
        server.sendmail(
            "notify@delta.tarang.ovh", message["To"], message.as_string()
        )
    print("Email sent")
    #append session and otp details to bb_logins to be used later by login page post form handler
    login_dict = {"email":login_email,"ID":generated_id,"OTP":otp}
    bb_logins.append(login_dict)
    return "Email sent"
    
#dashboard page for bloodbanks
@app.route("/dashboard/<path:subpath>")
def dashboard(subpath):
    for id in sessions:
        #if there exists id same as that present in url in sessions list
        if id["ID"] == subpath:
            #get getails about user from emailcol
            details  = emailcol.find_one({"email":id["email"]})
            list_to_be_rendered = []
            #get current blood stock for the bloodbank
            for bc in bcTypelist:
                info_db = dbclient[bc.replace(' ','')]
                statecol = info_db[details["state"]]
                results = statecol.find({"bb_name":details["bb_name"],"bb_address":details["bb_address"]})
            
                result_list = list(results)
                #if entery doesnt exist use no_result_dict instead
                if len(result_list)==0:
                    result_list.append(no_result_dict)
                list_to_be_rendered.append(result_list[0])
                
                
            
            
            
            #render template based on data just gathered

            return render_template("stockupdate.html",bcTypelist=bcTypelist,bgTypelist=bgTypelist,uniqueID=id["ID"],stockdict = list_to_be_rendered,bb_name=details["bb_name"])
    
    #if id doesnt exist in sesions show this error
    return "Requested page could not be found"
#bloodbank dashboard page post form handler
@app.route("/dashboard/post/<path:subpath>",methods=['GET', 'POST'])
def posthandler(subpath):
    #check if its POST method
    if request.method == 'POST':
        
        subpaths = subpath.split("/")
        for bc in bcTypelist:
            #checking which bcType the form was submitted for
            if bc.replace(' ','') == subpaths[0]:
                #check if the id is valid
                for ID in sessions:
                    if ID["ID"] == subpaths[1]:
                        #get details about bloodbank
                        details  = emailcol.find_one({"email":ID["email"]})
                        
                        db_to_update = dbclient[bc.replace(' ','')]
                        col_to_update = db_to_update[details["state"]]
                        #get other details like contact address etc from whole blood database
                        whole_blood_db = dbclient["WholeBlood"]
                        whole_col = whole_blood_db[details["state"]]
                        reference_dict = whole_col.find_one({"bb_name":details["bb_name"],"bb_address":details["bb_address"]})
                        for bg in bgTypelist:
                            try:#if the quantity is not a valid int update stock to 0
                                reference_dict[bg+"_quantity"] = int(request.form[bg])
                                if reference_dict[bg+'_quantity'] == 0:
                                    reference_dict[bg+"_is_available"] = False
                                else:
                                    reference_dict[bg+"_is_available"] = True
                            except:
                                reference_dict[bg+'_quantity'] = 0
                                reference_dict[bg+"_is_available"] = False
                        now = datetime.now()
                        reference_dict["lastupdated"]= now.strftime("%H:%M:%S")
                        
                        reference_dict.pop('_id')
                        #insert the dictionary in mongodb
                        col_to_update.find_one_and_replace({"bb_name":reference_dict["bb_name"],"bb_address":reference_dict["bb_address"]},reference_dict,upsert=True)
                       #redirect user back to dashboard
                        return redirect("http://127.0.0.1:5000/dashboard/"+subpaths[1])
                            
                                

                        

    #if it is not a POST request return 404
    return "404" 
#login page for bloodbank
@app.route('/login.html',methods=['GET', 'POST'])
def login():
    #post form handler
    if request.method == "POST":
        user_email = request.form["email"]
        user_otp = request.form["otp"]
        for bbuser in bb_logins:
            #validate email and otp match in bb_logins and create a session
            if bbuser["email"] == user_email and bbuser["OTP"]== user_otp and len(list(emailcol.find({"email":bbuser["email"]}))):
                sessions.append({"ID":bbuser["ID"],"email":bbuser["email"]})
                #if everything is valid redirect to dashboard with generated ID
                return redirect("http://127.0.0.1:5000/dashboard/"+bbuser["ID"])
        return "please enter a valid email or otp"
    else:#if its not a post request render login page
        return render_template("login.html",statelist = stateList,distlist = list_of_all_district,bclist = bcTypelist,bglist = bgTypelist)





#dontationrequest page for bloodbanks
@app.route("/donationrequest/<path:subpath>")
def donationrequest(subpath):
    for session in sessions:
        if session["ID"] == subpath:
            return render_template("bb_donor_request.html",bgTypelist=bgTypelist,uniqueID=subpath) 
    return "unauthorized"


#function that notifys user if a nearby bloodbank needs blood
def bb_notify(bb_details):
    campUserdb = userDBclient["campemaildb"]
    usercols = campUserdb["maillist"]
    #get list of registered user from mongodb
    mailList = list(usercols.find())
    for mailSub in mailList:
        #if notify distance is notify distance is greater than distance between user and blood bank  and user is of required bloodgroup send him an email
        if mailSub["notify_distance"] > geodesic(bb_details["coordinates"],mailSub["coordinates"]).km and mailSub["bloodgroup"]==bb_details["required_bg"]:
            message = MIMEMultipart("alternative")
            message["Subject"] = "A blood bank in your area needs blood of your blood group"
            message["From"] = "notify@delta.tarang.ovh"
            message["To"] = mailSub["email"]
            html_emailbody = """\
<html>
  <body>
    A bloodbank in your area requires """+bb_details["required_bg"]+""" blood <br>
    If you can donate blood to them today, please contact them<br>
    Blood Bank details : <br>"""+ bb_details["bb_name"]+"""<br>"""+bb_details["bb_address"]+"""
    <br>"""+bb_details["bb_contact"]+"""<br> blood group required """+ bb_details["required_bg"]+"""
    <br><a href=" """+bb_details["map_url"]+ """ ">click here to view it on Google map</a> 
    <br> Please only meet at bloodbank or hospital and report us if anything seems suspious

     <br><br>    <br><br>
    Want to stop recieving emails like this?<a href="http://delta.tarang.uk:5000/unsubscribe/"""+mailSub["unsub"]+""" ">Click here to unsubscribe</a>
    
  </body>
</html>
"""
                                                
                        
                        
                        
                        
                        
                        
            part_email = MIMEText(html_emailbody, "html")
            message.attach(part_email)
            #sending email to user 
            with smtplib.SMTP_SSL("box.tarang.ovh", 465) as server:
                server.login("notify@delta.tarang.ovh","raspberry")
                server.sendmail(
                    "notify@delta.tarang.ovh", message["To"], message.as_string()
                )
            print("Email sent")




#bloodbank donation request api
#get api provides bloodbanks coordinates and requiredbloodgroup and creates a new thread to send emails
@app.route("/api/drequest/<path:subpath>")
def drequest(subpath):
    subpaths = subpath.split('/')
    for session in sessions:
        #if the session is valid
        if subpaths[0]==session["ID"]:
            #get details about user from session
            geodb = userDBclient["geocodes"]
            detail = emailcol.find_one({'email':session["email"]})
            geocols = geodb[detail["state"]]
            #generating google maps link
            bb_details = geocols.find_one({"bb_name":detail["bb_name"],"bb_address":detail["bb_address"]})
            bb_details["map_url"]="https://www.google.com/maps/search/?api=1&query="+bb_details["bb_address"]
            bb_details["coordinates"]=[subpaths[1],subpaths[2]]
            bb_details["required_bg"]= subpaths[3]
            #create thread that runs bb_notify function with details or request
            thread = Thread(target=bb_notify, args=(bb_details,))
            thread.daemon = True
            thread.start()
            print("sending notification as requested by bloodbanks")
            return "Sending notification "

    


#index pages
@app.route("/index.html")
def index_pag():
    return render_template("index.html")

@app.route("/")
def index_page():
    return render_template("index.html")
#ngo details page
@app.route("/ngo-details.html")
def ngo():
    return render_template("ngo-details.html")



#various apis for more information see api documentation

@app.route('/api/nearby/<path:subpath>')
def nearby_api(subpath):
    #returns bloodbank i a district
    subpaths = subpath.split("/")
    required_state = subpaths[0]
    required_district = subpaths[1]
    
    geodb = userDBclient["geocodes"]
    geocol = geodb[required_state]
    #search bloodbanks in the database
    re = geocol.find({"district":required_district})
    result = list(re)
    for r in result:
        #append google maps link to all the resuts
        r["map_url"]="https://www.google.com/maps/search/?api=1&query="+r["bb_address"]
    return jsonify(results = json.loads(json_util.dumps(result)))

@app.route('/api/camp/1/<path:subpath>')
def getcampschedule(subpath):
    #returns bloodcamps in a district
    subpaths = subpath.split("/")
    required_state = subpaths[0]
    
    #camp db
    campdb = dbclient["camps"]
    campcols = campdb["campcols"]
    if len(subpaths) == 2:
        required_district = subpaths[1]
        #search for bloodcamp in particular district in database
        r = campcols.find({"state":required_state,"district":required_district})
        result = []
        for re in r:
            result.append(re)
            #append google mapurl 
            result[-1]["map_url"]="https://www.google.com/maps/search/?api=1&query="+re["camp_address"]

    else:
        r = campcols.find({"state":required_state})
        result = []
        for re in r:
            result.append(re)
            result[-1]["map_url"]="https://www.google.com/maps/search/?api=1&query="+re["camp_address"]
            #return json object
    return jsonify(results = json.loads(json_util.dumps(result)))   

    
@app.route('/api/camp/2/all')
def getAllCamps():
    #return all the camps
    campdb = dbclient["camps"]
    campcols = campdb["campcols"]
    #fetch all the camps in database
    result = campcols.find()
    return jsonify(results = json.loads(json_util.dumps(result)))     

@app.route('/api/camp/3/<path:subpath>')
def findNearestCamp(subpath):
    #returns list of bloodcams sorted by distancs
    subpaths = subpath.split("/")
    coordinates = [subpaths[0],subpaths[1]]
    campdb = dbclient["camps"]
    campcols = campdb["campcols"]
    final_result = []
    #get all the camps
    result = campcols.find()
    for r in result:
        final_result.append(r)
        distance = geodesic(r["coordinates"],coordinates).km
        final_result[final_result.index(r)]["distance"]=distance
    #sort by distance
    sorted_list = sorted(final_result, key=itemgetter('distance')) 
    for item in sorted_list:
        item["map_url"]="https://www.google.com/maps/search/?api=1&query="+item["camp_address"]
    return jsonify(results = json.loads(json_util.dumps(sorted_list)))  

    

@app.route("/api/adduser/<path:subpath>")
def adduser(subpath):
    subpaths = subpath.split("/")
    email_address = subpaths[0]
    user_latitude = subpaths[1]
    user_longitude = subpaths[2]
    user_notify_distance = 50
    user_blood_group = subpaths[3]
    unsubscribe_string = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
    sub_dict = {"email":email_address,"coordinates":[user_latitude,user_longitude],"unsub":unsubscribe_string,"bloodgroup":user_blood_group,"notify_distance":user_notify_distance}
    print(sub_dict)
    campUserdb = userDBclient["campemaildb"]
    usercols = campUserdb["maillist"]
    usercols.insert_one(sub_dict)
    return "user added"

#function used to send notification to user
def sendotp(subpaths,otp):
    message = MIMEMultipart("alternative")
    message["Subject"] = "OTP to confirm maillist subscription"
    message["From"] = "notify@delta.tarang.ovh"
    message["To"] = subpaths[0]
    html_emailbody = """\
<html>
  <body>
    Someone used this email address to signup as a voluntary donor,<br>
    if it was you use OTP code : <br>
    """+otp+"""<br>
    if it was not you simply ignore this email and your subscription
    will not be confirmed
  </body>
</html>
"""
                                                
                        
                        
                        
                        
                        
                        
    part_email = MIMEText(html_emailbody, "html")
    message.attach(part_email)
    
    with smtplib.SMTP_SSL("box.tarang.ovh", 465) as server:
        server.login("notify@delta.tarang.ovh","raspberry")
        server.sendmail(
            "notify@delta.tarang.ovh", message["To"], message.as_string()
        )
    print("Email sent")
    
@app.route("/api/otp/<path:subpath>")
def returnotp(subpath):
    subpaths = subpath.split("/")
    otp =  ''.join(random.SystemRandom().choice(string.digits) for _ in range(6))
    thread = Thread(target=sendotp, args=(subpaths,otp))
    thread.daemon = True
    thread.start()
    return otp

    



@app.route('/api/location/<path:subpath>')
def nearbylocation_api(subpath):
    print(subpath)
    subpaths = subpath.split("/")
    required_state = subpaths[0]
    required_district = subpaths[1]
    coordinates = [subpaths[2],subpaths[3]]
    
    
    geodb = userDBclient["geocodes"]
    geocol = geodb[required_state]
    final_result = []
    result = geocol.find({"district":required_district})
    for r in result:
        final_result.append(r)
        distance = geodesic(r["coordinates"],coordinates).km
        final_result[final_result.index(r)]["distance"]=distance


    sorted_list = sorted(final_result, key=itemgetter('distance'))
    for s in sorted_list:
        s["map_url"]="https://www.google.com/maps/search/?api=1&query="+s["bb_address"] 
    return jsonify(results = json.loads(json_util.dumps(sorted_list)))    

    



@app.route('/api/stock/<path:subpath>')
def stock_api(subpath):
   #getparamenters from th subpath
    subpaths = subpath.split("/")
    required_bctype = subpaths[0]
    required_state = subpaths[1]
    required_district = subpaths[2]
    
    required_bgtype = subpaths[3]
    for bctype in bcTypelist:
        if(urllib.parse.quote_plus(bctype)==required_bctype) or bctype==required_bctype:
            db = dbclient[bctype.replace(" ","")]
            break
        
    for state in stateList:
        
        if(state==required_state.replace("+"," ")):
           
            collection = db[state.replace(" ","")]
            break
           
    for district in list_of_all_district[stateList.index(state)]:
        
        if(district==required_district.replace("+"," ")):
            district_to_search = district
            break
            
    bg_index = bgTypelist.index(required_bgtype)


            
       
        
    #search for stock in database

    re = collection.find({"district":district_to_search,bgTypelist[bg_index]+"_is_available":True})
    result = list(re)
    for r in result:
        r["map_url"]="https://www.google.com/maps/search/?api=1&query="+r["bb_address"] 
    
    return jsonify(results = json.loads(json_util.dumps(result)))
#services
# all the service pages

@app.route("/service.html")
def service():
    return render_template("service.html")

#redner camp schedule page
@app.route("/camp_schedule.html")
def campschedule():
    return render_template("camp_schedule.html",statelist = stateList,distlist = list_of_all_district)
#render blood-stock page
@app.route("/blood-stock.html")
def bloodstock():
    return render_template("blood-stock.html",statelist = stateList,distlist = list_of_all_district,bclist = bcTypelist,bglist = bgTypelist)
#render nearby bloodbank page
@app.route("/near-by-blood.html")
def near_by_bb():
    return render_template("near-by-blood.html",statelist = stateList,distlist = list_of_all_district,bclist = bcTypelist,bglist = bgTypelist)

def send_donor_requests(form_dict):
    campUserdb = userDBclient["campemaildb"]
    usercols = campUserdb["maillist"]
    list_of_users_email_sent = []
    #get list of registered user from mongodb
    mailList = list(usercols.find())
    for mailSub in mailList:
        #if notify distance is notify distance is greater than distance between user and blood bank  and user is of required bloodgroup send him an email
        if mailSub["notify_distance"] > geodesic([form_dict["lat"],form_dict["longitude"]],mailSub["coordinates"]).km and mailSub["bloodgroup"]==form_dict["blood-group"]:
            list_of_users_email_sent.append(mailSub["email"])
            message = MIMEMultipart("alternative")
            message["Subject"] = "Someone in your area needs blood"
            message["From"] = "notify@delta.tarang.ovh"
            message["To"] = mailSub["email"]
            html_emailbody = """\
                <html><body>Someone in your area needs blood of type """+form_dict["blood-group"]+"""
            <br>If you can donate blood or know someone with """+form_dict["blood-group"]+""" who can donate blood to the person in need,
            <br>Contact the person in need with given contact details <br>
            Name : """+form_dict["name"]+"""<br>
            Contact number : """+form_dict["phone"]+"""<br>
            Email : """+form_dict["email"]+"""<br>

            <br><br><br>
            if you face are unable to contact the said person contact us at : support@delta.tarang.ovh
            <br> Beware , only meet an unknown person at a bloodbank or a hospital report any thing suspicious to us,Stay safe
          <br><br>
            Want to stop recieving emails like this?<a href="http://delta.tarang.uk:5000/unsubscribe/"""+mailSub["unsub"]+""" ">Click here to unsubscribe</a>
    
  </body>
</html>
    
"""        
            part_email = MIMEText(html_emailbody, "html")
            message.attach(part_email)
            #sending email to user 
            with smtplib.SMTP_SSL("box.tarang.ovh", 465) as server:
                server.login("notify@delta.tarang.ovh","raspberry")
                server.sendmail(
                    "notify@delta.tarang.ovh", message["To"], message.as_string()
                )
            print("Email sent")
    requestdb = userDBclient["donorRequests"]
    requestsCol = requestdb["requests"]
    form_dict["email_sent_to"] = list_of_users_email_sent
    requestsCol.insert_one(form_dict)
    print("Email to all users sent")





#render donor request page
@app.route('/donar_request.html',methods=["GET","POST"])
def donorrequest():
    if request.method == "POST":
        #print(request.form)
        form_dict = request.form.to_dict()
        #print(form_dict)
        if form_dict["lat"]=="":
            return "location is required please click detect my loaction button"
        #print(request.files)
        file_dict = request.files.to_dict()
        #print(file_dict)
        form_dict["request_id"] = randomstring(10)
        dirname = os.path.dirname(__file__)
        filename1 = os.path.join(dirname, 'uploaded',form_dict["request_id"]+"."+file_dict["file1"].filename.split(".")[-1])
        file_dict["file1"].save(filename1)
        #filename1 = randomstring(10) + "."+fileExtension
        form_dict["filename"]=form_dict["request_id"]+"."+file_dict["file1"].filename.split(".")[-1]
        thread = Thread(target=send_donor_requests, args=(form_dict,))
        thread.daemon = True
        thread.start()
        print("Sending email notifications to users")
        
       
        
        return render_template("sendingnotification.html")
    return render_template("donar_request.html",statelist = stateList,distlist = list_of_all_district,bclist = bcTypelist,bgTypelist = bgTypelist)





#render maillist bage
@app.route("/maillist")
def mailist():
    return render_template("maillist.html",statelist = stateList,distlist = list_of_all_district,bclist = bcTypelist,bglist = bgTypelist)

@app.route("/about-us.html")
def aboutus():
    return render_template("about-us.html")    

@app.route("/thankyou")
def thankyou():
    return render_template("thankyou.html" , bcTypelist=bcTypelist)


#the unsubscribe page deletes users data on http request to unsubscribe string
@app.route("/unsubscribe/<path:subpath>")
def unsubscribe(subpath):
    campUserdb = dbclient["campemaildb"]
    usercols = campUserdb["maillist"]
    usercols.delete_one({"unsub":subpath})
    return "Unsubscription Confirmed,You will not recieve an email from us ever again"



#run the flask app
app.run(host='0.0.0.0')