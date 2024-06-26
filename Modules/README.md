# Modules
Each of these modules plays a critical part in CE-Assistant's functionality. Here's what they all do.

### CEAPIReader
This module handles all interaction with the Challenge Enthusiast API. It can retrieve data on a single user or single game, but more importantly it can scrape all users and/or all games at once.

## Discord_Helper
This module handles a lot of the bot's interaction with Discord. It can make `discord.Embed`s when given a game that describes that game, or set up scrolling buttons when given a list of Embeds. It will also handle making #game-additions messages.

## hm
This module is the bot's util module. I know having one util module is bad, and you should split them up into other modules that make more sense, but I don't want to. It hosts get_unix(), get_rollable_game(), and lots of other data to be accessed by other classes/modules.

## Mongo_Reader
This module handles all interaction with MongoDB. MongoDB is where the bot keeps all of its information on games and users, so update messages and casino rolls can be possible. It fetches and dumps.

## Reformatter
This module is built to move over data from [CE-Assistant-v1](https://github.com/andykasen13/CE-Assistant-v1) to the data style of this bot. This is only run once.

## scraping
This module handles all web interaction. I probably should come up with a better name for this. This currently handles user updates.

## SpreadsheetHandler
This module handles all interaction with Google Sheets. It can push and pull data from any Google Sheet owned by the CE Assistant Google account.
