from flask import Flask, render_template, flash, request, json
from wtforms import Form, validators, StringField
import requests
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement
from cassandra import ConsistencyLevel

# Initialising the app and the configuration
app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')
app.config.from_pyfile('config.py')

# Declaring the keyspace, connecting to correct Kubernetes cluster and to the keyspace.
KEYSPACE = 'wikiflask'
cluster = Cluster(['cassandra'])
session = cluster.connect(keyspace=KEYSPACE)

# When the application is started for the first time the exists.txt file is empty
start_file = open('exists.txt', 'r+')
if start_file.read() == "":
    session.execute("""DROP KEYSPACE IF EXISTS %s""" % KEYSPACE)
    session.execute(
        """CREATE KEYSPACE IF NOT EXISTS %s WITH REPLICATION = {'class' : 'SimpleStrategy', 'replication_factor' : 1}""" % KEYSPACE)
    session.execute(
        """CREATE TABLE ask(ask_query text, ask_result text, PRIMARY KEY(ask_query))""")
    start_file.write('started')
# Close the text file
start_file.close()

#Core REST API structure for Summary request
wiki_url_template = 'https://en.wikipedia.org/api/rest_v1/page/summary/{query}'

#HTML form class
class ReusableForm(Form):
    name = StringField('Name:', validators=[validators.required()])

# Main method both for GET and POST
@app.route("/", methods=['GET', 'POST'])
def askwiki():
    #Get the current state of the form
    form = ReusableForm(request.form)

    # Print potential errors
    print(form.errors)

    # On submitted - it proceeds only if there is content in the input field
    if form.validate():
        if request.method == 'POST':
            # Input from the form - converted to lower to avoid ambiguity and double entries to the DB
            name = request.form['name'].lower()
            # Now we check if the record exists in the DB before reaching to wikimedia API
            ask_cassandra_query = session.prepare("""SELECT ask_query FROM ask WHERE ask_query=?""")
            db_response = session.execute(ask_cassandra_query, [name])
            retrieved_query = str(db_response)
            # Checking if the record already exists in the database, if so print the summary associated with it.
            if name == retrieved_query.lower():
                ask_cassandra_summary = session.prepare("""SELECT ask_result FROM ask WHERE ask_query=?""")
                db_summary = session.execute(ask_cassandra_summary, [name])
                flash('RECORD EXISTS IN CASSANDRA: ' + str(db_summary))
            # Otherwise request the information from Wikimedia API
            else:
                query_url = wiki_url_template.format(query=name)
                resp = requests.get(query_url)
                if resp.ok:
                    result = resp.json()
                    json_data = json.dumps(result)
                    json_input = json.loads(json_data)
                    # Finding extract-summary in the JSON file we have parsed.
                    json_output = json_input['extract']
                    # Since it is new data we want to insert it into our table
                    write_record = SimpleStatement(
                        """INSERT INTO ask (ask_query, ask_result) VALUES(%s, %s)""",
                        consistency_level=ConsistencyLevel.ONE)
                    session.execute(write_record, (name, json_output))
                    flash('RECORD COMES FROM WIKIMEDIA API: ' + json_output)

                # If response was unsuccessful the user receives feedback.
                else:
                    flash('The search has failed: ' + resp.reason)
    # Each time page is refreshed
    else:
        flash('Please insert your query.')

    return render_template('form.html', form=form)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)

