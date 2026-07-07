# Database Health Checking
This feature should check on the status of the database and report back to the #privatelog through the Discord bot process.

### Who is doing the checking?
The scraper process should do this.

### What all should it check?
All of the following should be checked:
- Any games without categories should be marked
- Any Rolls with an inaccurate amount of rollGames with them should be marked (see `pytest` for this)
- Any objectives without any objectiveRequirements should be marked
- Any inconsistencies between the LocalCache and the Supabase data should be marked
  - NOTE: This one should only be run *once per day* due to Egress limits on the Supabase free-tier project.
- Anything else that you can think of, we should do it.

### When should it do this?
- This health checking should come right after the big scrape loop
- Additionally, this can be initialized with an admin-only /health-check command, similar to the /initiate-loop command.

### How should this be reported?
- Each warning should be outputted as a single message to the #privatelog.
- These should all be prepended with the :hospital: emoji.

### Should any of these be automatically fixed by the bot?
No. Leave this to me to handle manually.