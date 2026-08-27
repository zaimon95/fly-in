class Sim:
    def __init__(self, nb_drones: int) -> None:
        self._nb_drones = nb_drones

    def get_nb_drones(self) -> int:
        return self._nb_drones
