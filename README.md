# CE-Assistant-v2
Object-based version of andykasen13/CE-Assistant

## Classes
### CE-User
- private int discord_id
- private String ce_id
- private int casino_score
- private CE-Roll[] current_rolls
- private CE-Roll[] completed_rolls
- private CE-Roll[] pending_rolls
- private CE-Roll[] cooldowns

### CE-Roll
- private String roll_name
- private String init_time
- private String end_time
- private CE-Game[] games
- private String partner_id
- private int cooldown_days
- private int rerolls
- public boolean isCoOp()

### CE-Game
- private String ce_id
- private String game_name
- private String platform
- private String platform_id
- private String point_value
- private boolean is_special // denotes whether the game is a special T0 or not
- private CE-Objective[] primary_objectives
- private CE-Objective[] community_objectives
- private int last_updated

### CE-User-Game extends CE-Game
- private int user_points
- private CE-User-Objective[] user_objective

### CE-Objective
- private String ce_id
- private boolean is_community
- private String description
- private int point_value
- private int point_value_partial
- private String name
- private String requirements
- private String[] achievement_ce_ids // this will just be an array of ce-ids

### CE-User-Objective extends CE-Objective
- private int user_points
