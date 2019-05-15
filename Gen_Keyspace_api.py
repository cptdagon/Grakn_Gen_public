from flask import Flask, request #flask framework
from flask_restful import Resource, Api, reqparse #used to build restful apis using flask
from grakn.client import GraknClient #grakn framework
import subprocess #used to ping server
import json #used to build api output

app = Flask(__name__)
api = Api(app)

#######################
### server ping api ###
#######################

class ApiPing(Resource): #pings grakn server for status. 
    def get(self):
        out = subprocess.Popen(['./grakn', 'server', 'status', 'Server_status.txt'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT) #terminal call for ./grakn server status
        stdout,stderr = out.communicate()
        first = stdout.decode("utf-8").split('\n')[12] #fetches storage status
        second = stdout.decode("utf-8").split('\n')[13] #fetches server status
        return {"storage": first.split(': ')[1],"server":second.split(': ')[1]} #beautyfies output

#######################
### grakn match api ###
#######################

class dataFetch(Resource): #builds a basic data fetch and returns the list of ids for the data
    def get(self,thing,has = "", limit = 100):

        ### parameter formater ###

        split = has.split(',') #has string in format 'name="Jim",gender="male"'
        has = ""
        if split[0] != '':
            for hasquery in split:
                has = has + ',has '+hasquery.split('=')[0]+' '+hasquery.split('=')[1]

        ### data fetch ###

        jsonobject = json.dumps({"matched": thing})[:-1]+',"answers": [ '
        with GraknClient(uri="localhost:48555") as client:
            with client.session(keyspace="dev_test") as session:
                with session.transaction().read() as read_transaction:
                    match_iterator = read_transaction.query('match $t isa '+thing+' '+has+';get;limit '+str(limit)+';')
                    answers = match_iterator.collect_concepts()
                    for answer in answers:
                        jsonobject = jsonobject + json.dumps({"id":answer.id})[:-1]+',"attributes": [ '
                        attributes = answer.attributes()
                        for attribute in attributes:
                            jsonobject = jsonobject + json.dumps({"label":attribute.type().label(),"value":attribute.value()})+','
                        jsonobject = jsonobject[:-1]+']},'
                    jsonobject = jsonobject[:-1]+']}'
                    return json.loads(jsonobject)

######################
### api references ###
######################

api.add_resource(ApiPing, '/ping')
api.add_resource(dataFetch, '/fetch/<string:thing>', '/fetch/<string:thing>/<string:has>', '/fetch/<string:thing>/<int:limit>', '/fetch/<string:thing>/<string:has>/<int:limit>')

if __name__ == '__main__':
   app.run(debug=True)
