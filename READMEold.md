# CE-Assistant-v2
Object-based version of andykasen13/CE-Assistant

## little notes
- consider having `CEGame` hold an array of just `CEObjectives` instead of two different ones for `Primary` and `Community`. Keep the `get_primary_objectives()` and `get_community_objectives()` and it'll sort it within the class (wait im so smart!)
- look into schmole's idea of rerolling a specific game in a roll in the event of country-lock. Example:
  - admin runs /change-roll-game(event_name : str, user : discord.User)
  - spits out a dropdown of all currently rolled games and admin selects the game to reroll
  - manually change this game to a newly rerolled game.
- show role if a game uses one

## Classes
### CEUser
```
- private int discord_id
- private String ce_id
- private int casino_score
- private CE-Roll[] current_rolls
- private CE-Roll[] completed_rolls
- private CE-Roll[] pending_rolls
- private CE-Roll[] cooldowns
```

### CERoll
```
- private String roll_name
- private String init_time
- private String end_time
- private CE-Game[] games
- private String partner_id
- private int cooldown_days
- private int rerolls
```

### CEGame
```
- private String ce_id
- private String game_name
- private String platform
- private String platform_id
- private String point_value
- private boolean is_special // denotes whether the game is a special T0 or not
- private CE-Objective[] primary_objectives
- private CE-Objective[] community_objectives
- private int last_updated
```

### CEUserGame
```
- private int user_points
- private CE-User-Objective[] user_objective
```

### CEObjective
```
- private String ce_id
- private boolean is_community
- private String description
- private int point_value
- private int point_value_partial
- private String name
- private String requirements
- private String[] achievement_ce_ids // this will just be an array of ce-ids
```

### CEUserObjective
```
- private int user_points
```

### ideas
- "other classes" - steamdata, completiondata
- "other exceptions" - FailedUserUpdateException, FailedGameUpdateException
- do we want to have it update users stuff once a day (like have one big message per day outlining what happened that day) or do it every 30 minutes with casino
- /show-rolls (or something) to see all available rolls 
  - maybe /see-available-rolls?


### version 2 changelog
- huge backend changes, entirely object-oriented now.
- #game-additions posts now have links to their games.
- user updates!! messages will be sent in the new #user-log channel for any of the following:
  - a user ranks up
  - a user clears a t4 or higher
  - a user unlocks a new discord role (category/tier related)
  - open to more suggestions here!! please submit them in #assistant-feedback, i'd love to implement more of them
- rolling to return soon...
  - thank you folkius for covering for the past couple months :)
  - #casino-log messages will be more detailed
  - Winner Takes All will accept both tier and category options.
  - /check-rolls will be much more concise.

## google cloud commands

### tmux
create:
```
tmux new-session -d -s my_session
```
attach:
```
tmux attach -t my_session
```
create and attach:
```
tmux new-session -d -s my_session
tmux attach -t my_session
```
detach:
```
tmux detach
```
list sessions:
```
tmux list-sessions
```

### virtual environment
create:
```
python3 -m venv .venv
source .venv/bin/activate
```
kill:
```
deactivate
```


### pip dependencies
```
pip install --upgrade discord selenium pillow requests bs4 apscheduler pymongo motor chromedriver_binary webdriver_manager pandas google-api-python-client google-auth-httplib2 google-auth-oauthlib
```
- `discord`: discord api manager
- `selenium` and `pillow`: screenshotting
- `requests`: api access
- `bs4`: html sorting
- `apscheduler`: task scheduler (out of date)
- `pymongo` and `motor`: mongodb access
- `chromedriver_binary`: screenshotting (out of date?)
- `webdriver_manager`: screenshotting
- `google-api-python-client`, `google-auth-httplib2`, and `google-auth-oauthlib`: google api access
- `pandas`: manual google sheets collector (out of date)
