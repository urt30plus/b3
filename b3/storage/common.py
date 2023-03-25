import os
import re
import sys
import threading
from time import time

import b3.functions
from b3.clients import (
    Client,
    ClientBan,
    ClientKick,
    ClientNotice,
    ClientTempBan,
    ClientWarning,
    Penalty,
)
from b3.storage import Storage
from b3.storage.cursor import Cursor as DBCursor


class QueryBuilder:
    def __init__(self, db=None):
        """
        Object constructor.
        :param db: The current database connection.
        """
        self.db = db

    def escape(self, word):
        """
        Escape quotes from a given string.
        :param word: The string on which to perform the escape
        """
        if isinstance(word, (int, complex, float)):
            return str(word)
        elif word is None:
            return '"None"'
        else:
            escaped = word.replace('"', '\\"')
            return f'"{escaped}"'

    def quoteArgs(self, args):
        """
        Return a list of quoted arguments.
        :param args: The list of arguments to format.
        """
        if type(args[0]) is tuple or type(args[0]) is list:
            args = args[0]
        return tuple(map(self.escape, args))

    def fieldStr(self, fields):
        """
        Return a list of fields whose keywords are surrounded by backticks.
        :param fields: The list of fields to format.
        """
        if isinstance(fields, (tuple, list)):
            return "`%s`" % "`, `".join(fields)
        elif isinstance(fields, str):
            if fields == "*":
                return fields
            else:
                return f"`{fields}`"
        else:
            raise TypeError("field must be a tuple, list, or string")

    def FieldClause(self, field, value=None):
        """
        Format a field clause in SQL according to the given parameters.
        :param field: The comparision type for this clause.
        :param value: The value of the comparision.
        """
        field = field.strip()

        if type(value) in (list, tuple):
            return "`" + field + "` IN(" + ",".join(map(self.escape, value)) + ")"
        elif value is None:
            value = self.escape("")
        else:
            value = self.escape(value)

        if len(field) >= 2:
            if field[-2] == ">=":
                return "`" + field[:-2].strip() + "` >= " + value
            elif field[-2] == "<=":
                return "`" + field[:-2].strip() + "` <= " + value
            elif field[-1] == "<":
                return "`" + field[:-1].strip() + "` < " + value
            elif field[-1] == ">":
                return "`" + field[:-1].strip() + "` > " + value
            elif field[-1] == "=":
                return "`" + field[:-1].strip() + "` = " + value
            elif field[-1] == "%" and field[0] == "%":
                return "`" + field[1:-1].strip() + "` LIKE '%" + value[1:-1] + "%'"
            elif field[-1] == "%":
                return "`" + field[:-1].strip() + "` LIKE '" + value[1:-1] + "%'"
            elif field[0] == "%":
                return "`" + field[1:].strip() + "` LIKE '%" + value[1:-1] + "'"
            elif field[0] == "&":
                return "`" + field[1:].strip() + "` & " + value
            elif field[0] == "|":
                return "`" + field[1:].strip() + "` | " + value

        return "`" + field + "` = " + value

    def WhereClause(self, fields=None, values=None, concat=" and "):
        """
        Construct a where clause for an SQL query.
        :param fields: The fields of the where clause.
        :param values: The value of each field.
        :param concat: The concat value for multiple where clauses
        """
        sql = []
        if isinstance(fields, tuple) and values is None and len(fields) == 2:
            if isinstance(fields[1], list):
                values = tuple(fields[1])
            elif not isinstance(fields[1], tuple):
                values = (str(fields[1]),)

            if isinstance(fields[0], (tuple, list)):
                fields = tuple(fields[0])
            elif not isinstance(fields[0], tuple):
                fields = (str(fields[0]),)
        else:
            if isinstance(fields, list):
                fields = tuple(fields)
            if isinstance(values, list):
                values = tuple(values)

        if isinstance(fields, tuple) and isinstance(values, tuple):
            # this will be a combination of both
            if len(fields) == 1 and len(values) == 1:
                sql.append(self.FieldClause(fields[0], values[0]))
            else:
                for k, field in enumerate(fields):
                    v = values[k]
                    sql.append(self.FieldClause(field, v))

        elif (
            fields is not None
            and not isinstance(fields, tuple)
            and values is not None
            and not isinstance(values, tuple)
        ):
            sql.append(self.FieldClause(fields, values))

        elif isinstance(fields, tuple) and len(fields) == 1 and isinstance(values, str):
            sql.append(self.FieldClause(fields[0], values))

        elif isinstance(fields, tuple) and len(fields) > 0 and isinstance(values, str):
            sql.append(self.FieldClause(fields[0], values))

            for field in fields[1:]:
                sql.append(self.FieldClause(field, ""))

        elif isinstance(fields, dict):
            for k, v in fields.items():
                sql.append(self.FieldClause(k, v))

        else:
            # its type is unknown, nothing we can do
            return fields

        return concat.join(sql)

    def SelectQuery(
        self,
        fields,
        table,
        where="",
        orderby="",
        limit=0,
        offset="",
        groupby="",
        having="",
        **keywords,
    ):
        """
        Construct a SQL select query.
        :param fields: A list of fields to select.
        :param table: The table from where to fetch data.
        :param where: A WHERE clause for this select statement.
        :param orderby: The ORDER BY clayse for this select statement.
        :param limit: The amount of data data to collect.
        :param offset: An offset which specifies how many records to skip.
        :param groupby: The GROUP BY clause for this select statement.
        :param having: The HAVING clause for this select statement.
        :param keywords: Unused at the moment.
        """
        sql = [f"SELECT {self.fieldStr(fields)} FROM {table}"]

        if where:
            sql.append(f"WHERE {self.WhereClause(where)}")
        if groupby:
            sql.append(f"GROUP BY {orderby}")
        if having:
            sql.append(f"HAVING {having}")
        if orderby:
            sql.append(f"ORDER BY {orderby}")
        if limit:
            sql.append("LIMIT")
        if offset:
            sql.append(offset + ",")
        if limit:
            sql.append(str(limit))

        return " ".join(sql)

    def UpdateQuery(self, data, table, where, delayed=None):
        """
        Construct a SQL update query.
        :param data: A dictionary of key-value pairs for the update.
        :param table: The table from where to fetch data.
        :param where: A WHERE clause for this select statement.
        :param delayed: Whether to add the DELAYED clause to the query.
        """
        sql = "UPDATE "
        if delayed:
            sql += "DELAYED "
        sql += table + " SET "
        sets = [self.FieldClause(k, v) for k, v in data.items()]
        sql += ", ".join(sets)
        sql += " WHERE " + self.WhereClause(where)
        return sql

    def InsertQuery(self, data, table, delayed=None):
        """
        Construct a SQL insert query.
        :param data: A dictionary of key-value pairs for the update.
        :param table: The table from where to fetch data.
        :param delayed: Whether to add the DELAYED clause to the query.
        """
        sql = "INSERT "
        if delayed:
            sql += "DELAYED "
        sql += "INTO " + table
        keys = []
        values = []
        for k, v in data.items():
            keys.append(k)
            values.append(self.escape(v))
        sql += "(" + self.fieldStr(keys) + ") VALUES (" + ", ".join(values) + ")"
        return sql

    def ReplaceQuery(self, data, table, delayed=None):
        """
        Construct a SQL replace query.
        :param data: A dictionary of key-value pairs for the update.
        :param table: The table from where to fetch data.
        :param delayed: Whether to add the DELAYED clause to the query.
        """
        sql = "REPLACE "
        if delayed:
            sql += "DELAYED "
        sql += "INTO " + table
        keys = []
        values = []
        for k, v in data.items():
            keys.append(k)
            values.append(self.escape(v))
        sql += "(" + self.fieldStr(keys) + ") VALUES (" + ", ".join(values) + ")"
        return sql


