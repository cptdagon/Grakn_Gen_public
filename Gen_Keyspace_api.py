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

api.add_resource(ApiPing, '/ping')

if __name__ == '__main__':
   app.run(debug=True)
