# -*- Encoding: utf-8 -*-
###
# Copyright (c) 2005-2007 Dennis Kaarsemaker
# Copyright (c) 2008-2011 Terence Simpson
# Copyright (c) 2010 Elián Hanisch
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
###

import supybot.conf as conf
import supybot.registry as registry

class ValidTypes(registry.OnlySomeStrings):
    """Invalid type, valid types are: 'removal', 'ban' or 'quiet'."""
    validStrings = ('removal', 'ban', 'quiet')


class SpaceSeparatedListOfTypes(registry.SpaceSeparatedListOf):
    Value = ValidTypes


def configure(advanced):
    from supybot.questions import yn, something, output
    import sqlite
    import re
    import os
    from supybot.utils.str import format

    def anything(prompt, default=None):
        """Because supybot is pure fail"""
        from supybot.questions import expect
        return expect(prompt, [], default=default)

    Bantracker = conf.registerPlugin('Bantracker', True)

    def getReviewTime():
        output("How many days should the bot wait before requesting a ban/quiet review?")
        review = something("Can be an integer or decimal value. Zero disables reviews.", default=str(Bantracker.request.review._default))

        try:
            review = float(review)
            if review < 0:
                raise TypeError
        except TypeError:
            output("%r is an invalid value, it must be an integer or float greater or equal to 0" % review)
            return getReviewTime()
        else:
            return review

    output("If you choose not to enabled Bantracker for all channels, it can be enabled per-channel with the '@Config channel' command")
    enabled = yn("Enable Bantracker for all channels?")
    database = something("Location of the Bantracker database", default=Bantracker.database._default)
    bansite = anything("URL of the Bantracker web interface, without the 'bans.cgi'. (leave this blank if you aren't running a web server)")

    request = yn("Enable review and comment requests from bot?", default=False)
    if request and advanced:
        output("Which types would you like the bot to request comments for?")
        output(format("The available request types are %L", Bantracker.request.type._default))
        types = anything("Separate types by spaces or commas:", default=', '.join(Bantracker.request.type._default))
        type = set([])
        for name in re.split(r',?\s+', types):
            name = name.lower()
            if name in ValidTypes.validStrings:
                type.add(name)

        output("Which nicks should be bot not requets comments from?")
        output("This is useful if you have automated channel bots that should not be directly asked for reviews")
        output("Is case-insensitive and the wildcards '*' and '?' are accepted.")
        ignores = anything("Separate nicks by spaces or commas:", default=', '.join(Bantracker.request.ignore._default))
        ignore = set([])
        for name in re.split(r',?\s+', ignores):
            name = name.lower()
            ignore.add(name)

        output("You can set the comment and review requests for some nicks to be forwarded to specific nicks/channels")
        output("This is useful if you have automated channel bots that should not be directly asked for reviews")
        output("Which nicks should these requests be forwarded for?")
        output("Is case-insensitive and the wildcards '*' and '?' are accepted.")
        forwards = anything("Separate nicks by spaces or commas:", default=', '.join(Bantracker.request.forward._default))
        forward = set([])
        for name in re.split(r',?\s+', forwards):
            name = name.lower()
            forward.add(name)

        output("Which nicks/channels should those requests be forwarded to?")
        output("Is case-insensitive and wildcards '*' and '?' are accepted.")
        channels_i = anything("Separate nicks/channels by spaces or commas:", default=', '.join(Bantracker.request.forward._default))
        channels = set([])
        for name in re.split(r',?\s+', channels_i):
            name = name.lower()
            channels.add(name)

        review = getReviewTime()

    else:
        type = Bantracker.request.type._default
        ignore = Bantracker.request.ignore._default
        forward = Bantracker.request.forward._default
        channels = Bantracker.request.forward.channels._default
        review = Bantracker.request.review._default

    Bantracker.enabled.setValue(enabled)
    Bantracker.database.setValue(database)
    Bantracker.bansite.setValue(bansite)
    Bantracker.request.setValue(request)
    Bantracker.request.type.setValue(type)
    Bantracker.request.ignore.setValue(ignore)
    Bantracker.request.forward.setValue(forward)
    Bantracker.request.forward.channels.setValue(channels)
    Bantracker.request.review.setValue(review)

    # Create the initial database
    db_file = Bantracker.database()
    if not db_file:
        db_file = conf.supybot.directories.data.dirize('bans.db')
        output("supybot.plugins.Bantracker.database will be set to %r" % db_file)
        Bantracker.database.setValue(db_file)

    if os.path.exists(db_file):
        output("%r already exists" % db_file)
        return

    output("Creating an initial database in %r" % db_file)
    con = sqlite.connect(db_file)
    cur = con.cursor()

    try:
        cur.execute("""CREATE TABLE 'bans' (
    id INTEGER PRIMARY KEY,
    channel VARCHAR(30) NOT NULL,
    mask VARCHAR(100) NOT NULL,
    operator VARCHAR(30) NOT NULL,
    time VARCHAR(300) NOT NULL,
    removal DATETIME,
    removal_op VARCHAR(30),
    log TEXT
)""")
#"""

        cur.execute("""CREATE TABLE comments (
    ban_id INTEGER,
    who VARCHAR(100) NOT NULL,
    comment MEDIUMTEXT NOT NULL,
    time VARCHAR(300) NOT NULL
)""")
#"""

        cur.execute("""CREATE TABLE sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    user MEDIUMTEXT NOT NULL,
    time INT NOT NULL
)""")
#"""

        cur.execute("CREATE INDEX comments_ban_id ON comments(ban_id)")

    except:
        con.rollback()
        raise
    else:
        con.commit()
    finally:
        cur.close()
        con.close()

    ## Notes on setting up the web interface.
    output("If you wish to use the web interface to Bantracker, please copy the cgi")
    output("direcdtory to somewhere accessible from your webserver. Remember to modify")
    output("the CONFIG_FILENAME variable in cgi/bans.cgi, and modify the")
    output("bantracker.conf configuration file with the appropriate information.")
    output("See the README.txt file for more information.")

