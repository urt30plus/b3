"""
Hall of Fame
"""
from dataclasses import dataclass

import b3.clients
import b3.parser


@dataclass
class Record:
    plugin_name: str
    map_name: str
    client: b3.clients.Client
    score: int
    is_new: bool = False


def record_holder(
    console: b3.parser.Parser,
    plugin_name: str,
    map_name: str = None,
) -> Record:
    if map_name is None:
        map_name = console.game.mapName
    q = (
        "SELECT * FROM plugin_hof "
        f"WHERE plugin_name='{plugin_name}' and map_name='{map_name}'"
    )
    with console.storage.query(q) as cursor:
        if r := cursor.getOneRow():
            if clients := console.clients.getByDB(f'@{r["player_id"]}'):
                return Record(
                    plugin_name=plugin_name,
                    map_name=map_name,
                    client=clients[0],
                    score=int(r["score"]),
                    is_new=False,
                )
    raise LookupError(f"Record not found: {plugin_name} / {map_name}")


def update_hall_of_fame(
    console: b3.parser.Parser,
    plugin_name: str,
    map_name: str,
    client: b3.clients.Client,
    score: int,
) -> Record:
    try:
        curr_record = record_holder(console, plugin_name, map_name)
    except LookupError:
        q = (
            f"INSERT INTO plugin_hof(plugin_name, map_name, player_id, score) "
            f"VALUES('{plugin_name}', '{map_name}', {client.id}, {score})"
            ""
        )
    else:
        if curr_record.score >= score:
            return curr_record
        q = (
            f"UPDATE plugin_hof SET player_id={client.id}, score={score} "
            f"WHERE plugin_name='{plugin_name}' and map_name='{map_name}'"
        )

    console.storage.query(q)
    return Record(
        plugin_name=plugin_name,
        map_name=map_name,
        client=client,
        score=score,
        is_new=True,
    )
