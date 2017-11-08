import datetime
import os
import re
import sys
from configparser import ConfigParser
from itertools import groupby

import click

from api_client import TogglClientApi
from jira_client import JIRA


CONFIG_FILE_LOCATIONS = ['.jiggl', os.path.expanduser('~/.jiggl'), '.jiggle', os.path.expanduser('~/.jiggle')]


def load_config():
    config = ConfigParser()
    filename = config.read(CONFIG_FILE_LOCATIONS)
    return config, filename


class DateParameter(click.ParamType):
    name = 'date'

    def convert(self, value, param, ctx):
        try:
            return datetime.datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            self.fail('{} is not a valid date'.format(value))


DATE_TYPE = DateParameter()

JIRA_PATTERN = re.compile(r'^([A-Z]+-\d+)\b')


def get_issue(entry):
    m = JIRA_PATTERN.match(entry.get('description', ''))
    if m:
        return m.group(1)


def filter_entries(entries):
    def parse_date(e):
        e['start'] = datetime.datetime.strptime(e['start'], '%Y-%m-%dT%H:%M:%S+00:00')
        e['issue'] = get_issue(e)
        return e

    return [
        parse_date(entry)
        for entry in entries
        if get_issue(entry)
           and entry['duration'] >= 60  # JIRA doesn't like time entries less than 60 seconds
    ]


def format_seconds(duration):
    seconds = duration % 60
    minutes = int(duration / 60) % 60
    hours = int(duration / 3600)
    s = f'{minutes:02}:{seconds:02}'
    if hours:
        s = f'{hours}:{s}'
    return s


@click.command()
@click.option('--start-date', type=DATE_TYPE, help='The first date from which to collect time entries',
              default=(datetime.date.today() - datetime.timedelta(1)).strftime('%Y-%m-%d'))
@click.option('--end-date', default=lambda: datetime.date.today().strftime('%Y-%m-%d'), type=DATE_TYPE,
              help='The last date from which to collect time entries')
@click.option('--username', help='Your Atlassian Id\'s username')
@click.option('--server', prompt=True, help='Like https://<THIS VALUE>.atlassian.net/')
@click.option('--toggl-token', prompt=True, help='Toggl API token')
@click.password_option(prompt=False, help='Your Atlassian Id\'s password')
def run(start_date, end_date, username, password, server, toggl_token):
    toggl = TogglClientApi({'token': toggl_token, 'user-agent': 'Jiggl'})

    # 1. Fetch all time entries from Toggl
    time_entries = toggl.query('/time_entries', {'start_date': start_date.isoformat() + '+00:00',
                                                 'end_date': end_date.isoformat() + '+00:00'})

    if not time_entries.ok:
        print(time_entries.reason)
        sys.exit(1)

    selected_entries = filter_entries(time_entries.json())
    print('Log the following entries?')
    grouped = groupby(selected_entries, key=lambda e: e['start'].date())
    for day, entries in grouped:
        print(f'\n{day}  {day:%A}')
        print()
        for entry in entries:
            print(f"  {entry['start']:%H:%M}  {format_seconds(entry['duration']):>8}  {entry['description']}")

    if click.confirm('\nSend to JIRA?', abort=True):
        if not password:
            password = click.prompt('Atlassian ID password', hide_input=True)

        j = JIRA(server, username, password)
        with click.progressbar(selected_entries, label='Sending to JIRA') as bar:
            for entry in bar:
                j.log_time(entry['issue'], entry['start'], entry['duration'],
                           entry['description'][len(entry['issue']):].strip())

        last_start = max(entry['start'] for entry in selected_entries)
        if last_start:
            config, filename = load_config()
            config['jira']['start_date'] = (last_start.date() + datetime.timedelta(1)).strftime('%Y-%m-%d')
            with open(filename[0], 'w') as configfile:
                config.write(configfile)


if __name__ == '__main__':
    config = load_config()[0]
    run(default_map=dict(config.items('toggl') + config.items('jira')) if config.sections() else {})
