"""Every supported game, in dropdown order.

A game's position in GAMES is only its dropdown index. Anything that has to
survive an update -- saved settings, auto-detection -- goes by `key`, so a new
game can be inserted anywhere in the list without shifting what users saved.
"""
from dataclasses import dataclass
from typing import Callable

from games.assetto_corsa import AssettoCorsa
from games.assetto_corsa_shared_memory import AssettoCorsaSharedMemory
from games.automobilista_2 import Automobilista2
from games.dirt_rally_2_0 import DirtRally2
from games.f1 import F12019, F12020, F12022, F12023
from games.forza_horizon import ForzaHorizon5, ForzaHorizon6
from games.outgauge import OutGauge
from games.truck_simulator import TruckSimulator
from games.wreckfest_2 import Wreckfest2


@dataclass(frozen=True)
class GameSpec:
    key: str
    label: str
    icon: str
    create: Callable[..., object]
    # Set for games whose telemetry does not carry the rev limit, so the user
    # enters it: create() then takes max_rpm=, and it is saved under [key].
    default_max_rpm: int | None = None
    max_rpm_label: str | None = None
    # Read from /dev/shm through connect()/read_data() without a socket.
    uses_shared_memory: bool = False

    @property
    def needs_max_rpm(self) -> bool:
        return self.default_max_rpm is not None


GAMES = (
    GameSpec("ams_2", "AMS 2 / pCars / pCars2", "ams-2.png", Automobilista2),
    GameSpec("assetto_corsa", "Assetto Corsa", "assetto.png", AssettoCorsa,
             default_max_rpm=9000, max_rpm_label="Assetto Max RPM"),
    GameSpec("assetto_corsa_competizione", "Assetto Corsa Competizione", "assetto-corsa-competizione.png",
             AssettoCorsaSharedMemory, uses_shared_memory=True),
    GameSpec("assetto_corsa_rally", "Assetto Corsa Rally", "assetto-corsa-rally.png", AssettoCorsaSharedMemory,
             default_max_rpm=6700, max_rpm_label="Assetto Rally Max RPM", uses_shared_memory=True),
    GameSpec("beamng", "BeamNG", "beamng.png", OutGauge,
             default_max_rpm=6200, max_rpm_label="BeamNG Max RPM"),
    GameSpec("dirt_rally_2_0", "Dirt Rally 2.0", "dirt-rally-2-0.png", DirtRally2),
    GameSpec("truck_simulator", "Euro Truck Simulator 2 / American Truck Simulator",
             "euro-truck-simulator-2.png", TruckSimulator),
    GameSpec("f1_2019", "F1 2019", "f1-2019.png", F12019),
    GameSpec("f1_2020", "F1 2020", "f1-2020.png", F12020),
    GameSpec("f1_2022", "F1 2022", "f1-2022.png", F12022),
    GameSpec("f1_2023", "F1 2023", "f1-2023.png", F12023),
    GameSpec("forza_horizon_5", "Forza Horizon 5", "forza-horizon-5.png", ForzaHorizon5),
    GameSpec("forza_horizon_6", "Forza Horizon 6", "forza-horizon-6.png", ForzaHorizon6),
    GameSpec("live_for_speed", "Live for Speed", "live-for-speed.png", OutGauge,
             default_max_rpm=8000, max_rpm_label="Live for Speed Max RPM"),
    GameSpec("wreckfest_2", "Wreckfest 2", "wreckfest-2.png", Wreckfest2),
)

GAME_INDEX_BY_KEY = {game.key: index for index, game in enumerate(GAMES)}
