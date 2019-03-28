from flask import Flask, render_template, flash, request, json
from wtforms import Form, validators, StringField
import requests
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement
from cassandra import ConsistencyLevel


KEYSPACE = "wikiflask"

app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')
app.config.from_pyfile('config.py')


cluster = Cluster(['cassandra'])
session = cluster.connect()
session.execute("DROP KEYSPACE IF EXISTS %s" % KEYSPACE)    # MIGHT NOT BE NEEDED?
session.execute(
    "CREATE KEYSPACE IF NOT EXISTS %s WITH REPLICATION = {'class' : 'SimpleStrategy', 'replication_factor' : 1}" % KEYSPACE)
session = cluster.connect(keyspace=KEYSPACE)

session.execute(
"CREATE TABLE ask(ask_query text, ask_result text, PRIMARY KEY(ask_query))")



#Core REST API structure for Summary request
wiki_url_template = 'https://en.wikipedia.org/api/rest_v1/page/summary/{query}'

#HTML form class
class ReusableForm(Form):
    name = StringField('Name:', validators=[validators.required()])

# main method both for GET and POST
@app.route("/", methods=['GET', 'POST'])
def askwiki():
    #get the current state of the form
    form = ReusableForm(request.form)

    # any errors
    print(form.errors)
    #on submitted - it proceeds only if there is content in the input field

    if form.validate():
        if request.method == 'POST':
            # input from the form - converted to lower to avoid ambiguity and double entries to the DB
            name = request.form['name'].lower()
            #print(name)
            # now we check if the record exists in the DB before reaching to wikimedia API

            counter = session.execute("SELECT count(*) FROM TABLE WHERE ask_query = name")
            # checking if the record exists in the database
            if counter > 0:
                repeated = session.execute("SELECT ask_result FROM ask WHERE ask_query=name")
                flash('RECORD EXISTS IN CASSANDRA: ' + repeated)
            else:
                query_url = wiki_url_template.format(query=name)
                resp = requests.get(query_url)
                if resp.ok:
                    result = resp.json()
                    json_data = json.dumps(result)
                    json_input = json.loads(json_data)
                    # Finding extract-summary in the JSON file we have parsed.
                    json_output = json_input['extract']

                    # inserting new data into the table
                    query = SimpleStatement(
                    "INSERT INTO ask (ask_query, ask_result) VALUES (name, json_output)",
                        consistency_level=ConsistencyLevel.ONE)
                    session.execute(query)
                    flash('RECORD COMES FROM WIKIMEDIA API: ' + json_output)

                # If response was unsuccessful the user receives feedback.
                else:
                    flash('The search has failed: ' + resp.reason)

    else:
        flash('Please insert your query.')

    return render_template('form.html', form=form)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)


