import requests

class ApiException(Exception):
    def __init__(self, errors):
        if isinstance(errors, list):
            self.errors = errors
        else:
            self.errors = [errors]

class CixClient(object):
    def __init__(self, apid, host='https://caseinsensitive.org'):
        self.apid = apid
        self.root = '{0}/ncaa/api'.format(host)

    def do_api_call(self, path, data={}):
        data['apid'] = self.apid
        full_path = '{0}/{1}'.format(self.root, path)
        response = requests.post(full_path, data=data)

        try:
            result = response.json()
        except ValueError:
            raise ApiException(['could not decode response'])

        if not result.get('success', False):
            errors = result.get('errors', []) or ['unknown error']
            raise ApiException(errors)

        return result.get('result', None)

    def my_orders(self):
        return self.do_api_call('open_orders')

    def my_positions(self, full_names=False):
        args = {
            'name': 'full' if full_names else 'abbrev',
        }
        return self.do_api_call('positions', args)

    def my_markets(self):
        return self.do_api_call('my_markets')

    def all_market_data(self):
        return self.do_api_call('market_data')

    def recent_executions(self, mine_only=False, since=None):
        data = {
            'mine_only': bool(mine_only)
        }

        if since is not None:
            data['since'] = since

        return self.do_api_call('executions', data=data)

    def get_book(self, team, depth=None):
        data = { 'team': team }
        if depth is not None:
            data['depth'] = depth

        return self.do_api_call('get_book', data)

    def place_order(self, team, side, quantity, price, cancel_on_game=None):
        data = {
            'team_identifier': team,
            'side': side,
            'quantity': quantity,
            'price': price,
        }

        if cancel_on_game is not None:
            data['cancel_on_game'] = bool(cancel_on_game)

        return self.do_api_call('place_order', data)

    def cancel_order(self, order_id):
        return self.do_api_call('cancel_order', { 'order_id': order_id })

    def make_market(self, team, bid=None, bid_size=None, ask=None, ask_size=None):
        data = { 'team': team }

        if bid is None:
            data['bid'] = 0.0
            data['bid_size'] = 0
        else:
            if bid_size is None:
                raise ApiException('must provide bid size')
            data['bid'] = bid
            data['bid_size'] = bid_size

        if ask is None:
            data['ask'] = 0.0
            data['ask_size'] = 0
        else:
            if ask_size is None:
                raise ApiException('must provide ask size')
            data['ask'] = ask
            data['ask_size'] = ask_size

        return self.do_api_call('make_market', data)
