from io import StringIO
from flask import Flask, render_template, request, make_response
from flask.wrappers import Response
from flask_sqlalchemy import SQLAlchemy
from pandas.core.frame import DataFrame
import pandas as pd
from werkzeug.utils import send_file
import numpy as np
import sqlite3  # Import sqlite3 for SQLite operations

app = Flask(__name__)
# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'  # Change to your SQLite DB path
SQLAlchemy(app)

def load_data_from_sql_database_into_dataframe():
    # Connect to SQLite database
    conn = sqlite3.connect('mydatabase.db')  # Change to your SQLite DB path
    mycursor = conn.cursor()
    mycursor.execute("SELECT * from selskab;")
    df_db = DataFrame(mycursor.fetchall(), columns=['type', 'bilag', 'dato', 'tekst', 'konto', 'momskode'])
    return(df_db)

def load_uploaded_csv_into_dataframe(uploaded_csv):
    df = pd.read_csv(uploaded_csv, sep=';')
    return(df)

def clean_data_and_prepare_for_merge(df):
    df.dropna(how='all', axis=1, inplace=True)  # Delete empty columns (economic specific)
    df.columns = ['fKontonr', 'tekst', 'debet']
    df["tekst"] = df["tekst"].str.lower()  # Python seems to be case-sensitive from using join.
    df = df.replace(r'^\s*$', np.NaN, regex=True)  # converts empty values to NaN
    df.dropna(subset=['tekst', 'debet'], inplace=True)
    df.drop(df[(df['debet'] == 0) | (df['debet'] == '0,00')].index, inplace=True)
    df.drop(df[(df['debet'] == '0') | (df['debet'] == '-0')].index, inplace=True)
    df = df[~df['tekst'].str.endswith('i alt', 'oresultat')]
    return(df)

def merge_acc_knowledge_dataframe_with_csv_dataframe(df, df_db):
    df = pd.merge(df, df_db, on='tekst', how='left')
    df = df.assign(type="F", bilag=1)
    df.drop(df[(df['debet'] == 0)].index, inplace=True)  # Høker Bugfix 26/08. Undersøg.
    df.dropna(subset=['debet'], inplace=True)   # Høker Bugfix 26/08. Undersøg.
    df.drop('fKontonr', axis=1, inplace=True)
    df = df[['type', 'bilag', 'dato', 'tekst', 'konto', 'momskode', 'debet']]  # Sort rows for Meneto
    df = df.drop_duplicates()
    return(df)

def convert_dataframe_to_csv_and_download(df):
    mitOutput = StringIO()
    df.to_csv(mitOutput,index=False, sep=';')
    output_csv_file = Response(mitOutput.getvalue(), mimetype="text/csv")
    output_csv_file.headers["Content-Disposition"] = "attachment; filename=\"saaaldo.csv\""
    return(output_csv_file)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/import_convert_download_route', methods=['POST'])
def load_input_convert_and_download_converted_csv():
    uploaded_csv = request.files.get('inputfile_html_attribute')
    df_db = load_data_from_sql_database_into_dataframe()
    df = load_uploaded_csv_into_dataframe(uploaded_csv)
    df = clean_data_and_prepare_for_merge(df)
    df = merge_acc_knowledge_dataframe_with_csv_dataframe(df, df_db)
    output_csv_file = convert_dataframe_to_csv_and_download(df)
    return output_csv_file
    
if __name__ == '__main__':
    app.run()