class DatabaseStorage(Storage):
    _lastConnectAttempt = 0
    _consoleNotice = True
    _reName = re.compile(r"([A-Z])")
    _reVar = re.compile(r"_([a-z])")

    def __init__(self, dsn, dsnDict, console):
        """
        Object constructor.
        :param dsn: The database connection string.
        :param dsnDict: The database connection string parsed into a dict.
        :param console: The console instance.
        """
        self.dsn = dsn
        self.dsnDict = dsnDict
        self.console = console
        self.db = None
        self._lock = threading.Lock()

    def connect(self):
        """
        Establish and return a connection with the storage layer.
        :return The connection instance if established successfully, otherwise None.
        """
        raise NotImplementedError

    def getConnection(self):
        """
        Return the database connection. If the connection has not been established yet, will establish a new one.
        :return The connection instance, or None if no connection can be established.
        """
        raise NotImplementedError

    def shutdown(self):
        """
        Close the current active database connection.
        """
        raise NotImplementedError

    def closeConnection(self):
        """
        Just an alias for shutdown (backwards compatibility).
        """
        self.shutdown()

    def getCounts(self):
        """
        Return a dictionary containing the number of clients, Bans, Kicks, Warnings and Tempbans.
        """
        counts = {"clients": 0, "Bans": 0, "Kicks": 0, "Warnings": 0, "TempBans": 0}

        with self.query("SELECT COUNT(id) total FROM clients") as cursor:
            counts["clients"] = int(cursor.getValue("total", 0))

        with self.query(
            "SELECT COUNT(id) total, type FROM penalties GROUP BY type"
        ) as cursor:
            for r in cursor:
                counts[r["type"] + "s"] = int(r["total"])

        return counts

    def getClient(self, client):
        """
        Return a client object fetching data from the storage.
        :param client: The client object to fill with fetch data.
        """
        where = {"id": client.id} if client.id > 0 else {"guid": client.guid}
        try:
            with self.query(
                QueryBuilder(self.db).SelectQuery("*", "clients", where, None, 1)
            ) as cursor:
                if not cursor:
                    raise KeyError(f"no client matching guid {client.guid}")
                found = False
                for k, v in cursor.getRow().items():
                    setattr(client, self.getVar(k), v)
                    found = True
                if not found:
                    raise KeyError(f"no client matching guid {client.guid}")
                return client
        except Exception:
            # query failed, try local cache
            if self.console.config.has_option("admins_cache", client.guid):
                data = self.console.config.get("admins_cache", client.guid, True)
                self.console.debug("pulling user form admins_cache %s", data)
                cid, name, level = data.split(",")
                client.id = cid.strip()
                client.name = name.strip()
                client._tempLevel = int(level.strip())
                return client
            else:
                raise KeyError(f"no client matching guid {client.guid} in admins_cache")

    def getClientsMatching(self, match):
        """
        Return a list of clients matching the given data:
        :param match: The data to match clients against.
        """
        stmt = QueryBuilder(self.db).SelectQuery(
            "*", "clients", match, "time_edit DESC", 5
        )

        clients = []
        with self.query(stmt) as cursor:
            for row in cursor:
                client = Client()
                for k, v in row.items():
                    setattr(client, self.getVar(k), v)
                clients.append(client)

        return clients

    def setClient(self, client):
        """
        Insert/update a client in the storage.
        :param client: The client to be saved.
        :return: The ID of the client stored into the database.
        """
        fields = (
            "ip",
            "greeting",
            "connections",
            "time_edit",
            "guid",
            "pbid",
            "name",
            "time_add",
            "auto_login",
            "mask_level",
            "group_bits",
            "login",
            "password",
        )

        data = {"id": client.id} if client.id > 0 else {}

        for f in fields:
            if hasattr(client, self.getVar(f)):
                data[f] = getattr(client, self.getVar(f))

        if client.id > 0:
            self.query(
                QueryBuilder(self.db).UpdateQuery(data, "clients", {"id": client.id})
            )
        else:
            with self.query(
                QueryBuilder(self.db).InsertQuery(data, "clients")
            ) as cursor:
                client.id = cursor.lastrowid

        return client.id

    def setClientAlias(self, alias):
        """
        Insert/update an alias in the storage.
        :param alias: The alias to be saved.
        :return: The ID of the alias stored into the database.
        """
        fields = ("num_used", "alias", "client_id", "time_add", "time_edit")
        data = {"id": alias.id} if alias.id else {}

        for f in fields:
            if hasattr(alias, self.getVar(f)):
                data[f] = getattr(alias, self.getVar(f))

        if alias.id:
            self.query(
                QueryBuilder(self.db).UpdateQuery(data, "aliases", {"id": alias.id})
            )
        else:
            with self.query(
                QueryBuilder(self.db).InsertQuery(data, "aliases")
            ) as cursor:
                alias.id = cursor.lastrowid

        return alias.id

    def getClientAlias(self, alias):
        """
        Return an alias object fetching data from the storage.
        :param alias: The alias object to fill with fetch data.
        :return: The alias object given in input with all the fields set.
        """
        if hasattr(alias, "id") and alias.id > 0:
            query = QueryBuilder(self.db).SelectQuery(
                "*", "aliases", {"id": alias.id}, None, 1
            )
        elif hasattr(alias, "alias") and hasattr(alias, "clientId"):
            query = QueryBuilder(self.db).SelectQuery(
                "*",
                "aliases",
                {"alias": alias.alias, "client_id": alias.clientId},
                None,
                1,
            )
        else:
            raise KeyError(f"no alias found matching {alias}")

        row = self.query(query).getOneRow()
        if not row:
            raise KeyError(f"no alias found matching {alias}")
        alias.id = int(row["id"])
        alias.alias = row["alias"]
        alias.timeAdd = int(row["time_add"])
        alias.timeEdit = int(row["time_edit"])
        alias.clientId = int(row["client_id"])
        alias.numUsed = int(row["num_used"])

        return alias

    def getClientAliases(self, client):
        """
        Return the aliases of the given client
        :param client: The client whose aliases we want to retrieve.
        :return: List of b3.clients.Alias instances.
        """
        stmt = QueryBuilder(self.db).SelectQuery(
            "*", "aliases", {"client_id": client.id}, "id"
        )

        aliases = []
        with self.query(stmt) as cursor:
            for g in cursor:
                alias = b3.clients.Alias()
                alias.id = int(g["id"])
                alias.alias = g["alias"]
                alias.timeAdd = int(g["time_add"])
                alias.timeEdit = int(g["time_edit"])
                alias.clientId = int(g["client_id"])
                alias.numUsed = int(g["num_used"])
                aliases.append(alias)

        return aliases

    def setClientIpAddress(self, ipalias):
        """
        Insert/update an ipalias in the storage.
        :param ipalias: The ipalias to be saved.
        """
        fields = ("num_used", "ip", "client_id", "time_add", "time_edit")
        data = {"id": ipalias.id} if ipalias.id else {}

        for f in fields:
            if hasattr(ipalias, self.getVar(f)):
                data[f] = getattr(ipalias, self.getVar(f))

        if ipalias.id:
            self.query(
                QueryBuilder(self.db).UpdateQuery(data, "ipaliases", {"id": ipalias.id})
            )
        else:
            with self.query(
                QueryBuilder(self.db).InsertQuery(data, "ipaliases")
            ) as cursor:
                ipalias.id = cursor.lastrowid

        return ipalias.id

    def getClientIpAddress(self, ipalias):
        """
        Return an ipalias object fetching data from the storage.
        :param ipalias: The ipalias object to fill with fetch data.
        :return: The ip alias object given in input with all the fields set.
        """
        if hasattr(ipalias, "id") and ipalias.id > 0:
            query = QueryBuilder(self.db).SelectQuery(
                "*", "ipaliases", {"id": ipalias.id}, None, 1
            )
        elif hasattr(ipalias, "ip") and hasattr(ipalias, "clientId"):
            query = QueryBuilder(self.db).SelectQuery(
                "*",
                "ipaliases",
                {"ip": ipalias.ip, "client_id": ipalias.clientId},
                None,
                1,
            )
        else:
            raise KeyError(f"no ip found matching {ipalias}")

        row = self.query(query).getOneRow()
        if not row:
            raise KeyError(f"no ip found matching {ipalias}")
        ipalias.id = int(row["id"])
        ipalias.ip = row["ip"]
        ipalias.timeAdd = int(row["time_add"])
        ipalias.timeEdit = int(row["time_edit"])
        ipalias.clientId = int(row["client_id"])
        ipalias.numUsed = int(row["num_used"])

        return ipalias

    def getClientIpAddresses(self, client):
        """
        Return the ip aliases of the given client.
        :param client: The client whose ip aliases we want to retrieve.
        :return: List of b3.clients.IpAlias instances
        """
        stmt = QueryBuilder(self.db).SelectQuery(
            "*", "ipaliases", {"client_id": client.id}, "id"
        )

        aliases = []
        with self.query(stmt) as cursor:
            for row in cursor:
                ip = b3.clients.IpAlias()
                ip.id = int(row["id"])
                ip.ip = row["ip"]
                ip.timeAdd = int(row["time_add"])
                ip.timeEdit = int(row["time_edit"])
                ip.clientId = int(row["client_id"])
                ip.numUsed = int(row["num_used"])
                aliases.append(ip)

        return aliases

    def getLastPenalties(self, types="Ban", num=5):
        """
        Return the last 'num' penalties saved in the storage.
        :param types: The penalties type.
        :param num: The amount of penalties to retrieve.
        """
        where = QueryBuilder(self.db).WhereClause({"type": types, "inactive": 0})
        where += f" AND (time_expire = -1 OR time_expire > {int(time())})"
        stmt = QueryBuilder(self.db).SelectQuery(
            fields="*",
            table="penalties",
            where=where,
            orderby="time_add DESC, id DESC",
            limit=num,
        )

        penalties = []
        with self.query(stmt) as cursor:
            while not cursor.EOF and len(penalties) < num:
                penalties.append(self._createPenaltyFromRow(cursor.getRow()))
                cursor.moveNext()

        return penalties

    def setClientPenalty(self, penalty):
        """
        Insert/update a penalty in the storage.
        :param penalty: The penalty to be saved.
        :return: The ID of the penalty saved in the storage.
        """
        fields = (
            "type",
            "duration",
            "inactive",
            "admin_id",
            "time_add",
            "time_edit",
            "time_expire",
            "reason",
            "keyword",
            "client_id",
            "data",
        )

        data = {"id": penalty.id} if penalty.id else {}
        if penalty.keyword and not re.match(r"^[a-z0-9]+$", penalty.keyword, re.I):
            penalty.keyword = ""

        for f in fields:
            if hasattr(penalty, self.getVar(f)):
                data[f] = getattr(penalty, self.getVar(f))

        if penalty.id:
            self.query(
                QueryBuilder(self.db).UpdateQuery(data, "penalties", {"id": penalty.id})
            )
        else:
            with self.query(
                QueryBuilder(self.db).InsertQuery(data, "penalties")
            ) as cursor:
                penalty.id = cursor.lastrowid

        return penalty.id

    def getClientPenalty(self, penalty):
        """
        Return a penalty object fetching data from the storage.
        :param penalty: The penalty object to fill with fetch data.
        :return: The penalty given as input with all the fields set.
        """
        stmt = QueryBuilder(self.db).SelectQuery(
            "*", "penalties", {"id": penalty.id}, None, 1
        )
        if not (row := self.query(stmt).getOneRow()):
            raise KeyError(f"no penalty matching id {penalty.id}")
        return self._createPenaltyFromRow(row)

    def getClientPenalties(self, client, type="Ban"):
        """
        Return the penalties of the given client.
        :param client: The client whose penalties we want to retrieve.
        :param type: The type of the penalties we want to retrieve.
        :return: List of penalties
        """
        where = QueryBuilder(self.db).WhereClause(
            {"type": type, "client_id": client.id, "inactive": 0}
        )
        where += f" AND (time_expire = -1 OR time_expire > {int(time())})"
        stmt = QueryBuilder(self.db).SelectQuery(
            "*", "penalties", where, "time_add DESC"
        )
        with self.query(stmt) as cursor:
            return [self._createPenaltyFromRow(row) for row in cursor]

    def getClientLastPenalty(self, client, type="Ban"):
        """
        Return the last penalty added for the given client.
        :param client: The client whose penalty we want to retrieve.
        :param type: The type of the penalty we want to retrieve.
        :return: The last penalty added for the given client
        """
        where = QueryBuilder(self.db).WhereClause(
            {"type": type, "client_id": client.id, "inactive": 0}
        )
        where += f" AND (time_expire = -1 OR time_expire > {int(time())})"
        stmt = QueryBuilder(self.db).SelectQuery(
            "*", "penalties", where, "time_add DESC", 1
        )
        if not (row := self.query(stmt).getOneRow()):
            return None
        return self._createPenaltyFromRow(row)

    def getClientFirstPenalty(self, client, type="Ban"):
        """
        Return the first penalty added for the given client.
        :param client: The client whose penalty we want to retrieve.
        :param type: The type of the penalty we want to retrieve.
        :return: The first penalty added for the given client.
        """
        where = QueryBuilder(self.db).WhereClause(
            {"type": type, "client_id": client.id, "inactive": 0}
        )
        where += f" AND (time_expire = -1 OR time_expire > {int(time())})"
        stmt = QueryBuilder(self.db).SelectQuery(
            "*", "penalties", where, "time_expire DESC, time_add ASC", 1
        )
        if not (row := self.query(stmt).getOneRow()):
            return None
        return self._createPenaltyFromRow(row)

    def disableClientPenalties(self, client, type="Ban"):
        """
        Disable all the penalties for the given client.
        :param client: The client whose penalties we want to disable.
        :param type: The type of the penalties we want to disable.
        """
        self.query(
            QueryBuilder(self.db).UpdateQuery(
                {"inactive": 1},
                "penalties",
                {"type": type, "client_id": client.id, "inactive": 0},
            )
        )

    def numPenalties(self, client, type="Ban"):
        """
        Return the amount of penalties the given client has according to the given type.
        :param client: The client whose number of penalties we are interested into.
        :param type: The penalties type.
        :return The number of penalties.
        """
        where = QueryBuilder(self.db).WhereClause(
            {"type": type, "client_id": client.id, "inactive": 0}
        )
        where += f" AND (time_expire = -1 OR time_expire > {int(time())})"
        with self.query(
            f"""SELECT COUNT(id) total FROM penalties WHERE {where}"""
        ) as cursor:
            value = int(cursor.getValue("total", 0))
        return value

    _groups = None

    def getGroups(self):
        """
        Return a list of available client groups.
        """
        if not self._groups:
            stmt = QueryBuilder(self.db).SelectQuery("*", "groups", None, "level")
            with self.query(stmt) as cursor:
                self._groups = []
                for row in cursor:
                    group = b3.clients.Group()
                    group.id = int(row["id"])
                    group.name = row["name"]
                    group.keyword = row["keyword"]
                    group.level = int(row["level"])
                    group.timeAdd = int(row["time_add"])
                    group.timeEdit = int(row["time_edit"])
                    self._groups.append(group)

        return self._groups

    def getGroup(self, group):
        """
        Return a group object fetching data from the storage layer.
        :param group: A group object with level or keyword filled.
        :return: The group instance given in input with all the fields set.
        """
        if hasattr(group, "keyword") and group.keyword:
            query = QueryBuilder(self.db).SelectQuery(
                "*", "groups", {"keyword": group.keyword}, None, 1
            )
            self.console.verbose2(query)
            if not (row := self.query(query).getOneRow()):
                raise KeyError(f"no group matching keyword: {group.keyword}")

        elif hasattr(group, "level") and group.level >= 0:
            query = QueryBuilder(self.db).SelectQuery(
                "*", "groups", {"level": group.level}, None, 1
            )
            self.console.verbose2(query)
            if not (row := self.query(query).getOneRow()):
                raise KeyError(f"no group matching level: {group.level}")
        else:
            raise KeyError("cannot find Group as no keyword/level provided")

        group.id = int(row["id"])
        group.name = row["name"]
        group.keyword = row["keyword"]
        group.level = int(row["level"])
        group.timeAdd = int(row["time_add"])
        group.timeEdit = int(row["time_edit"])

        return group

    def truncateTable(self, table):
        """
        Empty a database table (or a collection of tables)
        :param table: The database table or a collection of tables
        :raise KeyError: If the table is not present in the database
        """
        raise NotImplementedError

    def getTables(self):
        """
        List the tables of the current database.
        :return: list of strings.
        """
        raise NotImplementedError

    def _query(self, query, bindata=None):
        """
        Execute a query on the storage layer (internal method).
        :param query: The query to execute.
        :param bindata: Data to bind to the given query.
        :raise Exception: If the query cannot be evaluated.
        """
        with self._lock:
            cursor = self.db.cursor()
            if bindata is None:
                cursor.execute(query)
            else:
                cursor.execute(query, bindata)
            dbcursor = DBCursor(cursor, self.db)
        return dbcursor

    def query(self, query, bindata=None):
        """
        Execute a query on the storage layer.
        :param query: The query to execute.
        :param bindata: Data to bind to the given query.
        :raise Exception: If the query cannot be evaluated.
        """
        # use existing connection or create a new one
        connection = self.getConnection()
        if not connection:
            raise Exception("lost connection with the storage layer during query")

        try:
            # always return a cursor instance (also when EOF is reached)
            return self._query(query=query, bindata=bindata)
        except Exception as e:
            # log so we can inspect the issue and raise again
            self.console.error("Query failed [%s] %r: %s", query, bindata, e)
            raise e

    def queryFromFile(self, fp, silent=False):
        """
        This method executes an external sql file on the current database.
        :param fp: The filepath of the file containing the SQL statements.
        :param silent: Whether to silence warnings.
        :raise Exception: If the query cannot be evaluated or if the given path cannot be resolved.
        """
        # use existing connection or create a new one
        # duplicate code of query() method which is needed not to spam the database
        # with useless connection attempts (one for each query in the SQL file)
        if not self.getConnection():
            raise Exception("lost connection with the storage layer during query")

        # save standard error output
        orig_stderr = sys.stderr
        if silent:
            # silence warnings and such
            sys.stderr = open(os.devnull, "w")  # noqa: SIM115

        path = b3.functions.getAbsolutePath(fp)
        if not os.path.exists(path):
            raise Exception(f"SQL file does not exist: {path}")

        with open(path, "r") as sqlfile:
            statements = self.getQueriesFromFile(sqlfile)

        for stmt in statements:
            # will stop if a single query generate an exception
            self.query(stmt)

        # reset standard error output
        sys.stderr = orig_stderr

    def status(self):
        """
        Check whether the connection with the storage layer is active or not.
        :return True if the connection is active, False otherwise.
        """
        raise NotImplementedError

    def getField(self, name):
        """
        Return a database field name given the correspondent variable name.
        :param name: The variable name.
        """
        return self._reName.sub(r"_\1", name)

    def getVar(self, name):
        """
        Return a variable name given the correspondent database field name.
        :param name: The database field name.
        """
        return self._reVar.sub(lambda m: m.group(1).upper(), name)

    @staticmethod
    def getQueriesFromFile(sqlfile):
        """
        Return a list of SQL queries given an open file pointer.
        :param sqlfile: An open file pointer to a SQL script file.
        :return: List of strings
        """
        lines = [
            x.strip()
            for x in sqlfile
            if x and not x.startswith("#") and not x.startswith("--")
        ]
        return [x.strip() for x in " ".join(lines).split(";") if x]

    @staticmethod
    def _createPenaltyFromRow(row):
        """
        Create a Penalty object given a result set row.
        :param row: The result set row
        """
        constructors = {
            "Warning": ClientWarning,
            "TempBan": ClientTempBan,
            "Kick": ClientKick,
            "Ban": ClientBan,
            "Notice": ClientNotice,
        }

        try:
            constructor = constructors[row["type"]]
            penalty = constructor()
        except KeyError:
            penalty = Penalty()

        penalty.id = int(row["id"])
        penalty.type = row["type"]
        penalty.keyword = row["keyword"]
        penalty.reason = row["reason"]
        penalty.data = row["data"]
        penalty.inactive = int(row["inactive"])
        penalty.timeAdd = int(row["time_add"])
        penalty.timeEdit = int(row["time_edit"])
        penalty.timeExpire = int(row["time_expire"])
        penalty.clientId = int(row["client_id"])
        penalty.adminId = int(row["admin_id"])
        penalty.duration = int(row["duration"])
        return penalty
