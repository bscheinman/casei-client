import cix_client
import collections
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

class LineDirection:
    FLAT = 0
    UP = 1
    DOWN = 2

LineDelta = collections.namedtuple('LineDelta', ['direction', 'price', 'quantity'])

def render_line_delta(side_name, delta):
    if delta.direction == LineDirection.UP:
        direction = ' :arrow_up_small:'
    elif delta.direction == LineDirection.DOWN:
        direction = ' :arrow_down_small:'
    else:
        direction = ''

    return '{0}: {1} @ {2:.2f}{3}'.format(side_name, delta.quantity, delta.price,
            direction)

def publish_change(team, bid_delta, ask_delta):
    team_link = '<https://caseinsensitive.org/ncaa/game/{0}/team/{1}/?start_tab=stock_tab|{1}>'.format(game_id, team)
    bid_text = render_line_delta('Bid', bid_delta)
    ask_text = render_line_delta('Ask', ask_delta)

    message = '\n'.join((team_link, bid_text, ask_text))

    data = {
        'text': message
    }
    response = requests.post(webhook_url, json=data)

    if response.status_code != 200:
        sys.err.write('error publishing change: {0}\n'.format(response.text))

def line_delta(old_md, new_md, side):
    old_price = old_md.get(side, 0.0)
    new_price = new_md.get(side, 0.0)
    new_quantity = new_md.get('{0}_size'.format(side), 0)

    if new_price > old_price:
        direction = LineDirection.UP
    elif new_price < old_price:
        direction = LineDirection.DOWN
    else:
        direction = LineDirection.FLAT

    return LineDelta(price=new_price, quantity=new_quantity, direction=direction)

def publish_updated_lines(old_md, new_md):
    lines = []

    for team, line in new_md.iteritems():
        # Ignore lines that clear out when games start
        if not line.get('bid', 0.0) and not line.get('ask', 0.0):
            continue

        old_line = old_md.get(team, {})
        bid_delta = line_delta(old_line, line, 'bid')
        ask_delta = line_delta(old_line, line, 'ask')

        if bid_delta.direction != LineDirection.FLAT or \
                ask_delta.direction != LineDirection.FLAT:
            publish_change(team, bid_delta, ask_delta)

    return lines

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
            publish_updated_lines(old_md, md)

        old_md = md
            
        time.sleep(refresh_interval)

