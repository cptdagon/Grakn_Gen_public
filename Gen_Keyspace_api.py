from flask import Flask, request
from flask_restful import Resource, Api
from grakn.client import GraknClient
import subprocess

app = Flask(__name__)
api = Api(app)

class ApiPing(Resource):
    def get(self):
        out = subprocess.Popen(['./grakn', 'server', 'status', 'Server_status.txt'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        stdout,stderr = out.communicate()
        first = stdout.decode("utf-8").split('\n')[12]
        second = stdout.decode("utf-8").split('\n')[13]
        return {"storage": first.split(': ')[1],"server":second.split(': ')[1]}

class dataFetch(Resource):
    def get(self):
        jsonobject = dict()
        with GraknClient(uri="localhost:48555") as client:
            with client.session(keyspace="dev_test") as session:
                with session.transaction().read() as read_transaction:
                    match_iterator = read_transaction.query('match $p isa person;get;')
                    answers = match_iterator.collect_concepts()
                    for answer in answers:
                       jsonobject["id"] = answer.id
                    return {"answers": [ jsonobject ]}

api.add_resource(ApiPing, '/ping')
api.add_resource(dataFetch, '/fetchpeople')

if __name__ == '__main__':
   app.run(debug=True)

