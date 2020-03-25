# app.py
#
# Main app definition
#
# Author: Matt Harrison, Set 4B, A00875065

# Date example: 2020-01-22T22:00:00Z

import connexion
from connexion import NoContent
import datetime
import json
import yaml
import os
import logging
import logging.config
import requests
from flask_cors import CORS, cross_origin
from apscheduler.schedulers.background import BackgroundScheduler

DATE_FORMAT_STR = "%Y-%m-%dT%H:%M:%SZ"

with open('app_conf.yaml', 'r') as f:
    app_config = yaml.safe_load(f.read())

with open('log_conf.yaml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')


# Functions
@cross_origin(origin='localhost', headers=['Content-Type', 'Authorization'])
def get_order_stats():
    """ Reads and returns stats from JSON file """
    logger.info("Get request received...")
    file_path = './' + app_config["datastore"]["filename"]
    if os.path.exists(file_path):
        data_file = open(file_path)
        file_data = data_file.read()
        json_data = json.loads(file_data)
        data_file.close()
    else:
        logging.error("Data file does not exist.")
        return NoContent, 404
    logging.debug(str(json_data))
    logging.info("Get request completed")
    return json_data, 200


def populate_stats():
    """ Periodically update stats"""
    logger.info("Start Periodic Processing...")
    file_path = './' + app_config["datastore"]["filename"]
    if os.path.exists(file_path):
        data_file = open(file_path)
        file_data = data_file.read()
        json_data = json.loads(file_data)
        data_file.close()
    else:
        json_data = {
            "num_pickup_orders": 0,
            "num_delivery_orders": 0,
            "updated_timestamp": "2020-01-01T00:00:00Z"
        }
    current_time = datetime.datetime.today().strftime(DATE_FORMAT_STR)
    updated_time = json_data["updated_timestamp"]

    pickup_query = requests.get("%s/pickup?startDate=%s&endDate=%s" % (app_config["eventstore"]["url"], updated_time, current_time))
    if pickup_query.status_code != 200:
        logger.error("Error when requesting pickup orders. Status code: " + str(pickup_query.status_code))
    else:
        logger.info("New pickup events received: " + str(len(pickup_query.json())))

    delivery_query = requests.get("%s/delivery?startDate=%s&endDate=%s" % (app_config["eventstore"]["url"], updated_time, current_time))
    if delivery_query.status_code != 200:
        logger.error("Error when requesting delivery orders. Status code: " + str(delivery_query.status_code))
    else:
        logger.info("New delivery events received: " + str(len(delivery_query.json())))

    json_data["num_pickup_orders"] = json_data["num_pickup_orders"] + len(pickup_query.json())
    json_data["num_delivery_orders"] = json_data["num_delivery_orders"] + len(delivery_query.json())
    json_data["updated_timestamp"] = current_time

    data_file = open(file_path, "w")
    data_file.write(json.dumps(json_data))
    data_file.close()

    logger.debug("Updated stats data: " + json.dumps(json_data))
    logger.info("End Periodic Processing")


def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats, 'interval', seconds=app_config['scheduler']['period_sec'])
    sched.start()


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml")

if __name__ == "__main__":
    init_scheduler()
    app.run(host="127.0.0.1", port=8100)
    CORS(app.app, origins="localhost")
    app.app.config["CORS_HEADERS"] = "Content-Type"
