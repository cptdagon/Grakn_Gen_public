from flask import Flask, request #flask framework
from flask_restful import Resource, Api #used to build restful apis using flask
from grakn.client import GraknClient #grakn framework
import subprocess #used to ping server
import json #used to build api output

app = Flask(__name__)
api = Api(app)

class ApiPing(Resource): #pings grakn server for status. 
    def get(self):
        out = subprocess.Popen(['./grakn', 'server', 'status', 'Server_status.txt'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT) #terminal call for ./grakn server status
        stdout,stderr = out.communicate()
        first = stdout.decode("utf-8").split('\n')[12] #fetches storage status
        second = stdout.decode("utf-8").split('\n')[13] #fetches server status
        return {"storage": first.split(': ')[1],"server":second.split(': ')[1]} #beautyfies output

class dataFetch(Resource): #builds a basic data fetch and returns the list of ids for the data
    def get(self, thing):
        jsonobject = '{"answers": ['
        with GraknClient(uri="localhost:48555") as client: #grakn client local host port 
            with client.session(keyspace="dev_test") as session: #keyspace name
                with session.transaction().read() as read_transaction:
                    match_iterator = read_transaction.query('match $t isa '+thing+';get;') #dynamic object match to find data of type
                    answers = match_iterator.collect_concepts() 
                    for answer in answers:
                       jsonobject = jsonobject + json.dumps({"id":answer.id})+','
                    jsonobject = jsonobject[:-1]+']}'
                    return json.loads(jsonobject)

class apiTemp(Resource): #builds a basic data fetch and returns the list of ids $
    def get(self):
        jsonobject = json.dumps({"matched": "person"})[:-1]+',"answers": ['
        with GraknClient(uri="localhost:48555") as client:
            with client.session(keyspace="dev_test") as session:
                with session.transaction().read() as read_transaction:
                    match_iterator = read_transaction.query('match $t isa person;get;')
                    answers = match_iterator.collect_concepts()
                    for answer in answers:
                        jsonobject = jsonobject + json.dumps({"id":answer.id})[:-1]+',"attributes": ['
                        attributes = answer.attributes()
                        for attribute in attributes:
                            jsonobject = jsonobject + json.dumps({"label":attribute.type().label(),"value":attribute.value()})+','
                        jsonobject = jsonobject[:-1]+']},'
                    jsonobject = jsonobject[:-1]+']}'
                    return json.loads(jsonobject)

api.add_resource(ApiPing, '/ping')
api.add_resource(dataFetch, '/fetch/<string:thing>')
api.add_resource(apiTemp, '/')

if __name__ == '__main__':
   app.run(debug=True)
