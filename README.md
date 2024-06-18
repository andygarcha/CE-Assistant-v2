# CE-Assistant (v2)
An object oriented version of [CE-Assistant-v1](https://github.com/andykasen13/CE-Assistant), a discord bot coded using `discord.py`. This bot serves two main purposes for the online community [Challenge Enthusiasts](https://cedb.me).

### Challenge Enthusiasts
Challenge Enthusiasts is an online community made to curate and categorize video games in a point-based system. Each game is given certain "objectives" based on tasks to be completed in the game.

## Purpose 1: Game Updates
This bot will send detailed updates to the [Discord server](https://discord.gg/spKdVZTZ6c) whenever a game on the site is added, updated, or removed.

<img src="https://imgur.com/rXGjnuc.png" width="450" alt="Screenshot of a game, Battletoads, being added to Challenge Enthusiasts.">

When a game is updated, the bot gives a run down of everything that was changed.

<img src="https://imgur.com/ME18Ja5.png" width="450" alt="Screenshot of a game, Terra Feminarum, being updated on Challenge Enthusiasts.">

When a game has a longer amount of objectives (seven or more), the bot will screenshot just the specific objective that was changed.

<img src="https://imgur.com/pbDCyJ1.png" width="450" alt="Screenshot of the 'Challenge Enthusiasts' game on the Challenge Enthusiasts site, used for keeping track of individual user accomplishments, having a singular objective update.">

## Purpose 2: Casino
This bot allows users in the [Discord server](https://discord.gg/spKdVZTZ6c) to participate in roll events. Users who participate in these will have a set number of games that fit certain parameters (difficulty, category, etc.) randomly selected for them, depending on the event. Once they complete these events (usually within a time limit, but some events go on forever), they're awarded a badge on the site, and the bot sends an update to the server.

<img src="https://imgur.com/XNCDYDn.png" width="450" alt ="Screenshot of a message showing that a user, Kyara, has completed the roll event 'One Hell of a Day'.">

The bot keeps track of all previously completed rolls as well, so anyone can view their previous accomplishments.

This gets a lot trickier, as some rolls are Co-Op or PvP. You can view a spreadsheet with information on all of the roll events [here](https://docs.google.com/spreadsheets/d/1jvYRLshEu65s15NKLNmVxUeTFh-y73Ftd1Quy2uLs3M/edit?usp=sharing).

## Smaller Capabilities
While CE-Assistant has its own main purposes, it also can do a lot of smaller stuff.

### 1. Return user information
Users can use `/profile`, with an optional parameter of another `discord.User`, and the bot will return information about this user.

<img src="https://imgur.com/O85pItz.png" width="450" alt="An example of a profile embed, requested by user 'wantarou'.">

### 2. Return information on any CE game
Users can use `/ce-game` with one parameter for the name of the game, and the bot will return information from CE about it.
> Insert image

### 3. Return information on any Steam game
Users can use `/steam-game` with one parameter for the name of the game, and the bot will return information from Steam about it.

<img src="https://imgur.com/k6UO0aQ.png" width="450" alt="Requested Steam information on Celeste.">

### 4. Steam curator
The [Steam curator](https://store.steampowered.com/curator/36185934/) for Challenge Enthusiasts is updated with games that are cleared and popular on the site. Any time the curator is updated, the bot will send a message.

<img src="https://imgur.com/7LIzjYY.png" width="450" alt="A curator message showing that RefleX has been added to the curator.">

### 5. Setting user color
Challenge Enthusiast users are awarded ranks based on how many points they have. The higher rank they are, the more colors they have access to within the Discord server. `/set-color` presents users with the options they have available to them and changes their colors on request.

<img src="https://imgur.com/WGF0wQz.png" width="450" alt="Set color menu">

### 6. Get SteamHunters information
One Challenge Enthusiasts user, Schmole, runs a script once a month and collects information on all the games and users on Challenge Enthusiasts and dumps it on [this spreadsheet](https://docs.google.com/spreadsheets/d/1oAUw5dZdqZa1FWqrBV9MQQTr8Eq8g33zwEb49vk3hrk/edit?usp=sharing). This bot can access this spreadsheet and save specific data from it, specifically the 'Median Completion Time' from SteamHunters. So, rather than scrape the SteamHunters API every time a game is checked, the bot just accesses its local copy of this spreadsheet.

### 7. Help/FAQ
As is standard with any Discord bot, users can use `/help` to get a menu with frequently asked questions and access to other help.

## Admin Capabilities
Administrators in the server have access to other commands to help with the bot.

### 8. Add notes
Administrators have the option to add notes to any game update message, in case there's any added context needed.
> Insert image

### 9. Purge roll
In the event that something happens with a roll event, administrators can manually remove a roll from a user (without initiating a cooldown) so that they can re-roll.

## How this gets done (for nerd losers)
The previous version of this code, [CE-Assistant](https://github.com/andykasen13/CE-Assistant), was not object-oriented. While it also used `discord.py`, it held all of its data in `.json` files and simply edited them raw. This became a huge issue whenever we, the developers, had to go back in and fix something, because as time went on, dealing with just the raw data got more and more confusing. In this version, we made classes for every type of object we were working with.

This bot utilizes the APIs for [Steam](https://store.steampowered.com), [RetroAchievements](https://retroachievements.org), [SteamHunters](https://steamhunters.com), and [Challenge Enthusiasts](https://cedb.me). It stores its information using [MongoDB](https://mongodb.com).

The module [Mongo_Reader](./Modules/Mongo_Reader.py) contains all of the functions used for getting and dumping information straight from MongoDB. Similarly, the module [CEAPIReader](./Modules/CEAPIReader.py) contains all of the functions used for scraping information from Challenge Enthusiasts' own backend.

For screenshotting, we use Selenium WebDrivers to access the internet and re-worked the screenshot functions in `PIL`. It uses the locations of specific objects on the pages to get the exact screen needed, and saves it until it can be sent.

## Credits
Credits to [Andy](https://github.com/andykasen13) and [Theron](https://github.com/TheronBoozer) for being the main developers of both versions.

Credits to [Folkius](https://github.com/Folkius) and Jarvis, the main administrators of Challenge Enthusiasts who helped us with direction and ideas quite a lot, and to [Laura](https://github.com/lauriys) for writing the entire backend for the site and several custom API endpoints for the bot to use.

Credits to [apollo](https://github.com/apollohm) and [Schmole](https://github.com/Schmoley2) for writing code intermittenly and for general inspiration.

Credits to crappy for making both the icons for Challenge Enthusiasts emojis and the icon for CE-Assistant (seen below).

<img src="https://imgur.com/O9J7fg2.png" width="125" alt="The final icon used by CE-Assistant.">
