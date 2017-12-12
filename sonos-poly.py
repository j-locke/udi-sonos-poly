#!/usr/bin/env python
"""
Sonos NodeServer for UDI Polyglot v2
by Einstein.42 (James Milne) milne.james@gmail.com
"""

import polyinterface
import sys
import soco
import requests
import json

LOGGER = polyinterface.LOGGER
SERVERDATA = json.load(open('server.json'))
VERSION = SERVERDATA['credits'][0]['version']

class Controller(polyinterface.Controller):
    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.name = 'Sonos Controller'
        self.speakers = []

    def start(self):
        LOGGER.info('Starting Sonos Polyglot v2 NodeServer version {}'.format(VERSION))
        self.discover()

    def shortPoll(self):
        for node in self.nodes:
            self.nodes[node].update()

    def update(self):
        """
        Nothing to update for the controller.
        """
        pass

    def discover(self):
        LOGGER.info('Starting Speaker Discovery...')
        speakers = soco.discover()
        if speakers:
            LOGGER.info('Found {} Speaker(s).'.format(len(speakers)))
            for speaker in speakers:
                address = speaker.uid[8:22].lower()
                self.addNode(Speaker(self, self.address, address, speaker.player_name, speaker.ip_address))
        else:
            LOGGER.info('No Speakers found. Are they powered on?')

    commands = {'DISCOVER': discover}

class Speaker(polyinterface.Node):
    def __init__(self, parent, primary, address, name, ip):
        self.ip = ip
        self.zone = soco.SoCo(self.ip)
        LOGGER.info('Adding new Sonos Speaker: {}@{} Current Volume: {}'\
                    .format(name, ip, self.zone.volume))
        super(Speaker, self).__init__(parent, primary, address, 'Sonos {}'.format(name))

    def start(self):
        LOGGER.info("{} added. Updating information in ISY.".format(self.name))
        self.update()

    def update(self):
        try:
            self.setDriver('ST', self.zone.volume)
            self.setDriver('GV1', self.zone.bass)
            self.setDriver('GV2', self.zone.treble)
        except requests.exceptions.ConnectionError as e:
            LOGGER.error('Connection error to Speaker or ISY.: %s', e)

    def query(self, command):
        self.update()
        self.reportDrivers()

    def _play(self, command):
        self.zone.play()

    def _stop(self, command):
        self.zone.stop()

    def _pause(self, command):
        self.zone.pause()

    def _next(self, command):
        self.zone.next()

    def _previous(self, command):
        try:
            self.zone.previous()
        except:
            LOGGER.info("Error in command 'previous'. This typically means that the station or mode you are in doesn't support it.")

    def _partymode(self, command):
        self.zone.partymode()

    def _mute(self, command):
        if self.zone.mute:
            self.zone.mute = False
        else:
            self.zone.mute = True

    def _volume(self, command):
        val = command.get('value')
        if val:
            self.zone.volume = int(val)
            self.setDriver('ST', int(val), 56)

    def _bass(self, command):
        val = command.get('value')
        if val > -11 or val < 11:
            self.zone.bass = val
            self.setDriver('GV1', int(val), 56)

    def _treble(self, command):
        val = command.get('value')
        if val > -11 or val < 11:
            self.zone.treble = val
            self.setDriver('GV2', int(val), 56)

    drivers = [{'driver': 'GV1', 'value': 0, 'uom': '56'},
                {'driver': 'GV2', 'value': 0, 'uom': '56'},
                {'driver': 'GV3', 'value': 0, 'uom': '56'},
                {'driver': 'GV4', 'value': 0, 'uom': '56'},
                {'driver': 'ST', 'value': 0, 'uom': '51'}]

    commands = {    'PLAY': _play,
                    'STOP': _stop,
                    'DON': _play,
                    'DOF': _pause,
                    'PAUSE': _pause,
                    'NEXT': _next,
                    'PREVIOUS': _previous,
                    'PARTYMODE': _partymode,
                    'MUTE': _mute,
                    'BASS': _bass,
                    'TREBLE': _treble,
                    'VOLUME': _volume }

    id = 'sonosspeaker'

if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('Sonos')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
