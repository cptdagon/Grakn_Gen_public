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

class builders():
    def entity_builder(entities):
        raise NotImplementedError()

    def attribute_builder(attributes):
        jsonobject = ""
        for attribute in attributes:
            jsonobject = jsonobject + json.dumps({"label":attribute.type().label(),"value":attribute.value()}, default = str)+','
        jsonobject = jsonobject[:-1]+'],'
        return jsonobject

    def role_builder(roles):
        jsonobject = ""
        for role in roles:
            jsonobject = jsonobject + json.dumps({"label":role.label()}, default = str)+','
        jsonobject = jsonobject[:-1]+'],'
        return jsonobject

    def key_builder(keys):
        jsonobject = ""
        for key in keys:
            jsonobject = jsonobject + json.dumps({"label":key.label()},default = str)+','
        jsonobject = jsonobject[:-1]+'],'
        return jsonobject

    def relation_builder(relations):
        raise NotImplementedError()


#######################
### grakn match api ###
#######################

class dataFetch(Resource): #builds a basic data fetch and returns the list of ids for the data
    def get(self,kspace,thing,has = "", limit = 100):

        Key = request.headers.get('Api-Key')
        print (Key)
        ### parameter formater ###
        split = has.split(',') #has string in format 'name="Jim",gender="male"'
        has = ""
        if split[0] != '':
            for hasquery in split:
                has = has + ',has '+hasquery.split('=')[0]+' '+hasquery.split('=')[1]
        thingName = thing.split('-')[0]
        thingType = thing.split('-')[1].lower()
        ### data fetch ###

        jsonobject = json.dumps({"matched": thingName, "matchedType": thingType})[:-1]+',"answers": [ '
        with GraknClient(uri="localhost:48555") as client:
            with client.session(keyspace=kspace) as session:
                with session.transaction().read() as read_transaction:
                    if thingType == "entity":
                        match_iterator = read_transaction.query('match $t isa '+thingName+' '+has+';get;limit '+str(limit)+';')
                        answers = match_iterator.collect_concepts()
                        for answer in answers:
                            #players = answer.role_players()attributes = answer.attributes()
                            #for player in players:
                            #    print(player.id)
                            jsonobject = jsonobject + json.dumps({"id":answer.id})[:-1]+',"contains":[{ "attributes": [ '
                            attributes = answer.attributes()
                            for attribute in attributes:
                                jsonobject = jsonobject + json.dumps({"label":attribute.type().label(),"value":attribute.value()}, default = str)+','
                            jsonobject = jsonobject[:-1]+'], "roles": [ '
                            roles = answer.roles()
                            for role in roles:
                                jsonobject = jsonobject + json.dumps({"label":role.label()}, default = str)+','
                            jsonobject = jsonobject[:-1]+']}]},'
                        jsonobject = jsonobject[:-1]+']}'
                        return json.loads(jsonobject)

                    elif thingType == "relation":
                        match_iterator = read_transaction.query('match $t($a,$b) isa '+thingName+' '+has+';get $t;limit '+str(limit)+';')
                        answers = match_iterator.collect_concepts()
                        for answer in answers:
                            players = answer.role_players()
                            for player in players:
                                print(player.id)
                            jsonobject = jsonobject + json.dumps({"id":answer.id})[:-1]+',"contains":[{ "attributes": [ '
                            attributes = answer.attributes()
                            for attribute in attributes:
                                jsonobject = jsonobject + json.dumps({"label":attribute.type().label(),"value":attribute.value()}, default = str)+','
                            jsonobject = jsonobject[:-1]+'], "roles": [ '
                            roles = answer.roles()
                            for role in roles:
                                jsonobject = jsonobject + json.dumps({"label":role.label()}, default = str)+','
                            jsonobject = jsonobject[:-1]+']}]},'
                        jsonobject = jsonobject[:-1]+']}'
                        return json.loads(jsonobject)

                    elif thingType == "attribute":
                        Flask.abort(501)
                    else:
                        Flask.abort(400)

######################
### api references ###
######################

api.add_resource(ApiPing, '/ping')
api.add_resource(dataFetch,
    '/match/<string:kspace>/<string:thing>',
    '/match/<string:kspace>/<string:thing>/<string:has>',
    '/match/<string:kspace>/<string:thing>/<int:limit>',
    '/match/<string:kspace>/<string:thing>/<string:has>/<int:limit>')

if __name__ == '__main__':
   app.run(debug=True)
