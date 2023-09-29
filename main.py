#!/usr/bin/env python3

from threading import Event
import json
import os
import solaredge_modbus
import sys
import paho.mqtt.client as mqtt

exit = Event()


def dict_to_topics(root: str,d: dict):
    res = []
    for key,value in d.items():
        topic = f"{root}/{key}"
        if type(value) == dict:
            res = res + (dict_to_topics(topic,value))
        else:
            res.append((topic,value))
    return res
def publish_topics(client: mqtt.Client, l: list):
    for value in l:
        client.publish(topic=value[0],payload=value[1])

def connectMQTT(host: str, port:int, user:str,password:str):
    client = mqtt.Client()
    if user != "":
        client.username_pw_set(username=user,password=password)
    ret = client.connect(host, port, 60)
    
    if ret != 0:
        print("Could not connect to MQTT Broker")
        sys.exit(-1)
    return client

def connectInverter(host,port,timeout,unit):
    print(host,port,timeout,unit)
    inverter = solaredge_modbus.Inverter(
        host=host,
        port=port,
        timeout=timeout,
        unit=unit
    )
    inverter.connect()

    if not inverter.connected():
        print("Could not connect to Inverter")
        sys.exit(-1)
    return inverter

def read_data(inverter: solaredge_modbus.Inverter):
    values = {}
    values = inverter.read_all()
    meters = inverter.meters()
    batteries = inverter.batteries()
    values["meters"] = {}
    values["batteries"] = {}

    for meter, params in meters.items():
        meter_values = params.read_all()
        values["meters"][meter] = meter_values

    for battery, params in batteries.items():
        battery_values = params.read_all()
        values["batteries"][battery] = battery_values
    return values


def runfn(mqclient: mqtt.Client,inverter: solaredge_modbus.Inverter):
    values = read_data(inverter)
    #mqclient.publish(topic="solar/sepv",payload=json.dumps(values))
    topics = dict_to_topics("solar/sepv",values)
    publish_topics(mqclient,topics)

def main():
    MQTTHOST = os.getenv("MQTT_HOST")
    MQTTPORT = int(os.getenv("MQTT_PORT"))
    MQTTUSER = os.getenv("MQTT_USER")
    MQTTPASS = os.getenv("MQTT_PASS")
    INVERTER_HOST = os.getenv("INVERTER_HOST")
    INVERTER_PORT = int(os.getenv("INVERTER_PORT"))
    REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL"))
    INVERTER_TIMEOUT = 1
    INVERTER_UNIT = 1
    
    mqclient = connectMQTT(MQTTHOST,MQTTPORT,MQTTUSER,MQTTPASS)
    inverter = connectInverter(INVERTER_HOST,INVERTER_PORT,INVERTER_TIMEOUT,INVERTER_UNIT)

    while not exit.is_set():
        #if not mqclient.is_connected():
        #    print("Reconnecting MQTT")
        #    mqclient.reconnect()
        if not inverter.connected():
            connectInverter(INVERTER_HOST,INVERTER_PORT,INVERTER_TIMEOUT,INVERTER_UNIT)
        runfn(mqclient,inverter)
        exit.wait(REFRESH_INTERVAL)
    mqclient.disconnect()
    inverter.disconnect()

def quit(signo, _frame):
    print("Interrupted by %d, shutting down" % signo)
    exit.set()

if __name__ == '__main__':
    import signal
    for sig in ('TERM', 'HUP', 'INT'):
        signal.signal(getattr(signal, 'SIG'+sig), quit);

    main()