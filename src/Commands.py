from src.RedditBot import RedditBot
import json
from datetime import datetime, timedelta
from src import nHentai, UrlHandler, EmbedFactory
import rule34
import random

IMAGES_BASE_PATH = "[redacted]"

FORGOTTEN_IMAGES = {

    "test": IMAGES_BASE_PATH + "test.jpg"

}

NON_NSFW_WARNING = "i ain't sending something nsfw in a non nsfw channel"

r_bot = None
r34_bot = None


async def general(message, bot):

    content = message.content

    for substitution in bot.substitutions:

        content = substitution(content)

        if not bot.stack and content != message.content:
            break

    if content != message.content:

        await bot.send(content, message.channel)


async def get_post(message, bot, multi=False):
    command = message.content.split(" ")

    try:
        r_bot.authorize()
        if len(command) == 2:
            posts = r_bot.get_posts(command[1], "hot", 1)

        elif len(command) == 3:
            try:
                posts = r_bot.get_posts(command[1], "hot", int(command[2]))
            except ValueError:
                posts = r_bot.get_posts(command[1], command[2], 1)

        elif len(command) == 4:
            posts = r_bot.get_posts(command[1], command[2], int(command[3]))

        else:
            await bot.send("too many/too little arguments", message.channel)
            return

    except KeyError:
        await bot.send("reddit api error; one of the arguments is wrong", message.channel)
        return

    if not posts:
        await bot.send("no posts found", message.channel)

    if multi:
        for post in posts:
            await handle_post(post, message, bot)
    else:
        await handle_post(posts[-1], message, bot)


async def handle_post(post, message, bot):

    try:  # attempt to get the data of the post
        data = post['data']
    except KeyError:  # if no data was found, than there is no post
        await bot.send("no posts found", message.channel)
        return

    if data['is_self']:  # if the post is marked as a selfpost
        print("self_post", data)
        embed = EmbedFactory.reddit_selfpost(data)

    else:
        try:  # check for a url
            link = data['url']
        except KeyError:  # if there is no url, then something is wrong; send a message and return
            await bot.send("Something went wrong!", message.channel)
            return

        print("Handling link:", link)
        link = UrlHandler.handle(link)  # see if UrlHandler can understand the link

        if not link:  # if UrlHandler failed (returns none, it's a link post)
            print("link_post", data)
            embed = EmbedFactory.reddit_link_post(data)

        else:  # if UrlHandler succeeded, it's an image post
            print("imagepost", data)
            embed = EmbedFactory.reddit_image_post(data, link)

    await bot.send("", message.channel, embed=embed)


async def stack(message, bot):
    arg = message.content.split(" ")

    try:
        if arg[1].lower() in ("yes", "true", "t", "1"):
            bot.stack = True
        else:
            bot.stack = False

    except IndexError:
        bot.stack = not bot.stack

    await bot.send("Changed `stack` to `" + str(bot.stack) + "`", message.channel)
    bot.update_subs()


async def handle_command(command, message, bot):

    try:
        method = command_list[command]
    except KeyError:
        method = default_command

    await method(message, bot)


async def handle_message(message, bot):

    if message.content.startswith(trigger):

        command = message.content.strip(trigger).split()[0]
        await handle_command(command, message, bot)

    else:

        try:
            int(message.content)
            await get_nhentai(message, bot)
            return
        except ValueError:
            await general(message, bot)


async def _help(message, bot):
    bot.send("ask the present phone microwave; past phone microwave is too damn lazy to explain it", message.channel)


async def ping(message, bot):

    ping_time = datetime.utcnow()

    message = await bot.send("Pinging...", message.channel)

    pong_time = datetime.utcnow()

    ping_milliseconds = (pong_time - ping_time) / timedelta(milliseconds=1)

    await message.edit(content="Ping: %d ms" % ping_milliseconds)


async def unknown_command(message, bot):
    await bot.send("Even Amadeus is confused! (by your command)", message.channel)


async def get_nhentai(message, bot):

    try:
        if not message.channel.is_nsfw():
            await bot.send(NON_NSFW_WARNING, message.channel)
            return
    except AttributeError:
        pass

    gallery = nHentai.Gallery(message.content)

    await bot.send("", message.channel, embed=gallery.create_embed())


async def random_nhentai(message, bot):

    try:
        if not message.channel.is_nsfw():
            await bot.send(NON_NSFW_WARNING, message.channel)
            return
    except AttributeError:
        pass

    gallery = nHentai.Gallery(nHentai.random())

    await bot.send("", message.channel, embed=gallery.create_embed())


async def nhentai_search(message, bot):

    try:
        if not message.channel.is_nsfw():
            await bot.send(NON_NSFW_WARNING, message.channel)
            return
    except AttributeError:
        pass

    search_query = " ".join(message.content.split(" ")[1:])
    results = nHentai.search(search_query)

    await bot.send("", message.channel, embed=EmbedFactory.nhentai_gallery_list(search_query, results))


async def rule34_search(message, bot):

    try:
        if not message.channel.is_nsfw():
            await bot.send(NON_NSFW_WARNING, message.channel)
            return
    except AttributeError:
        pass

    tags = " ".join(message.content.split(" ")[1:])

    try:
        number = int(tags)

        details = await r34_bot.getPostData(number)

        tags = details['@tags']
        image_url = details['@file_url']

        embed = EmbedFactory.rule34_image(tags, image_url, number)
        await bot.send("", message.channel, embed=embed)
        return

    except ValueError:

        links = await r34_bot.getImageURLS(tags)
        embed = EmbedFactory.rule34_image([], random.choice(links), "Random result for " + tags)

        await bot.send("", message.channel, embed=embed)


async def forgotten_emote(message, bot):

    wanted_emote = " ".join(message.content.split(" ")[1:])

    if wanted_emote == "list":
        await bot.send("Current forgotten emotes:\n`" + " ".join(FORGOTTEN_IMAGES.keys()) + "`", message.channel)
        return

    try:

        await bot.send("", message.channel, file=FORGOTTEN_IMAGES[wanted_emote],
                       filename=FORGOTTEN_IMAGES[wanted_emote].split("\\")[-1])

    except KeyError:

        await bot.send("Unknown forgotten image", message.channel)


def create_r_bot():
    global r_bot

    with open('data//config.json') as json_data_file:
        r_data = json.load(json_data_file)['reddit']

        r_bot = RedditBot(r_data['username'], r_data['password'],
                          r_data['client-id'], r_data['secret-id'],
                          "DiscordScraper/v1.0")

    r_bot.authorize()


def create_r34_bot(loop):
    global r34_bot

    r34_bot = rule34.Rule34(loop)


command_list = {
    'stack': stack,
    'p': get_post,
    'help': _help,
    'pm': lambda m, b: get_post(m, b, multi=True),
    'ping': ping,
    'r': random_nhentai,
    's': nhentai_search,
    '34': rule34_search,
    'f': forgotten_emote
}

default_command = unknown_command

trigger = "/"


if __name__ == '__main__':
    rule34 = rule34.Sync()
    print(rule34.getImageURLS("lucina"))
    print(rule34.getPostData(1818))
