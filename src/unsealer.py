import os
import signal
import queue
import time
import json
import requests
import dns.resolver
import getpass
from pyzabbix import ZabbixMetric
from pyzabbix import ZabbixSender
from pydantic import BaseSettings
from urllib3.exceptions import InsecureRequestWarning

class Settings(BaseSettings):
    VAULT_HEADLESS_SVC: str
    KEYS_QUORUM: int
    ZABBIX_ADDR: str
    ZABBIX_PORT: int
    ZABBIX_ITEM: str



def sigint_handler(sig, frame):
    print('You pressed Ctrl+C!')
    print ('I assume you want to deattach')
    print ('Hold Ctrl and press P and Q instead')


def ready(status:bool):
    if status:
        if not os.path.exists('/tmp/inloop'):
            os.mknod('/tmp/inloop')
    else:
        if os.path.exists('/tmp/inloop'):
            os.remove('/tmp/inloop')

def get_keys():
    ready(False)

    keys = []

    while (True):
        new_key = pswd = getpass.getpass('key: ')
        if not len(new_key):
            print("{}/{} keys are populated".format(len(keys), keys_quorum))
        elif new_key not in keys:
            keys.append(new_key)
            print("{}/{} keys are populated".format(len(keys), keys_quorum))
        else:
            print ("This key is already stored")
            print("{}/{} keys are populated".format(len(keys), keys_quorum))

        if (len(keys)==keys_quorum):
            print("\nAll keys are populated")
            print("Starting unseal control loop\n")
            return (keys)

    
def unseal_loop(keys):
    while (True):
        metrics = []
        metrics.append(alive_metric)
        sealed=True
        try:
            nodes=dns.resolver.query(vault_headless_svc, 'A')
        except Exception as e:
                print ("Cant resolve DNS names for nodes. Is addr is correct and cluster is running?")
                print (e)
                break
        for i,node in enumerate(nodes):
            try:
                resp = requests.get(url="http://{}:8200/v1/sys/seal-status".format(node))
                data = resp.json()
            except Exception as e:
                print ("Issues, when connecting to vault {}: {}".format(i,e))
                ready(False)
                break
            
            if type(data) == dict:
                sealed = bool(data.get("sealed"))
            else:
                print ("Unexpected or empty reply from vault{}: {}".format(i,data))
                ready(False)
                break

            if sealed:
                print ("Vault {} is sealed. Starting to unseal.".format(i))
                for key in keys:
                    url = "http://{}:8200/v1/sys/unseal".format(node)
                    datakey = {}
                    datakey['key']=key
                    try:
                        ureply = requests.put(url=url,data=json.dumps(datakey))
                        udata = ureply.json()
                        print ("Key sent to {}".format(i))
                        if udata and type(udata) == dict:
                            progress = udata.get("progress")
                            print("progress: ",progress)
                        else:
                            print("Unexpected reply from vault{}: {}".format(i,udata))
                            ready(False)
                            break
                            
                        time.sleep(1)
                    except Exception as e:
                        print ("Issues, when connecting to vault{}: {}".format(i,e))
                        ready(False)
                        break
                
                try:
                    resp = requests.get(url="http://{}:8200/v1/sys/seal-status".format(node))
                    data = resp.json()
                except Exception as e:
                    print ("Issues, when connecting to vault{}: {}".format(i,e))
                    ready(False)
                    break

                if data and type(data) == dict:
                    sealed = bool(data.get("sealed"))
                    if sealed:
                        print ("Keys are sent, but vault {} is still unsealed:".format(i))
                        print ("Dying")
                        print (udata)
                        ready(False)
                        return
                    else:
                        print ("Unsealed vault{} sucsessfully".format(i))
                        ready(True)
                        zbx.send(metrics)
            else:
                print("Vault node {} is not sealed".format(i))
                ready(True)
                zbx.send(metrics)

        time.sleep(30)
        print ("")




if (__name__ == '__main__'): 

    signal.signal(signal.SIGINT, sigint_handler)
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

    alive_metric = ZabbixMetric(Settings().ZABBIX_ITEM, 'unsealer_is_alive', 1)
    zbx = ZabbixSender(zabbix_server=Settings().ZABBIX_ADDR, zabbix_port=Settings().ZABBIX_PORT, use_config=None, chunk_size=250)

    keys_quorum = Settings().KEYS_QUORUM
    vault_headless_svc=Settings().VAULT_HEADLESS_SVC

    keys=get_keys()
    unseal_loop(keys)
