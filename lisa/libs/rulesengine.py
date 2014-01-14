# -*- coding: UTF-8 -*-
import json, re, sys, os, inspect, gettext
from pymongo import MongoClient
from twisted.python.reflect import namedAny
from twisted.python import log

class RulesEngine():
    def __init__(self, configuration):
        self.configuration = configuration
        client = MongoClient(configuration['database']['server'], configuration['database']['port'])
        self.database = client.lisa
        self.build_default_schema()
        path = os.path.realpath(os.path.abspath(os.path.join(os.path.split(
        inspect.getfile(inspect.currentframe()))[0],os.path.normpath("lang/"))))
        self._ = translation = gettext.translation(domain='lisa', localedir=path, languages=[self.configuration['lang']]).ugettext



    def build_default_schema(self):
        key_defaultanswer =     {   "name": "DefaultAnwser" }
        data_defaultanswer =    {
                                    "name": "DefaultAnwser",
                                    "order": 999,
                                    "before": None,
                                    "after": """lisaprotocol.answerToClient(json.dumps(
                                                    {
                                                        'plugin': jsonOutput['plugin'],
                                                        'method': jsonOutput['method'],
                                                        'body': jsonOutput['body'],
                                                        'clients_zone': ['sender'],
                                                        'from': jsonOutput['from']
                                                    }))""",
                                    "end": True,
                                    "enabled": True
                                }
        self.database.rules.update(key_defaultanswer, data_defaultanswer, upsert=True)

    def Rules(self, jsonData, lisaprotocol):
        rulescollection = self.database.rules
        pluginscollection = self.database.plugins
        intentscollection = self.database.intents
        jsonInput = lisaprotocol.wit.message_send(unicode(jsonData['body']))
        jsonInput['from'], jsonInput['type'], jsonInput['zone'] = jsonData['from'], jsonData['type'], jsonData['zone']

        if self.configuration['debug']['debug_before_before_rule']:
            log.msg("Before 'before' rule: " + str(jsonInput))
        for rule in rulescollection.find({"enabled": True, "before": {"$ne":None}}).sort([("order", 1)]):
            exec(rule['before'])
        if self.configuration['debug']['debug_after_before_rule']:
            log.msg("After 'before' rule: " + str(jsonInput))
        if self.configuration['debug']['debug_wit']:
            log.msg("WIT: " + str(jsonInput['outcome']))


        #TODO load the intent from intentscollection. It will point on a string on plugin or core
        oIntent = intentscollection.find_one({"name": jsonInput['outcome']['intent']})
        print oIntent
        if oIntent and jsonInput['outcome']['confidence'] >= self.configuration['wit_confidence']:
            instance = namedAny(str(oIntent["module"]))(lisa=lisaprotocol)
            methodToCall = getattr(instance, oIntent['function'])
            jsonOutput = methodToCall(jsonInput)
        else:
            jsonOutput = {}
            jsonOutput['plugin'] = "None"
            jsonOutput['method'] = "None"
            jsonOutput['body'] = self._("I have not the right plugin installed to answer you correctly")
        jsonOutput['from'] = jsonData['from']
        if self.configuration['debug']['debug_before_after_rule']:
            log.msg("Before 'after' rule: " + str(jsonOutput))
        for rule in rulescollection.find({"enabled": True, "after": {"$ne":None}}).sort([("order", 1)]):
            exec(rule['after'])
            #todo it doesn't check if the condition of the rule after has matched to end the rules
            if rule['end']:
                break
        if self.configuration['debug']['debug_after_after_rule']:
            log.msg("After 'after' rule: " + str(jsonOutput))
