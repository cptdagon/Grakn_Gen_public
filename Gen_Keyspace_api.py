from flask import Flask, abort, request #flask framework
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

    #### builds entity json ####
    @classmethod
    def entity_builder(cls,entity):
        jsonobject = json.dumps({"id":entity.id, "label":entity.type().label()})[:-1]+',"contains":[{ '
        jsonobject = jsonobject + ( cls.attributes_builder(entity.attributes()) + cls.roles_builder(entity.roles()) + cls.keys_builder(entity.keys()) )
        jsonobject = jsonobject[:-1]+'}]},'
        return jsonobject
    #### builds a list of entity json ####
    @classmethod
    def entities_builder(cls,entities):
        jsonobject = ""
        for entity in entities:
            jsonobject = jsonobject + cls.entity_builder(entity)
        jsonobject = jsonobject[:-1]
        return jsonobject

    #### builds attribute json ####
    @classmethod
    def attribute_builder(cls,attribute):
        jsonobject = json.dumps({"label":attribute.type().label(),"value":attribute.value()}, default = str)[:-1]+',"contains":[{ '
        jsonobject = jsonobject + cls.attributes_builder(attribute.attributes())
        jsonobject = jsonobject + cls.roles_builder(attribute.roles())[:-1]+'}]},'
        return jsonobject

    #### builds a list of attribute json ####
    @classmethod
    def attributes_builder(cls,attributes):
        jsonobject = '"attributes":[ '
        for attribute in attributes:
            jsonobject = jsonobject + cls.attribute_builder(attribute)
        jsonobject = jsonobject[:-1]+'],'
        return jsonobject

    #### builds role json ####
    @classmethod
    def role_builder(cls,role):
        jsonobject = json.dumps({"label":role.label()}, default = str)+','
        return jsonobject

    #### builds a list of role json ####
    @classmethod
    def roles_builder(cls,roles):
        jsonobject = '"roles":[ '
        for role in roles:
            jsonobject = jsonobject + cls.role_builder(role)
        jsonobject = jsonobject[:-1]+'],'
        return jsonobject

    #### builds key json ####
    @classmethod
    def key_builder(cls,key):
        jsonobject = json.dumps({"label":key.label()},default = str)+','
        return jsonobject

    #### builds a list of key json ####
    @classmethod
    def keys_builder(cls,keys):
        jsonobject = '"keys":[ '
        for key in keys:
            jsonobject = jsonobject + cls.key_builder(key)
        jsonobject = jsonobject[:-1]+'],'
        return jsonobject

    #### builds player json ####
    @classmethod
    def player_builder(cls,player):
        jsonobject = '{'
        if player.is_attribute():
            jsonobject = jsonobject + '"attribute":[{ ' + cls.attribute_builder(player)[:-1] + '}],"entity":[],"relation":[],'
        elif player.is_entity():
            jsonobject = jsonobject + '"attribute":[],"entity":[ ' + cls.entity_builder(player)[:-1] + '],"relation":[]'
        elif player.is_relation():
            jsonobject = jsonobject + '"attribtue":[],"entity":[],"relation":[ ' + cls.relation_builder(player)[:-1] + ']'
        else:
            jsonobject = jsonobject + '"attribute":[],"entity":[],"relation":[]'
        jsonobject = jsonobject + '},'
        return jsonobject

    #### builds a list of player json ####
    @classmethod
    def players_builder(cls,players):
        jsonobject = '"players":[ '
        for player in players:
            jsonobject = jsonobject + cls.player_builder(player)
        jsonobject = jsonobject[:-1] + '],'
        return jsonobject

    #### builds relation json ####
    @classmethod
    def relation_builder(cls,relation):
        jsonobject = json.dumps({"id":relation.id, "label":relation.type().label()})[:-1]+',"contains":[{ '
        jsonobject = jsonobject + ( cls.players_builder(relation.role_players()) + cls.attributes_builder(relation.attributes()) + cls.roles_builder(relation.roles()) + cls.keys_builder(relation.keys()) )
        jsonobject = jsonobject[:-1]+'}]},'
        return jsonobject

    #### builds a list of relation json ####
    @classmethod
    def relations_builder(cls,relations):
        jsonobject = ""
        for relation in relations:
            jsonobject = jsonobject + cls.relation_builder(relation)
        jsonobject = jsonobject[:-1]
        return jsonobject

    #### determines how to behave based on the contents of the results fetched from grakn ####
    @classmethod
    def objectSwitch(cls,answers):
        a = False
        e = False
        r = False
        jsonobject = ""
        #### determine the contents of the answers list ####
        for answer in answers:
            if answer.is_entity():
                e = True
            elif answer.is_attribute():
                a = True
            elif answer.is_relation():
                r = True
            else:
                #### this shouldn't execute ####
                abort(500, "you shouldn't be here, leave. now.")
        #### test results ####
        if (a & (not (e | r))): # <=invalid syntax at ':'
            jsonobject = jsonobject + '{' +builders.attributes_builder(answers)
        elif (e and (not (a or r))):
            jsonobject = jsonobject + builders.entities_builder(answers)
        elif (r and (not (a or e))):
            jsonobject = jsonobject + builders.relations_builder(answers)
        else:
            #### hits this if more than one type is found in the list of answers ####
            #### typicaly occurs when a get $a, $b; term is used.
            abort(500, "well this is rather awkward... :| ")
        return jsonobject

