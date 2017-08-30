import cix_client
import json
import os
import requests
import sys
import time

config_path = sys.argv[1]

try:
    with open(config_path, 'r') as config_file:
        raw_config = config_file.read()
except IOError:
    sys.err.write('failed to read config file\n')
    sys.exit(1)

try:
    config_obj = json.loads(raw_config)
except ValueError:
    sys.err.write('failed to parse config file\n')
    sys.exit(1)

try:
    webhook_url = config_obj['webhook_url']
except KeyError:
    sys.err.write('no webhook url configured\n')
    sys.exit(1)

try:
    apid = config_obj['apid']
except KeyError:
    sys.err.write('no apid configured\n')
    sys.exit(1)

try:
    game_id = config_obj['game_id']
except KeyError:
    sys.err.write('no game id configured\n')
    sys.exit(1)

try:
    refresh_interval = int(config_obj.get('refresh_interval', '60'))
except ValueError:
    sys.err.write('invalid refresh interval\n')
    sys.exit(1)
else:
    if refresh_interval <= 0:
        sys.err.write('non-positive refresh interval\n')
        sys.exit(1)

def get_updated_lines(old_md, new_md):
    lines = []

    for team, line in new_md.iteritems():
        updated = False

        try:
            old_line = old_md[team]
        except KeyError:
            updated = True
        else:
            updated = line['bid'] != old_line['bid'] or \
                      line['ask'] != old_line['ask']

        if updated:
            lines.append((team, line))

    return lines

message_template = '<https://caseinsensitive.org/ncaa/game/{0}/team/{1}/?start_tab=stock_tab|{1}> \nBid: {2} @ {3:.2f}\nAsk: {4} @ {5:.2f}'
def publish_change(team, line):
    message = message_template.format(game_id, team, line['bid_size'],
            line['bid'], line['ask_size'], line['ask'])
    data = {
        'text': message
    }
    response = requests.post(webhook_url, json=data)

    if response.status_code != 200:
        sys.err.write('error publishing change: {0}\n'.format(response.text))

if __name__ == '__main__':
    client = cix_client.CixClient(apid)
    old_md = None
    while True:
        try:
            md = client.all_market_data()
        except ApiException as e:
            sys.err.write('error retrieving market data: {0}\n'.format(str(e)))
            continue

        if old_md is not None:
            for team, line in get_updated_lines(old_md, md):
                publish_change(team, line)

        old_md = md
            
        time.sleep(refresh_interval)

