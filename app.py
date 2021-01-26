import os
from flask import Flask
from flask import render_template, json, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import pandas as pd
import datetime
import pickle

app = Flask(__name__)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per minute"],
)

def get_generation(date_string, country_code) -> dict:
    from entsoe import EntsoePandasClient
    client = EntsoePandasClient(api_key=os.getenv("ENTSOE_API_KEY"))
    start = pd.Timestamp(date_string, tz='Europe/Brussels')
    end = start + pd.Timedelta("1 days")
    filename = os.path.join("files", country_code, f"{date_string}.pkl")
    if os.path.isfile(filename):
        with open(filename, "rb") as file:
            dic = pickle.load(file)
    else:
        directory = os.path.dirname(filename)
        os.makedirs(directory, exist_ok=True)
        df = client.query_generation(country_code, start=start,end=end, psr_type=None, nett=True).sum()
        dic = dict(df)
        with open(filename, "wb") as file:
            pickle.dump(dic, file)

    # df is a series
    return dic

@app.route("/", methods=['GET'])
@limiter.limit("100 per minute")
def index():
    date_string = request.args.get("date", "20201111", str)
    country_code = request.args.get("country", "DE", str)
    try:
        datetime.datetime.strptime(date_string, "%Y%m%d")
        data = get_generation(date_string, country_code)
        response = app.response_class(
            response=json.dumps(data),
            status=200,
            mimetype='application/json'
        )
    except ValueError:
        response = app.response_class(
            response=json.dumps("wrong date format"),
            status=400,
            mimetype="application/json"
        )
    return response


if __name__ == "__main__":
  app.run(host='0.0.0.0', port=1024, debug=True)