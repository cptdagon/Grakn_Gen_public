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

#####################
### json builders ###
#####################

class builders():

    @classmethod
    def entity_builder(cls,entity): #builds a entity along with its associated attributes, roles, and keys
        jsonobject = json.dumps({"id":entity.id, "label":entity.type().label()})[:-1]+',"contains":[{ '
        #jsonobject = jsonobject + cls.attributes_builder(entity.attributes())
        #jsonobject = jsonobject + cls.roles_builder(entity.roles())
        #jsonobject = jsonobject + cls.keys_builder(entity.keys())
        jsonobject = jsonobject + ( cls.attributes_builder(entity.attributes()) + cls.roles_builder(entity.roles()) + cls.keys_builder(entity.keys()) )
        jsonobject = jsonobject[:-1]+'}]},'
        return jsonobject

    @classmethod
    def entities_builder(cls,entities): #builds a list of entities
        jsonobject = ""
        for entity in entities:
            jsonobject = jsonobject + cls.entity_builder(entity)
        jsonobject = jsonobject[:-1]
        return jsonobject

    @classmethod
    def attribute_builder(cls,attribute): #builds an attribute along with its owned attributes, roles, and keys
        jsonobject = json.dumps({"label":attribute.type().label(),"value":attribute.value()}, default = str)[:-1]+',"contains":[{ '
        jsonobject = jsonobject + cls.attributes_builder(attribute.attributes())
        jsonobject = jsonobject + cls.roles_builder(attribute.roles())[:-1]+'}]},'
        return jsonobject

    @classmethod
    def attributes_builder(cls,attributes): #builds a list of attributes
        jsonobject = '"attributes":[ '
        for attribute in attributes:
            jsonobject = jsonobject + cls.attribute_builder(attribute)
        jsonobject = jsonobject[:-1]+'],'
        return jsonobject

    @classmethod
    def role_builder(cls,role): #builds a role
        jsonobject = json.dumps({"label":role.label()}, default = str)+','
        return jsonobject

    @classmethod
    def roles_builder(cls,roles): #builds a list of roles
        jsonobject = '"roles":[ '
        for role in roles:
            jsonobject = jsonobject + cls.role_builder(role)
        jsonobject = jsonobject[:-1]+'],'
        return jsonobject

    @classmethod
    def key_builder(cls,key): #builds a key
        jsonobject = json.dumps({"label":key.label()},default = str)+','
        return jsonobject

    @classmethod
    def keys_builder(cls,keys): #builds a list of keys
        jsonobject = '"keys":[ '
        for key in keys:
            jsonobject = jsonobject + cls.key_builder(key)
        jsonobject = jsonobject[:-1]+'],'
        return jsonobject

    @classmethod
    def player_builder(cls,player):
        jsonobject = '{'
        if player.is_attribute():
            jsonobject = jsonobject + '"attribute":[{ ' + cls.attribute_builder(player)[:-1] + '}],"entity":[],"relation":[],'
            #jsonobject = jsonobject + cls.attribute_builder(player)
            #jsonobject = jsonobject[:-1] + '}],"entity":[],"relation":[],'
        elif player.is_entity():
            jsonobject = jsonobject + '"attribute":[],"entity":[ ' + cls.entity_builder(player)[:-1] + '],"relation":[]'
            #jsonobject = jsonobject + cls.entity_builder(player)
            #jsonobject = jsonobject[:-1] + '],"relation":[]'
        elif player.is_relation():
            jsonobject = jsonobject + '"attribtue":[],"entity":[],"relation":[ ' + cls.relation_builder(player)[:-1] + ']'
            #jsonobject = jsonobject + cls.relation_builder(player)
            #jsonobject = jsonobject[:-1] + ']'
        else:
            jsonobject = jsonobject + '"attribute":[],"entity":[],"relation":[]'
        jsonobject = jsonobject + '},'
        return jsonobject

    @classmethod
    def players_builder(cls,players):
        jsonobject = '"players":[ '
        for player in players:
            jsonobject = jsonobject + cls.player_builder(player)
        jsonobject = jsonobject[:-1] + '],'
        return jsonobject

    @classmethod
    def relation_builder(cls,relation): #builds a relation with its players, and owned attributes, roles, and keys
        jsonobject = json.dumps({"id":relation.id, "label":relation.type().label()})[:-1]+',"contains":[{ '
        #jsonobject = jsonobject + cls.players_builder(relation.role_players())
        #jsonobject = jsonobject + cls.attributes_builder(relation.attributes())
        #jsonobject = jsonobject + cls.roles_builder(relation.roles())
        #jsonobject = jsonobject + cls.keys_builder(relation.keys())
        jsonobject = jsonobject + ( cls.players_builder(relation.role_players()) + cls.attributes_builder(relation.attributes()) + cls.roles_builder(relation.roles()) + cls.keys_builder(relation.keys()) )
        jsonobject = jsonobject[:-1]+'}]},'
        return jsonobject

    @classmethod
    def relations_builder(cls,relations): #builds a list of relations
        jsonobject = ""
        for relation in relations:
            jsonobject = jsonobject + cls.relation_builder(relation)
        jsonobject = jsonobject[:-1]
        return jsonobject

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

class testapis(Resource):
    def get(self):
        jsonobject = json.dumps({"matched": "friendship", "matchedType": "relationship"})[:-1]+',"answers": [ '
        with GraknClient(uri="localhost:48555") as client:
            with client.session(keyspace="dev_test2") as session:
                with session.transaction().read() as read_transaction:
                    match_iterator = read_transaction.query('match $t isa friendship ;get;limit 1;')
                    answers = match_iterator.collect_concepts()
                    jsonobject = jsonobject + builders.relations_builder(answers)
                    jsonobject = jsonobject[:-1]+'}]}'
                    return json.loads(jsonobject)

######################
### api references ###
######################
api.add_resource(testapis, '/test')
api.add_resource(ApiPing, '/ping')
api.add_resource(dataFetch,
    '/match/<string:kspace>/<string:thing>',
    '/match/<string:kspace>/<string:thing>/<string:has>',
    '/match/<string:kspace>/<string:thing>/<int:limit>',
    '/match/<string:kspace>/<string:thing>/<string:has>/<int:limit>')

if __name__ == '__main__':
   app.run(debug=True)
