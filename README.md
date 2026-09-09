# Here Comes The Bus for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

_Integration to integrate with Here Comes the bus._

**This integration will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | Show ignition and display on map in true/false state.
`sensor` | Show info from here comes the bus.
`device_tracker` | Show the bus on the map.

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `here_comes_the_bus`.
1. Download _all_ the files from the `custom_components/here_comes_the_bus/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant ("Settings" -> "System" -> Powerbutton at top right -> "Restart Home Assistant")
1. In the HA UI go to "Settings" -> "Devices & Services" click "+ Add Integration" and search for "Here Comes the Bus"

## Configuration is done in the UI

<!---->

## Bus arrival estimates

**Estimated time until arrival** shows how many minutes remain until a student's
morning pickup, afternoon drop-off, or midday stop. It compares the bus's current
location with at least two previous trips. If there isn't enough history, or the
bus's location is too old or doesn't match a known route, the estimate is
unavailable. **Estimated arrival details** explains what's happening.

Estimates use Recorder, Home Assistant's history storage. The default setup needs
no changes. If you exclude entities from recording, keep the bus **device tracker**,
**Log time**, **Speed**, and relevant **AM/mid/PM stop arrival time** sensors included.
The integration saves learned trips separately, so they survive normal history
cleanup. If Recorder is disabled, estimates pause and the details sensor explains
why. The bus tracker and reported sensors continue working.

**Estimated arrival status** shows `tracking` while the bus follows a known route,
`projecting` while briefly estimating progress from its recent speed, or `unknown`
when no estimate is available. At the stop, there are two possible outcomes:

- `done`: pickup or drop-off likely happened. Here Comes The Bus reported an
  arrival, or the bus's movement indicates it stopped there with **Estimate missed
  pickup/drop-off** enabled. This doesn't confirm that your child got on or off.
- `passed`: the bus went past the stop on its expected approach, but there isn't
  enough evidence to say whether pickup or drop-off happened.

With **Estimate missed pickup/drop-off** enabled, later location updates can
change `passed` to `done` if they provide enough evidence that the bus stopped.
Simply passing the stop, waiting longer, or enabling the option doesn't establish
that pickup or drop-off happened.

A new stop-arrival report from Here Comes The Bus takes precedence over the
estimate when it agrees with the bus's recent locations. The status becomes
`done` and the countdown ends, even with **Estimate missed pickup/drop-off** off.
That option is a fallback when no supported arrival report is available. The
integration uses HCTB's stop-arrival times, not individual badge scans, and checks
recent locations to avoid treating an old arrival time as today's pickup.

For spoken countdowns, add **Arrival announcements allowed** as a condition in your
automation. This pauses announcements when the estimate is missing or uncertain,
during brief projections, and after arrival. The integration doesn't make
announcements itself.

Find these options under **Settings → Devices & services → Here Comes The Bus → Configure**:

- **Enable arrival estimates** (on by default): turn this off if you only want the
  bus tracker and information reported by Here Comes The Bus. It disables all
  estimated sensors and their calculations. Saved trips are kept if you turn it
  back on later.
- **Estimate missed pickup/drop-off** (off by default): useful if your district
  or bus doesn't reliably report pickups and drop-offs through Here Comes The Bus.
  Turn this on to use the bus's movement and stops to estimate when pickup or
  drop-off happened, even if HCTB doesn't report it. The **Estimated pickup/drop-off**
  sensor turns on when a likely stop is detected. It can't tell whether your child
  actually got on or off the bus.
- **Bus direction at stop**: leave **Morning pickup** and **Afternoon drop-off** on
  **Automatic** to learn the direction from past trips. If the bus passes the stop
  in both directions, choose the direction it travels when picking up or dropping
  off that student to help distinguish the correct pass.
- **Pause announcements after the bus passes** (on by default): turn off
  **Arrival announcements allowed** once the bus appears to have passed the stop
  on its pickup or drop-off approach, even if no arrival was detected. It stays
  off for that morning, midday, or afternoon trip, including after a restart.

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[Home-Assistant-Here-Comes-The-Bus]: https://github.com/pcartwright81/Home-Assistant-Here-Comes-The-Bus
[buymecoffee]: https://www.buymeacoffee.com/pcartwright81
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/pcartwright81/Home-Assistant-Here-Comes-The-Bus.svg?style=for-the-badge
[commits]: https://github.com/pcartwright81/Home-Assistant-Here-Comes-The-Bus/commits/main
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/pcartwright81/Home-Assistant-Here-Comes-The-Bus.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Patrick%20Cartwright%20%40pcartwright81-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/pcartwright81/Home-Assistant-Here-Comes-The-Bus.svg?style=for-the-badge
[releases]: https://github.com/pcartwright81/Home-Assistant-Here-Comes-The-Bus/releases
