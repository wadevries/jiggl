import datetime
import requests


class JIRA(object):
    def __init__(self, server, username, password):
        self.server = server
        self.auth = (username, password)

    def api(self, method, endpoint, data=None, params=None):
        response = requests.request(method, f'https://{self.server}.atlassian.net/rest/api/2/{endpoint}', json=data,
                                    auth=self.auth, params=params)
        response.raise_for_status()
        return response.json()

    def get(self, *args, **kwargs):
        return self.api('get', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.api('post', *args, **kwargs)

    def log_time(self, issue, start, duration, comment=None):
        data = {'started': f'{start:%Y-%m-%dT%H:%M:%S}.000+0000', 'timeSpentSeconds': duration}
        if comment:
            data['comment'] = comment

        return self.post(f'issue/{issue}/worklog', data, params={'notifyUsers': 'false'})
