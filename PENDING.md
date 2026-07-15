# Pending
Current issue: game stays pending as long as it's considered 'updated'.

## Issue 1: What counts as 'updated'?
I believe right now, any game with an updatedAt value higher than the last check counts. However, we should
just be checking to see if an actual UpdateMessageForScraperProcess was made between the new game and the last 
snapshot.

## Issue 2: Overwriting — IMPLEMENTED

Right now, if a game gets updated, it generates a diff message to be sent to #gameadditions and stores it with
the unstable flag. Then, on the next check, if somethings changes again, that old diff message gets overwritten.

This one is kind of fine with me right now.

Possible solution: create three new tables: pendingGame, pendingObjective, pendingObjectiveRequirement. When a game
gets an update (if it's the first, you can check by seeing if the game's id is currently in pendingGame), copy all the
current data to pendingGame / pendingObjective / pendingObjectiveRequirement. Store the newly updated data in the
proper tables. Then, keep determining if the game is updated by comparing with the most recently pulled data - 
which is in the proper game / objective / objectiveRequirement tables. Once that comparison turns up nothing, 
*then* generate the message by comparing the newly scraped data with the data from the pending* tables, and remove
that data from those tables.

Implemented per `docs/superpowers/plans/2026-07-15-pending-game-snapshot-diff.md` on branch
`feature/pending-game-snapshot-diff`. Note: the three Supabase tables above still need to be created manually
(SQL in the plan doc's "New Supabase Schema" section) before this is live in production.