Bantracker = conf.registerPlugin('Bantracker')
conf.registerChannelValue(Bantracker, 'enabled',
        registry.Boolean(False, """Enable the bantracker"""))
conf.registerGlobalValue(Bantracker, 'database',
        registry.String(conf.supybot.directories.data.dirize('bans.db'), "Filename of the bans database", private=True))
conf.registerGlobalValue(Bantracker, 'bansite',
        registry.String('', "Web site for the bantracker, without the 'bans.cgi' appended", private=True))

conf.registerChannelValue(Bantracker, 'request',
        registry.Boolean(False,
            "Enable message requests from bot"))
conf.registerChannelValue(Bantracker.request, 'type',
        SpaceSeparatedListOfTypes(['removal', 'ban', 'quiet'],
            "List of events for which the bot should request a comment."))
conf.registerChannelValue(Bantracker.request, 'ignore',
        registry.SpaceSeparatedListOfStrings(['FloodBot?', 'FloodBotK?', 'ChanServ'],
            "List of nicks for which the bot won't request a comment."\
            " Is case insensible and wildcards * ? are accepted."))
conf.registerChannelValue(Bantracker.request, 'forward',
        registry.SpaceSeparatedListOfStrings([],
            "List of nicks for which the bot will forward the request to"\
            " the channels/nicks defined in forwards.channels option."\
            " Is case insensible and wildcards * ? are accepted."))
conf.registerChannelValue(Bantracker.request.forward, 'channels',
        registry.SpaceSeparatedListOfStrings([],
            "List of channels/nicks to forward the comment request if the op is in the forward list."))

conf.registerChannelValue(Bantracker, 'review',
        registry.Boolean(True,
            "Enable/disable reviews per channel."))
conf.registerGlobalValue(Bantracker.review, 'when',
        registry.Float(7,
            "Days after which the bot will request for review a ban. Can be an integer or decimal"
            " value. Zero disables reviews globally."))
conf.registerChannelValue(Bantracker.review, 'ignore',
        registry.SpaceSeparatedListOfStrings(['FloodBot?', 'FloodBotK?', 'ChanServ'],
            "List of nicks for which the bot won't request a review."\
            " Is case insensible and wildcards * ? are accepted."))
conf.registerChannelValue(Bantracker.review, 'forward',
        registry.SpaceSeparatedListOfStrings([],
            "List of nicks for which the bot will forward the reviews to"\
            " the channels/nicks defined in forwards.channels option."\
            " Is case insensible and wildcards * ? are accepted."))
conf.registerChannelValue(Bantracker.review.forward, 'channels',
        registry.SpaceSeparatedListOfStrings([],
            "List of channels/nicks to forward the request if the op is in the forward list."))

conf.registerChannelValue(Bantracker, 'autoremove',
        registry.Boolean(True,
            """Enable/disable autoremoval of bans."""))
conf.registerChannelValue(Bantracker.autoremove, 'notify',
        registry.Boolean(True,
            """Enable/disable notifications of removal of bans."""))
conf.registerChannelValue(Bantracker.autoremove.notify, 'channels',
        registry.SpaceSeparatedListOfStrings([],
            """List of channels/nicks to notify about automatic removal of bans."""))