#########################
#### grakn match api ####
#########################

class genApiFetch(Resource):  #### basic fetch request ####
    def get(self,
            kspace,       #### mandatory #### keyspace name ####
            thing,        #### mandatory #### thing to search for => format thing type = thing name => e.g: 'attribute=name' => match $t isa name ####
            has = " ",    #### not mandatory #### search parameters to either filter or fetch extra data from the database ####
                                             #### parameter name => parameter value  => e.g: 'name="Jim"' ####
                                             #### parametre name => parameter variable => e.g: 'name=$n' ####
                                             #### multiple values are comma seperated and types of values can be mixed => e.g: 'name=$n,eyeColor="blue"' ####
            get = "$t",    #### not mandatory #### specify variables to fetch data from => e.g: '$t,$n' ####
            limit = 100): #### not mandatory #### fetch quantity limit => used to improve response time of api ####
        #### parameters ####
        split = has.split(',')
        has = ""
        if split[0] != ' ':
            for hasquery in split:
                has = has + ',has '+hasquery.split('=')[0]+' '+hasquery.split('=')[1]
        thingName = thing.split('=')[1]
        thingType = thing.split('=')[0].lower()
        #### data fetch ####
        jsonobject = json.dumps({"matchedName": thingName, "matchedType": thingType})[:-1]+', "answers":[ '
        with GraknClient(uri="localhost:48555") as client:
            with client.session(keyspace=kspace) as session:
                with session.transaction().read() as read_transaction:
                    match_iterator = read_transaction.query('match $t isa '+thingName+' '+has+';get '+get+';limit '+str(limit)+';')
                    answers = match_iterator.collect_concepts()
                    jsonobject = jsonobject + builders.objectSwitch(answers)
                    jsonobject = jsonobject[:-1]+'}]}'
                    return json.loads(jsonobject) # json.laods

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

########################
#### api references ####
########################

api.add_resource(genApiFetch,
    '/fetch/<string:kspace>/<string:thing>',                                        #### http://127.0.0.1:5000/fetch/<keyspace_name>/<thingtype=thingname>
    '/fetch/<string:kspace>/<string:thing>/<string:has>',                           #### http://127.0.0.1:5000/fetch/<keyspace_name>/<thingtype=thingname>/<parametername=parametervalue>
    '/fetch/<string:kspace>/<string:thing>/<int:limit>',                            #### http://127.0.0.1:5000/fetch/<keyspace_name>/<thingtype=thingname>/<limitvalue>
    '/fetch/<string:kspace>/<string:thing>/<string:get>',                           #### http://127.0.0.1:5000/fetch/<keyspace_name>/<thingtype=thingname>/<getvariables>
    '/fetch/<string:kspace>/<string:thing>/<string:has>/<string:get>',              #### http://127.0.0.1:5000/fetch/<keyspace_name>/<thingtype=thingname>/<parametername=parametervalue>/<getvariables>
    '/fetch/<string:kspace>/<string:thing>/<string:has>/<int:limit>',               #### http://127.0.0.1:5000/fetch/<keyspace_name>/<thingtype=thingname>/<parametername=parametervalue>/<limitvalue>
    '/fetch/<string:kspace>/<string:thing>/<string:has>/<string:get>/<int:limit>',) #### http://127.0.0.1:5000/fetch/<keyspace_name>/<thingtype=thingname>/<parametername=parametervalue>/<getvariable>/<limitvalue>

api.add_resource(testapis, '/test') #### http://127.0.0.1:5000/test

api.add_resource(ApiPing, '/ping') #### http://127.0.0.1:5000/ping

if __name__ == '__main__':
   app.run(debug=True)
