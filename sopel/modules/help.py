# coding=utf-8
"""
help.py - Sopel Help Module
Copyright 2008, Sean B. Palmer, inamidst.com
Copyright © 2013, Elad Alfassa, <elad@fedoraproject.org>
Copyright © 2018, Adam Erdman, pandorah.org
Licensed under the Eiffel Forum License 2.

https://sopel.chat
"""
from __future__ import unicode_literals, absolute_import, print_function, division

import collections
import requests
import socket
import textwrap

from sopel.logger import get_logger
from sopel.module import commands, rule, example, priority
from sopel.config.types import (
    StaticSection, ChoiceAttribute
)


# Pastebin handlers


def _requests_post_catch_errors(*args, **kwargs):
    try:
        response = requests.post(*args, **kwargs)
        response.raise_for_status()
    except (
            requests.exceptions.Timeout,
            requests.exceptions.TooManyRedirects,
            requests.exceptions.RequestException,
            requests.exceptions.HTTPError
    ):
        # We re-raise all expected exception types to a generic "posting error"
        # that's easy for callers to expect, and then we pass the original
        # exception through to provide some debugging info
        LOGGER.exception('Error during POST request')
        raise PostingException('Could not communicate with remote service')

    # remaining handling (e.g. errors inside the response) is left to the caller
    return response


def post_to_clbin(msg):
    try:
        result = _requests_post_catch_errors('https://clbin.com/', data={'clbin': msg})
    except PostingException:
        raise

    result = result.text
    if 'https://clbin.com/' in result:
        return result
    else:
        LOGGER.error("Invalid result %s", result)
        raise PostingException('clbin result did not contain expected URL base.')


def post_to_0x0(msg):
    try:
        result = _requests_post_catch_errors('https://0x0.st', files={'file': msg})
    except PostingException:
        raise

    result = result.text
    if 'https://0x0.st' in result:
        return result
    else:
        LOGGER.error('Invalid result %s', result)
        raise PostingException('0x0.st result did not contain expected URL base.')


def post_to_hastebin(msg):
    try:
        result = _requests_post_catch_errors('https://hastebin.com/documents', data=msg)
    except PostingException:
        raise

    try:
        result = result.json()
    except ValueError:
        LOGGER.error("Invalid Hastebin response %s", result)
        raise PostingException('Could not parse response from Hastebin!')

    if 'key' not in result:
        LOGGER.error("Invalid result %s", result)
        raise PostingException('Hastebin result did not contain expected URL base.')
    return "https://hastebin.com/" + result['key']


def post_to_termbin(msg):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)  # the bot may NOT wait forever for a response; that would be bad
    try:
        s.connect(('termbin.com', 9999))
        s.sendall(msg)
        s.shutdown(socket.SHUT_WR)
        response = ""
        while 1:
            data = s.recv(1024)
            if data == "":
                break
            response += data
        s.close()
    except socket.error:
        LOGGER.exception('Error during communication with termbin')
        raise PostingException('Error uploading to termbin')

    return response.strip(u'\x00\n')


_pastebin_providers = {
    'clbin': post_to_clbin,
    '0x0': post_to_0x0,
    'hastebin': post_to_hastebin,
    'termbin': post_to_termbin
}


class HelpSection(StaticSection):
    output = ChoiceAttribute('output',
                             list(_pastebin_providers),
                             default='clbin')


def configure(config):
    config.define_section('help', HelpSection)
    provider_list = ', '.join(_pastebin_providers)
    config.help.configure_setting(
        'output',
        'Pick a pastebin provider: {}: '.format(provider_list)
    )


LOGGER = get_logger(__name__)


def setup(bot):
    global help_prefix
    help_prefix = bot.config.core.help_prefix
    bot.config.define_section('help', HelpSection)


@rule('$nick' r'(?i)(help|doc) +([A-Za-z]+)(?:\?+)?$')
@example('.help tell')
@commands('help', 'commands')
@priority('low')
def help(bot, trigger):
    """Shows a command's documentation, and possibly an example."""
    if trigger.group(2):
        name = trigger.group(2)
        name = name.lower()

        # number of lines of help to show
        threshold = 3

        if name in bot.doc:
            if len(bot.doc[name][0]) + (1 if bot.doc[name][1] else 0) > threshold:
                if trigger.nick != trigger.sender:  # don't say that if asked in private
                    bot.reply('The documentation for this command is too long; I\'m sending it to you in a private message.')

                def msgfun(l):
                    bot.msg(trigger.nick, l)
            else:
                msgfun = bot.reply

            for line in bot.doc[name][0]:
                msgfun(line)
            if bot.doc[name][1]:
                msgfun('e.g. ' + bot.doc[name][1])
    else:
        # This'll probably catch most cases, without having to spend the time
        # actually creating the list first. Maybe worth storing the link and a
        # heuristic in the DB, too, so it persists across restarts. Would need a
        # command to regenerate, too...
        if (
                'command-list' in bot.memory and
                bot.memory['command-list'][0] == len(bot.command_groups) and
                bot.memory['command-list'][2] == bot.config.help.output
        ):
            url = bot.memory['command-list'][1]
        else:
            bot.say("Hang on, I'm creating a list.")
            msgs = []

            name_length = max(6, max(len(k) for k in bot.command_groups.keys()))
            for category, cmds in collections.OrderedDict(sorted(bot.command_groups.items())).items():
                category = category.upper().ljust(name_length)
                cmds = set(cmds)  # remove duplicates
                cmds = '  '.join(cmds)
                msg = category + '  ' + cmds
                indent = ' ' * (name_length + 2)
                # Honestly not sure why this is a list here
                msgs.append('\n'.join(textwrap.wrap(msg, subsequent_indent=indent)))

            url = create_list(bot, '\n\n'.join(msgs))
            if not url:
                return
            bot.memory['command-list'] = (len(bot.command_groups),
                                          url,
                                          bot.config.help.output)
        bot.say("I've posted a list of my commands at {0} - You can see "
                "more info about any of these commands by doing {1}help "
                "<command> (e.g. {1}help time)".format(url, help_prefix))


def create_list(bot, msg):
    msg = 'Command listing for {}@{}\n\n'.format(bot.nick, bot.config.core.host) + msg

    try:
        result = _pastebin_providers[bot.config.help.output](msg)
    except PostingException:
        bot.say("Sorry! Something went wrong.")
        LOGGER.exception("Error posting commands")
        return
    return result


class PostingException(Exception):
    pass


@rule('$nick' r'(?i)help(?:[?!]+)?$')
@priority('low')
def help2(bot, trigger):
    response = (
        "Hi, I'm a bot. Say {1}commands to me in private for a list "
        "of my commands, or see https://sopel.chat for more "
        "general details. My owner is {0}."
        .format(bot.config.core.owner, help_prefix))
    bot.reply(response)
