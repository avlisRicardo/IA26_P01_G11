"""
data_loader.py
--------------
Carregamento do dataset (ficheiros CSV) do projeto de routing de produtos locais.

Uso:
    from src.data_loader import load_dataset
    ds = load_dataset("data/tiny")
    ds.orders.head()
    ds.rules["stop_service_min"]          # -> 10
    ds.distance(1, 4)                     # -> (30.6, 40.8)  (km, minutos)
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# Colunas com datas/horas, por ficheiro (convertidas para datetime)
DATETIME_COLUMNS = {
    "orders": ["order_datetime"],
    "order_items": ["availability_start", "availability_end",
                    "delivery_start", "delivery_end"],
}

#class "contentor" de todos os dados
@dataclass
class Dataset:
    """Agrupa todas as tabelas do dataset e as regras do problema."""
    localities: pd.DataFrame
    producers: pd.DataFrame
    products: pd.DataFrame
    collection_centers: pd.DataFrame
    vehicles: pd.DataFrame
    customers: pd.DataFrame
    delivery_locations: pd.DataFrame
    orders: pd.DataFrame
    order_items: pd.DataFrame
    locations: pd.DataFrame
    distance_matrix: pd.DataFrame
    rules: dict

    def __post_init__(self):
        # Dicionários de consulta rápida (O(1)) para usar nos algoritmos de pesquisa
        dm = self.distance_matrix
        self._dist_lookup = {
            (o, d): (km, mins)
            for o, d, km, mins in zip(dm.origin_location_id, dm.destination_location_id,
                                      dm.distance_km, dm.duration_min)
        }
        loc = self.locations
        self._loc_lookup = {
            (t, r): lid for t, r, lid in zip(loc.location_type, loc.ref_id, loc.location_id)
        }

    def tables(self) -> dict:
        """Devolve todas as tabelas (sem as regras) como dicionário {nome: DataFrame}."""
        return {k: v for k, v in self.__dict__.items() if isinstance(v, pd.DataFrame)}

    def distance(self, origin: int, destination: int) -> tuple:
        """Distância (km) e tempo (min) entre dois location_id."""
        if origin == destination:
            return 0.0, 0.0
        return self._dist_lookup[(origin, destination)]

    def location_id(self, location_type: str, ref_id: int) -> int:
        """
        Converte uma entidade no seu location_id (usado na matriz de distâncias).
        Ex.: location_id("producer", 2) ou location_id("delivery_location", 3)
        """
        return self._loc_lookup[(location_type, ref_id)]


def _parse_rule(value: str):
    """Converte o valor de uma regra para int, float ou mantém como texto."""
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            pass
    return value


def load_rules(path: Path) -> dict:
    """Lê rules.csv para um dicionário {regra: valor}."""
    df = pd.read_csv(path)
    return {row.rule: _parse_rule(str(row.value)) for row in df.itertuples()}


def load_dataset(folder) -> Dataset:
    """Lê todos os CSV de uma pasta e devolve um objeto Dataset."""
    folder = Path(folder)
    if not folder.exists():
        raise FileNotFoundError(f"Pasta do dataset não encontrada: {folder.resolve()}")

    tables = {}
    for name in Dataset.__dataclass_fields__:
        if name == "rules":
            continue
        tables[name] = pd.read_csv(folder / f"{name}.csv",
                                   parse_dates=DATETIME_COLUMNS.get(name, []))

    return Dataset(**tables, rules=load_rules(folder / "rules.csv"))