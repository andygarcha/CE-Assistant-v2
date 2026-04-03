# Plans
These are all of my plans for CE Assistant.

## Version 3
Separate out the logic into their own components. We have way too much running on a Discord bot right now.
1. Discord bot frontend (this repository).
2. Scraping loop. Runs once every 30 minutes.
    - would be very helpful to have a way to only scrape from databases with updatedAt values ≥ some given POST value.
3. Web page frontend. Holy shit this looks awful. Maybe it would just be better to integrate casino stuff into the site.
4. API hoster. This would *only* be useful if we keep the frontend. Otherwise it's fine to keep the advanced logic in the bot. It doesn't hurt too badly.
5. Backend. Currently MongoDB, and I'd like to migrate to Supabase.

## Other Long-Term Updates
- Integrate all sheet-rolls from the Casino Google Sheet.