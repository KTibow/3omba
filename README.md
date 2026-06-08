# 3omba

3omba is a program that transforms a Roomba into a cleaning, wall-avoiding alarm clock.

## Use

- Make sure your Roomba is plugged in and accessible at `/dev/ttyUSB0`.
- Make sure you have `uv` installed - see [this guide](https://docs.astral.sh/uv/getting-started/installation/).
- Then just start it with `uv run main.py` (`uv` will handle installing dependencies for you),
- and use the buttons on your Roomba to schedule your alarm.

## Why so simplistic?

My original project was to fully replace the standard Roomba algorithm with a custom algorithm. But it turned out that, even after trying for weeks, the reinforcement learning framework I used, PufferLib, couldn't vacuum [my virtual rooms](https://github.com/KTibow/puffer) without moving in weird, unclean ways. I ended up cutting my losses and spending the rest of the time I had on

- cleaning up this MVP to usable state
- documenting my failure - [I blogged about it some here](https://kendell.dev/blog/rl-verage/), and the Multiagent Snake environment seems to have similar problems (movement that's seemingly random and stupid)
- making [other tools for the PufferLib community](https://kendell.dev/jsuarez-index/)

I'm still really happy with its obstacle/wall avoidance!
