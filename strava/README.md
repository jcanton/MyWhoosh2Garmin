# What does it do

strava.py connects to the API to get all the activities and then uses your Strava cookie to login and get your .fit file from https://www.strava.com/activities/{activity.id}/export_original.
I did this because we are not allowed to scrape MyWhoosh site. It's in the TOS.

## Installation

### Register your app on Strava

1. Go to [Strava API settings](https://www.strava.com/settings/api)
2. Get your Strava cookie and turn it into a cookies.json
3. To continue, hold on

## Running

```
uv run main.py
```

Dependencies are declared at the top of `main.py` and pinned in `main.py.lock`, so `uv` resolves them on the first run.
